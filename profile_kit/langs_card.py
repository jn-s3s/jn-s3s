"""Language matrix card: top languages as segmented spectrum bars."""

from profile_kit.github_api import LanguageTotal
from profile_kit.metrics import language_shares
from profile_kit.svg import (
    LINE,
    TEXT_HI,
    TEXT_MID,
    Svg,
    esc,
    frame,
    num,
    readable,
)

WIDTH, HEIGHT = 420, 230
LEFT, RIGHT = 27, 393
BAR_LEFT = 42
SEGMENTS = 40
ROW_TOP, ROW_STEP = 60, 28


def render_langs_card(languages: list[LanguageTotal]) -> str:
    """Build the animated language-matrix SVG from owned-repository totals."""
    shares = language_shares(languages)
    svg = Svg(
        WIDTH,
        HEIGHT,
        title="Most used languages",
        description=", ".join(
            f"{share.language.name} {share.percent:.1f}%" for share in shares
        ),
    )
    frame(svg, "TELEMETRY // LANGUAGE MATRIX", "BY BYTES")

    segment_width = (RIGHT - BAR_LEFT) / SEGMENTS
    for index, share in enumerate(shares):
        y = ROW_TOP + index * ROW_STEP
        color = readable(share.language.color)
        row_delay = 0.35 + index * 0.1
        svg.add(
            f'<rect class="fade" x="{LEFT}" y="{y - 8}" width="8" height="8" rx="1.5" '
            f'fill="{color}" style="animation-delay:{num(row_delay)}s"/>',
            f'<text class="fade" x="{BAR_LEFT}" y="{y}" font-size="11" font-weight="700" '
            f'fill="{TEXT_HI}" style="animation-delay:{num(row_delay)}s">'
            f"{esc(share.language.name)}</text>",
            f'<text class="fade" x="{RIGHT}" y="{y}" font-size="10" text-anchor="end" '
            f'fill="{TEXT_MID}" style="animation-delay:{num(row_delay)}s">'
            f"{share.percent:.1f}%</text>",
        )
        lit = round(share.percent / 100 * SEGMENTS)
        cells = []
        for segment in range(SEGMENTS):
            x = BAR_LEFT + segment * segment_width
            if segment < lit:
                delay = row_delay + 0.15 + segment * 0.022
                cells.append(
                    f'<rect class="fade" x="{num(x)}" y="{y + 5}" '
                    f'width="{num(segment_width - 1.6)}" height="6" rx="1" '
                    f'fill="{color}" style="animation-delay:{num(delay)}s"/>'
                )
            else:
                cells.append(
                    f'<rect x="{num(x)}" y="{y + 5}" width="{num(segment_width - 1.6)}" '
                    f'height="6" rx="1" fill="{LINE}"/>'
                )
        svg.add("".join(cells))
    return svg.render()
