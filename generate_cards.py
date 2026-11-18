"""Generate the telemetry cards: core metrics, language matrix and streaks.

Fetches activity totals, language sizes and the full contribution history,
then renders three animated SVGs into profile/. Run by the Update README
cards workflow every 30 minutes. Requires GITHUB_TOKEN.
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from profile_kit.github_api import (
    GitHubApiError,
    fetch_contributions,
    fetch_languages,
    fetch_profile,
    fetch_stats,
)
from profile_kit.langs_card import render_langs_card
from profile_kit.metrics import summarize_streak
from profile_kit.stats_card import render_stats_card
from profile_kit.streak_card import render_streak_card

LOGIN_ENV = "GITHUB_REPOSITORY_OWNER"
DEFAULT_LOGIN = "jn-s3s"
PROFILE_DIR = Path("profile")


def main() -> None:
    """Fetch telemetry data and write the three card SVGs."""
    login = os.environ.get(LOGIN_ENV, DEFAULT_LOGIN)
    today = datetime.now(UTC).date()
    try:
        profile = fetch_profile(login)
        stats = fetch_stats(login)
        languages = fetch_languages(login)
        days = fetch_contributions(login, profile.created_at.date(), today)
    except GitHubApiError as err:
        print(f"Aborting: {err}", file=sys.stderr)
        sys.exit(1)

    summary = summarize_streak(days)
    PROFILE_DIR.mkdir(exist_ok=True)
    cards = {
        "stats.svg": render_stats_card(stats),
        "top-langs.svg": render_langs_card(languages),
        "streak.svg": render_streak_card(summary, days, today),
    }
    for name, content in cards.items():
        (PROFILE_DIR / name).write_text(content, encoding="utf-8")
    print(f"Telemetry cards generated for {login}.")


if __name__ == "__main__":
    main()
