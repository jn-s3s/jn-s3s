"""Contribution signal card: streaks plus a 52-week LED activity waveform."""

import math
from datetime import date

from profile_kit.github_api import ContributionDay
from profile_kit.metrics import Streak, StreakSummary, Week, weekly_bins
from profile_kit.svg import (
    AMBER,
    CYAN,
    GREEN,
    LINE,
    LINE_STRONG,
    TEXT_DIM,
    TEXT_HI,
    TEXT_MID,
    Svg,
    frame,
    label,
    num,
    rolling_number,
)

WIDTH, HEIGHT = 840, 230
LEFT = 27
DIVIDER_X = 262
WAVE_LEFT, WAVE_RIGHT = 282, 813
WAVE_BOTTOM = 202
SEGMENTS = 12
SEGMENT_PITCH = 8
COLUMNS = 52

STREAK_CSS = """
.scan{opacity:0}
@media (prefers-reduced-motion:no-preference){
.scan{opacity:1;animation:scan 8s linear infinite}
}
@keyframes scan{from{transform:translateX(0)}to{transform:translateX(VAR)}}
"""


def _fmt(day: date) -> str:
    return day.strftime("%b %d %Y").upper()


def _range(start: date, end: date) -> str:
    return _fmt(start) if start == end else f"{_fmt(start)} - {_fmt(end)}"


def _streak_detail(streak: Streak, last_active: date | None) -> str:
    if streak.length:
        return _range(streak.start, streak.end)
    if last_active:
        return f"LAST ACTIVE {_fmt(last_active)}"
    return "NO ACTIVITY YET"


def _streak_block(
    svg: Svg,
    caption: str,
    value: int,
    detail: str,
    top: float,
    color: str,
    delay: float,
) -> None:
    label(svg, caption, x=LEFT, y=top, fill=TEXT_MID, delay=delay)
    rolling_number(
        svg, f"{value:,}", x=LEFT, y=top + 34, size=32, fill=color, delay=delay + 0.1
    )
    unit = "DAY" if value == 1 else "DAYS"
    svg.add(
        f'<text class="fade" x="{LEFT}" y="{top + 50}" font-size="8" fill="{TEXT_DIM}" '
        f'style="animation-delay:{num(delay + 0.2)}s">{unit} // {detail}</text>'
    )


def _waveform(svg: Svg, weeks: list[Week]) -> None:
    peak = max((week.total for week in weeks), default=0)
    column_width = (WAVE_RIGHT - WAVE_LEFT) / COLUMNS
    bar_width = column_width - 3.4
    scan_travel = WAVE_RIGHT - WAVE_LEFT
    svg.css.append(STREAK_CSS.replace("VAR", f"{num(scan_travel)}px"))

    cells, labels = [], []
    for index, week in enumerate(weeks):
        x = WAVE_LEFT + index * column_width
        level = math.ceil(week.total / peak * SEGMENTS) if peak and week.total else 0
        col_delay = 0.5 + index * 0.028
        for segment in range(SEGMENTS):
            y = WAVE_BOTTOM - (segment + 1) * SEGMENT_PITCH
            if segment < level:
                color = AMBER if segment >= SEGMENTS - 3 else CYAN
                delay = col_delay + segment * 0.02
                cells.append(
                    f'<rect class="lift" x="{num(x)}" y="{num(y)}" '
                    f'width="{num(bar_width)}" height="6" rx="1" fill="{color}" '
                    f'style="animation-delay:{num(delay)}s"/>'
                )
            else:
                cells.append(
                    f'<rect x="{num(x)}" y="{num(y)}" width="{num(bar_width)}" '
                    f'height="6" rx="1" fill="{LINE}" fill-opacity=".55"/>'
                )
        if week.month:
            labels.append(
                f'<text class="fade" x="{num(x + column_width / 2)}" y="{WAVE_BOTTOM + 14}" '
                f'font-size="8" text-anchor="middle" fill="{TEXT_DIM}" '
                f'style="animation-delay:{num(col_delay)}s">{week.month}</text>'
            )
    svg.add(
        "".join(cells),
        f'<path class="draw" d="M{WAVE_LEFT},{WAVE_BOTTOM + 3}H{WAVE_RIGHT}" '
        f'pathLength="1" stroke="{LINE_STRONG}" style="animation-delay:.4s"/>',
        "".join(labels),
        f'<g class="scan"><rect x="{WAVE_LEFT}" y="{WAVE_BOTTOM - SEGMENTS * SEGMENT_PITCH}" '
        f'width="2" height="{SEGMENTS * SEGMENT_PITCH}" fill="{CYAN}" fill-opacity=".5"/></g>',
    )


def render_streak_card(
    summary: StreakSummary, days: list[ContributionDay], today: date
) -> str:
    """Build the animated contribution-signal SVG from streak totals and history."""
    weeks = weekly_bins(days, today)
    peak = max((week.total for week in weeks), default=0)
    svg = Svg(
        WIDTH,
        HEIGHT,
        title="Contribution activity",
        description=(
            f"{summary.total} total contributions since {_fmt(summary.first)}. "
            f"Current streak {summary.current.length} days, longest "
            f"{summary.longest.length} days."
        ),
    )
    frame(svg, "SIGNAL // CONTRIBUTION ACTIVITY", "LAST 52 WEEKS", GREEN)

    _streak_block(
        svg,
        "CURRENT STREAK",
        summary.current.length,
        _streak_detail(summary.current, summary.last_active),
        60,
        AMBER,
        0.4,
    )
    svg.add(
        f'<path class="draw" d="M{LEFT},128H{DIVIDER_X - 16}" pathLength="1" '
        f'stroke="{LINE}" style="animation-delay:.5s"/>'
    )
    _streak_block(
        svg,
        "LONGEST STREAK",
        summary.longest.length,
        _streak_detail(summary.longest, summary.last_active),
        146,
        TEXT_HI,
        0.6,
    )
    svg.add(
        f'<path class="draw" d="M{DIVIDER_X},52V208" pathLength="1" '
        f'stroke="{LINE}" style="animation-delay:.3s"/>'
    )

    label(svg, "TOTAL CONTRIBUTIONS", x=WAVE_LEFT, y=60, fill=TEXT_MID, delay=0.4)
    rolling_number(svg, f"{summary.total:,}", x=WAVE_LEFT, y=84, size=22, delay=0.5)
    svg.add(
        f'<text class="fade" x="{WAVE_RIGHT}" y="60" font-size="8" text-anchor="end" '
        f'fill="{TEXT_DIM}" style="animation-delay:.5s">SINCE {_fmt(summary.first)}</text>',
        f'<text class="fade" x="{WAVE_RIGHT}" y="84" font-size="8" text-anchor="end" '
        f'fill="{TEXT_DIM}" style="animation-delay:.6s">PEAK {peak}/WK</text>',
    )
    _waveform(svg, weeks)
    return svg.render()
