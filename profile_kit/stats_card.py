"""Core metrics card: activity totals with an animated rank gauge."""

import math

from profile_kit.github_api import UserStats
from profile_kit.metrics import rank
from profile_kit.svg import (
    AMBER,
    CYAN,
    GREEN,
    LINE,
    LINE_STRONG,
    TEXT_DIM,
    TEXT_MID,
    Svg,
    frame,
    label,
    num,
    rolling_number,
)

WIDTH, HEIGHT = 420, 230
LEFT = 27
VALUE_RIGHT = 252
GAUGE_X, GAUGE_Y, GAUGE_R = 332, 116, 50

ICONS = {
    "star": "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 "
    ".416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 "
    "1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 "
    ".416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z",
    "commit": "M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 "
    "4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 "
    "2.5 2.5 0 0 0 5 0Z",
    "pr": "M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 "
    "0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 "
    ".854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 "
    "0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 "
    "2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 "
    "0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z",
    "merge": "M5.45 5.154A4.25 4.25 0 0 0 9.25 7.5h1.378a2.251 2.251 0 1 1 0 "
    "1.5H9.25A5.734 5.734 0 0 1 5 7.123v3.505a2.25 2.25 0 1 1-1.5 0V5.372a2.25 "
    "2.25 0 1 1 1.95-.218ZM4.25 13.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 "
    "1.5Zm8.5-4.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5ZM5 3.25a.75.75 0 1 0 0 "
    ".005V3.25Z",
    "issue": "M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8 0a8 8 0 1 1 0 16A8 "
    "8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z",
}


def _icon(svg: Svg, name: str, x: float, y: float, delay: float) -> None:
    svg.add(
        f'<g class="fade" transform="translate({num(x)},{num(y)}) scale(.75)" '
        f'style="animation-delay:{num(delay)}s"><path d="{ICONS[name]}" fill="{AMBER}"/></g>'
    )


def _metric_row(
    svg: Svg, icon: str, caption: str, value: str, y: float, index: int
) -> None:
    delay = 0.4 + index * 0.12
    _icon(svg, icon, LEFT, y - 10, delay)
    label(svg, caption, x=LEFT + 18, y=y, fill=TEXT_MID, delay=delay)
    rolling_number(
        svg, value, x=VALUE_RIGHT, y=y + 1, size=15, anchor="end", delay=delay + 0.1
    )
    svg.add(
        f'<path class="fade" d="M{LEFT + 18},{y + 8}H{VALUE_RIGHT}" stroke="{LINE}" '
        f'stroke-dasharray="1 4" style="animation-delay:{num(delay)}s"/>'
    )


def _gauge(svg: Svg, level: str, percentile: float) -> None:
    circumference = 2 * math.pi * GAUGE_R
    target = circumference * percentile / 100
    svg.css.append(
        f"@keyframes gauge{{from{{stroke-dashoffset:{num(circumference)}}}}}"
    )
    origin = f"transform-origin:{GAUGE_X}px {GAUGE_Y}px"

    ticks = []
    for index in range(48):
        angle = math.radians(index * 7.5)
        inner = GAUGE_R + 7 if index % 4 == 0 else GAUGE_R + 9
        outer = GAUGE_R + 12
        x1 = GAUGE_X + inner * math.sin(angle)
        y1 = GAUGE_Y - inner * math.cos(angle)
        x2 = GAUGE_X + outer * math.sin(angle)
        y2 = GAUGE_Y - outer * math.cos(angle)
        ticks.append(f"M{num(x1)},{num(y1)}L{num(x2)},{num(y2)}")
    svg.add(
        f'<path class="fade" d="{"".join(ticks)}" stroke="{LINE_STRONG}" '
        f'style="animation-delay:.3s"/>',
        f'<circle cx="{GAUGE_X}" cy="{GAUGE_Y}" r="{GAUGE_R}" stroke="{LINE}" '
        f'stroke-width="5"/>',
        f'<g transform="rotate(-90 {GAUGE_X} {GAUGE_Y})"><circle cx="{GAUGE_X}" '
        f'cy="{GAUGE_Y}" r="{GAUGE_R}" stroke="{AMBER}" stroke-width="5" '
        f'stroke-linecap="round" stroke-dasharray="{num(circumference)}" '
        f'style="stroke-dashoffset:{num(target)};animation:gauge 1.8s '
        f'cubic-bezier(.3,.8,.2,1) both;animation-delay:.5s"/></g>',
        f'<g class="spin" style="{origin};animation-duration:24s"><circle '
        f'cx="{GAUGE_X}" cy="{GAUGE_Y}" r="{GAUGE_R - 9}" stroke="{CYAN}" '
        f'stroke-opacity=".4" stroke-dasharray="2 6"/></g>',
    )
    label(svg, "RANK", x=GAUGE_X, y=GAUGE_Y - 22, anchor="middle", delay=0.9)
    svg.add(
        f'<text class="d fade" x="{GAUGE_X}" y="{GAUGE_Y + 12}" font-size="30" '
        f'text-anchor="middle" fill="{AMBER}" style="animation-delay:1s">{level}</text>',
        f'<text class="fade" x="{GAUGE_X}" y="{GAUGE_Y + 30}" font-size="8" '
        f'text-anchor="middle" fill="{TEXT_DIM}" style="animation-delay:1.1s">'
        f"TOP {percentile:.1f}%</text>",
    )


def render_stats_card(stats: UserStats) -> str:
    """Build the animated core-metrics SVG with a rank gauge for `stats`."""
    grade = rank(stats)
    merge_rate = (
        100 * stats.merged_pull_requests / stats.pull_requests
        if stats.pull_requests
        else 0
    )
    svg = Svg(
        WIDTH,
        HEIGHT,
        title="Core metrics",
        description=(
            f"Stars {stats.stars}, commits {stats.commits}, pull requests "
            f"{stats.pull_requests}, merge rate {merge_rate:.1f}%, issues "
            f"{stats.issues}. Rank {grade.level}."
        ),
    )
    frame(svg, "TELEMETRY // CORE METRICS", "LIVE FEED", GREEN)
    rows = (
        ("star", "STARS EARNED", f"{stats.stars:,}"),
        ("commit", "TOTAL COMMITS", f"{stats.commits:,}"),
        ("pr", "PULL REQUESTS", f"{stats.pull_requests:,}"),
        ("merge", "MERGE RATE", f"{merge_rate:.1f}%"),
        ("issue", "ISSUES OPENED", f"{stats.issues:,}"),
    )
    for index, (icon, caption, value) in enumerate(rows):
        _metric_row(svg, icon, caption, value, 62 + index * 32, index)
    _gauge(svg, grade.level, grade.percentile)
    return svg.render()
