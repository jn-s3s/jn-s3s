"""Generate the GitHub profile README, hero banner and featured module cards.

Reads featured repository URLs from the FEATURED_REPOS environment variable,
fetches their metadata plus the operator profile, renders the animated SVGs
into profile/ and writes README.md. Run by the daily Update Profile README
workflow. Requires GITHUB_TOKEN.
"""

import os
import re
import sys
from pathlib import Path

from profile_kit.github_api import GitHubApiError, Repo, fetch_profile, fetch_repos
from profile_kit.hero import render_hero
from profile_kit.project_card import render_project_card
from profile_kit.svg import esc

REPOS_ENV = "FEATURED_REPOS"
LOGIN_ENV = "GITHUB_REPOSITORY_OWNER"
DEFAULT_LOGIN = "jn-s3s"
PROFILE_DIR = Path("profile")
PROJECTS_DIR = PROFILE_DIR / "projects"
MASCOT_GIF = "https://media1.tenor.com/m/MVFAsfv3wk0AAAAC/one-piece-one-piece-movie.gif"


def parse_repo_url(url: str) -> tuple[str, str]:
    """Extract owner and name from a GitHub repository URL.

    Raises ValueError when the URL is not a github.com repository link.
    """
    match = re.search(r"github\.com/([^/]+)/([^/]+)/?$", url.strip())
    if not match:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return match.group(1), match.group(2).removesuffix(".git")


def _repo_specs() -> list[tuple[str, str]]:
    raw = os.environ.get(REPOS_ENV, "")
    urls = [part.strip() for part in re.split(r"[\n,]+", raw) if part.strip()]
    specs = []
    for url in urls:
        try:
            specs.append(parse_repo_url(url))
        except ValueError as err:
            print(f"Skipping: {err}", file=sys.stderr)
    return specs


def _project_filename(index: int, repo: Repo) -> str:
    return f"{index:02d}-{repo.name}.svg"


def _clean_stale_projects(keep: set[str]) -> None:
    if not PROJECTS_DIR.exists():
        return
    for path in PROJECTS_DIR.glob("*.svg"):
        if path.name not in keep:
            path.unlink()


def assemble_readme(profile_login: str, repos: list[Repo]) -> str:
    """Build the README markup that lays out the generated SVG panels."""
    blocks = [
        '<p align="center">',
        f'  <img src="./{PROFILE_DIR}/hero.svg" alt="{esc(profile_login)} operator profile" width="100%">',
        "</p>",
    ]
    if repos:
        cards = []
        for index, repo in enumerate(repos, 1):
            alt = esc(f"{repo.name}: {repo.description or 'featured project'}")
            cards.append(
                f'  <a href="{esc(repo.url)}"><img src="./{PROJECTS_DIR}/'
                f'{_project_filename(index, repo)}" alt="{alt}" width="49%"></a>'
            )
        blocks += ['<p align="center">', *cards, "</p>"]
    blocks += [
        '<p align="center">',
        f'  <img src="./{PROFILE_DIR}/stats.svg" alt="Core metrics and rank" width="49%">',
        f'  <img src="./{PROFILE_DIR}/top-langs.svg" alt="Most used languages" width="49%">',
        "</p>",
        '<p align="center">',
        f'  <img src="./{PROFILE_DIR}/streak.svg" alt="Contribution activity and streaks" width="100%">',
        "</p>",
        "<details>",
        "<summary>// crew_mascot</summary>",
        "<br>",
        '<p align="center">',
        f'  <img src="{MASCOT_GIF}" alt="One Piece - Chopper" width="498">',
        "</p>",
        "</details>",
    ]
    return "\n".join(blocks) + "\n"


def main() -> None:
    """Fetch data, render the hero and module cards, and write README.md."""
    login = os.environ.get(LOGIN_ENV, DEFAULT_LOGIN)
    try:
        profile = fetch_profile(login)
        repos = fetch_repos(_repo_specs())
    except GitHubApiError as err:
        print(f"Aborting: {err}", file=sys.stderr)
        sys.exit(1)

    PROFILE_DIR.mkdir(exist_ok=True)
    PROJECTS_DIR.mkdir(exist_ok=True)
    (PROFILE_DIR / "hero.svg").write_text(render_hero(profile, repos), encoding="utf-8")

    keep = set()
    for index, repo in enumerate(repos, 1):
        name = _project_filename(index, repo)
        keep.add(name)
        (PROJECTS_DIR / name).write_text(
            render_project_card(repo, index), encoding="utf-8"
        )
    _clean_stale_projects(keep)

    Path("README.md").write_text(
        assemble_readme(profile.login, repos), encoding="utf-8"
    )
    print(f"README.md generated with {len(repos)} featured modules.")


if __name__ == "__main__":
    main()
