"""GitHub API access for the profile generators.

Every request authenticates with the token in the GITHUB_TOKEN environment
variable. A failure raises GitHubApiError with the request context, so a
scheduled run stops before it can overwrite good cards with empty data.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime

API_URL = "https://api.github.com"
USER_AGENT = "jn-s3s-profile-generator"
RETRY_DELAYS = (3, 10)
PAGE_SIZE = 100


class GitHubApiError(RuntimeError):
    """Raised when a GitHub API call fails or returns an unusable payload."""


@dataclass(frozen=True)
class UserProfile:
    """Public identity details shown in the hero banner."""

    login: str
    user_id: int
    bio: str
    location: str
    created_at: datetime
    public_repos: int


@dataclass(frozen=True)
class Repo:
    """Metadata for one featured repository card."""

    owner: str
    name: str
    url: str
    description: str
    language: str | None
    language_color: str | None
    stars: int
    forks: int
    commits: int
    releases: int
    latest_release: str | None


@dataclass(frozen=True)
class UserStats:
    """Activity totals that feed the stats card and the rank."""

    stars: int
    commits: int
    pull_requests: int
    merged_pull_requests: int
    issues: int
    reviews: int
    followers: int


@dataclass(frozen=True)
class LanguageTotal:
    """Bytes of code written in one language across the owner's repositories."""

    name: str
    color: str | None
    size: int


@dataclass(frozen=True)
class ContributionDay:
    """Contribution count for one UTC calendar day."""

    day: date
    count: int


def _token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise GitHubApiError(
            "GITHUB_TOKEN is not set: export a token with repo scope first"
        )
    return token


