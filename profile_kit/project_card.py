"""Featured module card: one clickable panel per repository in FEATURED_REPOS."""

from profile_kit.github_api import Repo
from profile_kit.svg import (
    AMBER,
    CYAN,
    LINE,
    MONO_ADVANCE,
    TEXT_HI,
    TEXT_MID,
    Svg,
    esc,
    frame,
    label,
    mono_width,
    num,
    readable,
    rolling_number,
    wrap,
)

WIDTH, HEIGHT = 420, 220
LEFT, RIGHT = 27, 393
NAME_SIZE = 17
DESCRIPTION_SIZE, DESCRIPTION_LINE = 10.5, 16


def _version_chip(svg: Svg, version: str) -> float:
    """Draw the latest release tag at the top right; return its left edge."""
    size = 9
    width = mono_width(version, size) + 14
    left = RIGHT - width
    svg.add(
        f'<g class="fade" style="animation-delay:.7s">'
        f'<rect x="{num(left)}" y="54" width="{num(width)}" height="16" '
        f'fill="{AMBER}" fill-opacity=".08" stroke="{AMBER}" stroke-opacity=".55"/>'
        f'<text x="{num(left + 7)}" y="65.5" font-size="{size}" font-weight="700" '
        f'fill="{AMBER}">{esc(version)}</text></g>'
    )
    return left


def render_project_card(repo: Repo, index: int) -> str:
    """Build the animated card SVG for `repo`, labelled as module `index`."""
    language = repo.language or "Unknown"
    svg = Svg(
        WIDTH,
        HEIGHT,
        title=f"{repo.name} - {language}",
        description=repo.description or "No description provided.",
    )
    frame(
        svg,
        f"MODULE {index:02d}",
        language.upper(),
        readable(repo.language_color),
        delay=index * 1.9,
    )
    svg.add(
        f'<text class="d fade" x="{RIGHT + 4}" y="132" font-size="96" '
        f'text-anchor="end" fill="{TEXT_HI}" fill-opacity=".035" '
        f'style="animation-delay:.2s">{index:02d}</text>'
    )

    name_limit = RIGHT - 12
    if repo.latest_release:
        name_limit = _version_chip(svg, repo.latest_release) - 12
    columns = int((name_limit - LEFT) / (MONO_ADVANCE * NAME_SIZE))
    name = repo.name if len(repo.name) <= columns else repo.name[: columns - 3] + "..."
    svg.add(
        f'<text class="rise" x="{LEFT}" y="67" font-size="{NAME_SIZE}" '
        f'font-weight="700" fill="{TEXT_HI}" style="animation-delay:.35s">'
        f"{esc(name)}</text>",
        f'<rect class="grow" x="{LEFT}" y="77" width="30" height="2" fill="{CYAN}" '
        f'style="animation-delay:.6s"/>',
        f'<rect class="grow" x="{LEFT + 34}" y="77" width="6" height="2" '
        f'fill="{CYAN}" fill-opacity=".5" style="animation-delay:.7s"/>',
    )

    columns = int((RIGHT - LEFT) / (MONO_ADVANCE * DESCRIPTION_SIZE))
    description = repo.description or "No description provided."
    for line_index, line in enumerate(wrap(description, columns, 4)):
        svg.add(
            f'<text class="fade" x="{LEFT}" y="{100 + line_index * DESCRIPTION_LINE}" '
            f'font-size="{DESCRIPTION_SIZE}" fill="{TEXT_MID}" '
            f'style="animation-delay:{num(0.55 + line_index * 0.09)}s">'
            f"{esc(line)}</text>"
        )

    svg.add(
        f'<path class="draw" d="M{LEFT},164H{RIGHT}" pathLength="1" stroke="{LINE}" '
        f'style="animation-delay:.4s"/>'
    )
    metrics = (
        ("STARS", repo.stars, 0),
        ("FORKS", repo.forks, 92),
        ("COMMITS", repo.commits, 184),
        ("RELEASES", repo.releases, 290),
    )
    for metric_index, (caption, value, offset) in enumerate(metrics):
        delay = 0.8 + metric_index * 0.12
        label(svg, caption, x=LEFT + offset, y=182, delay=delay)
        rolling_number(
            svg,
            f"{value:,}",
            x=LEFT + offset,
            y=201,
            size=13,
            fill=AMBER if caption == "STARS" else TEXT_HI,
            delay=delay,
        )
    return svg.render()
