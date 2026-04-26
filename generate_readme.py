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
        return json.loads(response.read().decode("utf-8"))


def generate_readme(projects: list[dict]) -> str:
    """Generates the README.md content with GIF on left and projects on right.

    When no projects are provided, the GIF takes the full width.

    Parameters:
        projects: A list of repository metadata dictionaries.

    Returns:
        The generated README.md content as a string.
    """
    if not projects:
        return """<p align="center">
  <img src="https://media1.tenor.com/m/MVFAsfv3wk0AAAAC/one-piece-one-piece-movie.gif" alt="One Piece - Chopper" width="800">
</p>
"""

    project_items = []
    for project in projects:
        name = project["name"]
        url = project["html_url"]
        description = project.get("description") or "No description provided."
        language = project.get("language") or "N/A"
        stars = project.get("stargazers_count", 0)

        item = (
            f"<li>"
            f'<a href="{url}"><strong>{name}</strong></a> '
            f"<span>({language}) {stars} stars</span><br>"
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
    return readme


def main() -> None:
    """Main entry point for the README generator.

    Reads the repository list from environment variables,
    fetches metadata for each, and writes the generated README.md.
    """
    repos_env = os.environ.get(REPOS_ENV)
    if repos_env:
        repo_urls = [url.strip() for url in repos_env.split(",") if url.strip()]
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