def _send(method: str, path: str, body: dict | None = None) -> dict:
    """Send one API request, retrying network and 5xx failures twice."""
    request = urllib.request.Request(
        f"{API_URL}{path}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            if err.code >= 500 and attempt < len(RETRY_DELAYS):
                time.sleep(RETRY_DELAYS[attempt])
                attempt += 1
                continue
            detail = err.read().decode("utf-8", "replace")[:300]
            raise GitHubApiError(
                f"{method} {path} failed with HTTP {err.code}: {detail}"
            ) from err
        except urllib.error.URLError as err:
            if attempt < len(RETRY_DELAYS):
                time.sleep(RETRY_DELAYS[attempt])
                attempt += 1
                continue
            raise GitHubApiError(
                f"{method} {path} could not reach GitHub: {err.reason}"
            ) from err
        except json.JSONDecodeError as err:
            raise GitHubApiError(
                f"{method} {path} returned invalid JSON: {err}"
            ) from err


def _graphql(query: str, variables: dict, *, allow_missing: bool = False) -> dict:
    """Run a GraphQL query and return its data.

    With allow_missing, NOT_FOUND errors are logged and their fields come
    back as None instead of failing the whole query.
    """
    payload = _send("POST", "/graphql", {"query": query, "variables": variables})
    errors = payload.get("errors") or []
    missing = [error for error in errors if error.get("type") == "NOT_FOUND"]
    if errors and not (allow_missing and len(missing) == len(errors)):
        messages = "; ".join(error.get("message", "unknown error") for error in errors)
        raise GitHubApiError(f"GraphQL query failed: {messages}")
    for error in missing:
        print(f"Skipping: {error.get('message')}", file=sys.stderr)
    data = payload.get("data")
    if data is None:
        raise GitHubApiError("GraphQL response contained no data")
    return data


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch_profile(login: str) -> UserProfile:
    """Fetch the public profile of `login`. Raises GitHubApiError on failure."""
    query = """
    query($login: String!) {
      user(login: $login) {
        login databaseId bio location createdAt
        repositories(ownerAffiliations: OWNER, privacy: PUBLIC) { totalCount }
      }
    }
    """
    user = _graphql(query, {"login": login})["user"]
    return UserProfile(
        login=user["login"],
        user_id=user["databaseId"],
        bio=user["bio"] or "",
        location=user["location"] or "",
        created_at=_parse_time(user["createdAt"]),
        public_repos=user["repositories"]["totalCount"],
    )


def fetch_repos(specs: list[tuple[str, str]]) -> list[Repo]:
    """Fetch featured repositories in the order given as (owner, name) pairs.

    Repositories GitHub cannot find are logged and skipped. Any other
    failure raises GitHubApiError.
    """
    if not specs:
        return []
    fields = """
      name url description stargazerCount forkCount
      owner { login }
      primaryLanguage { name color }
      releases { totalCount }
      latestRelease { tagName }
      defaultBranchRef { target { ... on Commit { history { totalCount } } } }
    """
    params = ", ".join(
        f"$owner{i}: String!, $name{i}: String!" for i in range(len(specs))
    )
    selections = "\n".join(
        f"repo{i}: repository(owner: $owner{i}, name: $name{i}) {{ {fields} }}"
        for i in range(len(specs))
    )
    variables = {}
    for i, (owner, name) in enumerate(specs):
        variables[f"owner{i}"] = owner
        variables[f"name{i}"] = name
    data = _graphql(
        f"query({params}) {{ {selections} }}", variables, allow_missing=True
    )

    repos = []
    for i in range(len(specs)):
        node = data.get(f"repo{i}")
        if node is None:
            continue
        language = node["primaryLanguage"] or {}
        branch = node["defaultBranchRef"]
        history = (branch or {}).get("target", {}).get("history", {})
        release = node["latestRelease"] or {}
        repos.append(
            Repo(
                owner=node["owner"]["login"],
                name=node["name"],
                url=node["url"],
                description=node["description"] or "",
                language=language.get("name"),
                language_color=language.get("color"),
                stars=node["stargazerCount"],
                forks=node["forkCount"],
                commits=history.get("totalCount", 0),
                releases=node["releases"]["totalCount"],
                latest_release=release.get("tagName"),
            )
        )
    return repos


def _owned_repositories(login: str, selection: str, *, include_forks: bool) -> list:
    """Return every repository node owned by `login`, following pagination."""
    fork_filter = "" if include_forks else ", isFork: false"
    query = f"""
    query($login: String!, $after: String) {{
      user(login: $login) {{
        repositories(first: {PAGE_SIZE}, after: $after, ownerAffiliations: OWNER{fork_filter}) {{
          nodes {{ {selection} }}
          pageInfo {{ hasNextPage endCursor }}
        }}
      }}
    }}
    """
    nodes = []
    cursor = None
    while True:
        page = _graphql(query, {"login": login, "after": cursor})["user"][
            "repositories"
        ]
        nodes.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            return nodes
        cursor = page["pageInfo"]["endCursor"]


def fetch_stats(login: str) -> UserStats:
    """Fetch activity totals the same way github-readme-stats counts them.

    Commits come from commit search, so they include every year and every
    repository the token can see. Raises GitHubApiError on failure.
    """
    query = """
    query($login: String!) {
      user(login: $login) {
        followers { totalCount }
        pullRequests { totalCount }
        mergedPullRequests: pullRequests(states: MERGED) { totalCount }
        openIssues: issues(states: OPEN) { totalCount }
        closedIssues: issues(states: CLOSED) { totalCount }
        contributionsCollection { totalPullRequestReviewContributions }
      }
    }
    """
    user = _graphql(query, {"login": login})["user"]
    repos = _owned_repositories(login, "stargazerCount", include_forks=True)
    search_query = urllib.parse.urlencode({"q": f"author:{login}", "per_page": 1})
    search = _send("GET", f"/search/commits?{search_query}")
    return UserStats(
        stars=sum(repo["stargazerCount"] for repo in repos),
        commits=search["total_count"],
        pull_requests=user["pullRequests"]["totalCount"],
        merged_pull_requests=user["mergedPullRequests"]["totalCount"],
        issues=user["openIssues"]["totalCount"] + user["closedIssues"]["totalCount"],
        reviews=user["contributionsCollection"]["totalPullRequestReviewContributions"],
        followers=user["followers"]["totalCount"],
    )


def fetch_languages(login: str) -> list[LanguageTotal]:
    """Sum code size per language over owned, non-fork repositories.

    Returns the totals sorted from largest to smallest. Raises
    GitHubApiError on failure.
    """
    selection = """
      languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
        edges { size node { name color } }
      }
    """
    totals: dict[str, LanguageTotal] = {}
    for repo in _owned_repositories(login, selection, include_forks=False):
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            known = totals.get(name)
            size = edge["size"] + (known.size if known else 0)
            totals[name] = LanguageTotal(name, edge["node"]["color"], size)
    return sorted(totals.values(), key=lambda language: language.size, reverse=True)


def fetch_contributions(login: str, start: date, end: date) -> list[ContributionDay]:
    """Fetch daily contribution counts from `start` to `end`, both inclusive.

    GitHub limits one contributions query to a single year, so each year
    becomes its own alias in one request. Raises GitHubApiError on failure.
    """
    years = range(start.year, end.year + 1)
    params = ", ".join(
        f"$from{year}: DateTime!, $to{year}: DateTime!" for year in years
    )
    selections = "\n".join(
        f"y{year}: contributionsCollection(from: $from{year}, to: $to{year}) "
        "{ contributionCalendar { weeks { contributionDays { date contributionCount } } } }"
        for year in years
    )
    variables: dict[str, str] = {"login": login}
    for year in years:
        variables[f"from{year}"] = f"{max(start, date(year, 1, 1))}T00:00:00Z"
        variables[f"to{year}"] = f"{min(end, date(year, 12, 31))}T23:59:59Z"
    query = (
        f"query($login: String!, {params}) {{ user(login: $login) {{ {selections} }} }}"
    )
    user = _graphql(query, variables)["user"]

    days: dict[date, int] = {}
    for year in years:
        for week in user[f"y{year}"]["contributionCalendar"]["weeks"]:
            for entry in week["contributionDays"]:
                day = date.fromisoformat(entry["date"])
                if start <= day <= end and day.year == year:
                    days[day] = entry["contributionCount"]
    return [ContributionDay(day, count) for day, count in sorted(days.items())]
