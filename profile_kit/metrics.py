"""Pure computations behind the telemetry cards: rank, streaks and aggregates.

These mirror github-readme-stats and github-readme-streak-stats so the custom
cards report the same numbers the third-party cards used to show.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from profile_kit.github_api import ContributionDay, LanguageTotal, UserStats

RANK_THRESHOLDS = (1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100)
RANK_LEVELS = ("S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C")


@dataclass(frozen=True)
class Rank:
    """A github-readme-stats style grade and the percentile it sits at."""

    level: str
    percentile: float


@dataclass(frozen=True)
class Streak:
    """A run of consecutive contribution days."""

    length: int
    start: date
    end: date


@dataclass(frozen=True)
class StreakSummary:
    """Totals and streaks derived from the full contribution history."""

    total: int
    first: date
    current: Streak
    longest: Streak
    last_active: date | None


@dataclass(frozen=True)
class Week:
    """One column of the contribution waveform."""

    start: date
    total: int
    month: str | None


@dataclass(frozen=True)
class LanguageShare:
    """A language and its share of the displayed code, as a percentage."""

    language: LanguageTotal
    percent: float


def _exponential_cdf(x: float) -> float:
    return 1 - 2**-x


def _log_normal_cdf(x: float) -> float:
    return x / (1 + x)


def rank(stats: UserStats, *, all_commits: bool = True) -> Rank:
    """Grade activity the way github-readme-stats does, returning level and percentile.

    With all_commits the commit median is 1000, otherwise 250. A lower
    percentile is a better grade.
    """
    commit_median = 1000 if all_commits else 250
    weighted = (
        2 * _exponential_cdf(stats.commits / commit_median)
        + 3 * _exponential_cdf(stats.pull_requests / 50)
        + 1 * _exponential_cdf(stats.issues / 25)
        + 1 * _exponential_cdf(stats.reviews / 2)
        + 4 * _log_normal_cdf(stats.stars / 50)
        + 1 * _log_normal_cdf(stats.followers / 10)
    )
    percentile = (1 - weighted / 12) * 100
    index = next(
        i for i, threshold in enumerate(RANK_THRESHOLDS) if percentile <= threshold
    )
    return Rank(RANK_LEVELS[index], percentile)


def summarize_streak(days: list[ContributionDay]) -> StreakSummary:
    """Compute total, first and last activity, and current/longest streaks.

    `days` must be sorted and cover every calendar day up to today. A zero
    on the most recent day does not break a streak, because that day is not
    over yet, matching github-readme-streak-stats.
    """
    if not days:
        raise ValueError("No contribution days to summarize")
    today = days[-1].day
    first = None
    last = None
    total = 0
    current = Streak(0, today, today)
    longest = Streak(0, today, today)
    run_length = 0
    run_start = today
    for entry in days:
        total += entry.count
        if entry.count > 0:
            if first is None:
                first = entry.day
            last = entry.day
            run_length += 1
            if run_length == 1:
                run_start = entry.day
            current = Streak(run_length, run_start, entry.day)
            if run_length > longest.length:
                longest = current
        elif entry.day != today:
            run_length = 0
            current = Streak(0, today, today)
    return StreakSummary(total, first or today, current, longest, last)


def weekly_bins(
    days: list[ContributionDay], today: date, weeks: int = 52
) -> list[Week]:
    """Group contributions into the last `weeks` Sunday-aligned columns.

    Each column sums seven days; a column is labelled with a month when it
    contains the first day of that month.
    """
    counts = {entry.day: entry.count for entry in days}
    offset = (today.weekday() + 1) % 7
    this_sunday = today - timedelta(days=offset)
    columns = []
    for index in range(weeks - 1, -1, -1):
        start = this_sunday - timedelta(weeks=index)
        total = 0
        month = None
        for day_offset in range(7):
            day = start + timedelta(days=day_offset)
            total += counts.get(day, 0)
            if day.day == 1:
                month = day.strftime("%b").upper()
        columns.append(Week(start, total, month))
    return columns


def language_shares(
    languages: list[LanguageTotal], *, count: int = 6, hide: tuple[str, ...] = ("lua",)
) -> list[LanguageShare]:
    """Take the top `count` languages and express each as a share of their total.

    Languages named in `hide` (case-insensitive) are dropped first, matching
    the previous top-langs card configuration.
    """
    hidden = {name.lower() for name in hide}
    kept = [language for language in languages if language.name.lower() not in hidden][
        :count
    ]
    total = sum(language.size for language in kept)
    if total == 0:
        return []
    return [LanguageShare(language, 100 * language.size / total) for language in kept]
