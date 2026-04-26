"""Generates the GitHub profile README.md with featured projects.

This script fetches repository metadata from the GitHub API and generates
a README.md file that displays the Chopper GIF on the left side and a list
of public projects on the right side.

Attributes:
    REPOS_ENV: Environment variable name containing comma-separated repo URLs.
"""

import os
import sys
import re
import urllib.request
import json
from pathlib import Path


REPOS_ENV = "FEATURED_REPOS"


def parse_repo_url(url: str) -> tuple[str, str]:
    """Extracts owner and repo name from a GitHub URL.

    Parameters:
        url: The GitHub repository URL.

    Returns:
        A tuple of (owner, repo_name).

    Raises:
        ValueError: If the URL is not a valid GitHub repository URL.
    """
    pattern = r"github\.com/([^/]+)/([^/]+)/?$"
    match = re.search(pattern, url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return match.group(1), match.group(2)


def fetch_repo_info(owner: str, repo: str) -> dict:
    """Fetches repository metadata from the GitHub API.

    Parameters:
        owner: The repository owner.
        repo: The repository name.

    Returns:
        A dictionary containing repository metadata.

    Raises:
        urllib.error.HTTPError: If the API request fails.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    req = urllib.request.Request(api_url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "jn-s3s-profile-readme-generator")

    with urllib.request.urlopen(req) as response:
        repo_info = json.loads(response.read().decode("utf-8"))

    # Fetch commit count using pagination
    commit_count = fetch_commit_count(owner, repo)
    repo_info["commit_count"] = commit_count

    # Fetch releases info
    releases_info = fetch_releases_info(owner, repo)
    repo_info["total_releases"] = releases_info["total_releases"]
    repo_info["latest_version"] = releases_info["latest_version"]

    return repo_info


def fetch_commit_count(owner: str, repo: str) -> int:
    """Fetches the total number of commits in the repository.

    Parameters:
        owner: The repository owner.
        repo: The repository name.

    Returns:
        The total number of commits, or 0 if unable to fetch.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    req = urllib.request.Request(api_url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "jn-s3s-profile-readme-generator")

    try:
        with urllib.request.urlopen(req) as response:
            commits = json.loads(response.read().decode("utf-8"))
            return len(commits) if commits else 0
    except Exception:
        return 0


def fetch_releases_info(owner: str, repo: str) -> dict:
    """Fetches releases information for the repository.

    Parameters:
        owner: The repository owner.
        repo: The repository name.

    Returns:
        A dictionary containing total_releases and latest_version.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    req = urllib.request.Request(api_url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "jn-s3s-profile-readme-generator")

    try:
        with urllib.request.urlopen(req) as response:
            releases = json.loads(response.read().decode("utf-8"))
            total_releases = len(releases) if releases else 0
            latest_version = releases[0]["tag_name"] if releases else None
            return {"total_releases": total_releases, "latest_version": latest_version}
    except Exception:
        return {"total_releases": 0, "latest_version": None}


def generate_readme(projects: list[dict]) -> str:
    """Generates the README.md content with GIF on left and projects on right.

    When no projects are provided, the GIF takes the full width.

    Parameters:
        projects: A list of repository metadata dictionaries.

    Returns:
        The generated README.md content as a string.
    """
    if not projects:
        readme = """<p align="center">
  <img src="https://media1.tenor.com/m/MVFAsfv3wk0AAAAC/one-piece-one-piece-movie.gif" alt="One Piece - Chopper" width="800">
</p>
"""
    else:
        project_items = []
        for project in projects:
            name = project["name"]
            url = project["html_url"]
            description = project.get("description") or "No description provided."
            language = project.get("language") or "N/A"
            owner = project["owner"]["login"]
            repo = project["name"]
            commits = project.get("commit_count", 0)
            total_releases = project.get("total_releases", 0)

            # Create dynamic badges for repo stats using HTML img tags
            commits_badge = f'<a href="{url}/network/members"><img src="https://img.shields.io/badge/commits-{commits}-brightgreen?style=social&logo=github" alt="GitHub Commits" /></a>'
            stars_badge = f'<a href="{url}/stargazers"><img src="https://img.shields.io/github/stars/{owner}/{repo}?style=social" alt="GitHub Stars" /></a>'
            forks_badge = f'<a href="{url}/network/members"><img src="https://img.shields.io/github/forks/{owner}/{repo}?style=social" alt="GitHub Forks" /></a>'
            lang_badge = f'<img src="https://img.shields.io/badge/language-{language}-blue" alt="Language" />' if language != "N/A" else ""

            # Create releases badges if available
            releases_badge = ""
            latest_release_badge = ""
            if total_releases > 0:
                releases_badge = f'<a href="{url}/releases"><img src="https://img.shields.io/badge/releases-{total_releases}-informational?style=social&logo=github" alt="GitHub Releases" /></a>'
                latest_release_badge = f'<a href="{url}/releases/latest"><img src="https://img.shields.io/github/v/release/{owner}/{repo}?style=social&logo=github" alt="Latest Release" /></a>'

            # Collect all badges
            badges = [commits_badge, stars_badge, forks_badge]
            if releases_badge:
                badges.append(releases_badge)
            if latest_release_badge:
                badges.append(latest_release_badge)
            if lang_badge:
                badges.append(lang_badge)
            badges_line = " ".join(badges)

            item = (
                f"<li>"
                f'<a href="{url}"><strong>{name}</strong></a><br>'
                f"{badges_line}<br>"
                f"<sub>{description}</sub>"
                f"</li>"
            )
            project_items.append(item)

        projects_html = "\n        ".join(project_items)

        readme = f"""<table width="100%">
  <tr>
    <td width="55%" valign="top">
      <img src="https://media1.tenor.com/m/MVFAsfv3wk0AAAAC/one-piece-one-piece-movie.gif" alt="One Piece - Chopper" width="100%">
    </td>
    <td width="45%" valign="top">
      <h3>Public Projects</h3>
      <ul>
        {projects_html}
      </ul>
    </td>
  </tr>
</table>
"""

    # Add stats at the bottom
    readme += """
<table width="100%">
  <tr>
    <td width="55%" valign="top">
      <img src="./profile/stats.svg" alt="jn-s3s GitHub stats" />
      <img src="./profile/streak.svg" alt="jn-s3s GitHub streak" />
    </td>
    <td width="45%" valign="top">
      <img src="./profile/top-langs.svg" alt="jn-s3s GitHub top language" />
    </td>
  </tr>
</table>
"""

    return readme


def main() -> None:
    """Main entry point for the README generator.

    Reads the repository list from environment variables,
    fetches metadata for each, and writes the generated README.md.
    """
    repos_env = os.environ.get(REPOS_ENV)
    if repos_env:
        repo_urls = [url.strip() for url in repos_env.splitlines()  if url.strip()]
    else:
        repo_urls = []

    projects = []
    for url in repo_urls:
        try:
            owner, repo = parse_repo_url(url)
            info = fetch_repo_info(owner, repo)
            projects.append(info)
            print(f"Fetched: {owner}/{repo}")
        except Exception as e:
            print(f"Error fetching {url}: {e}", file=sys.stderr)
            continue

    readme_content = generate_readme(projects)
    readme_path = Path("README.md")
    readme_path.write_text(readme_content, encoding="utf-8")

    if projects:
        print(f"README.md generated successfully with {len(projects)} projects.")
    else:
        print("README.md generated with no projects (GIF only).")


if __name__ == "__main__":
    main()
