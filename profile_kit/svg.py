"""Shared visual system for the profile SVGs: palette, fonts, motion and frames.

Each card is a standalone SVG that GitHub shows through an <img> tag, so it
cannot load external files or run scripts. Fonts are embedded as data URIs.
Every animation sits inside `prefers-reduced-motion: no-preference`, and with
motion turned off an SVG shows its finished, static state.
"""

import base64
import json
import textwrap
from dataclasses import dataclass, field
from functools import cache
from html import escape
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parent / "fonts"
MONO_ADVANCE = 0.65
MARGIN = 5
CUT = 16

PANEL_TOP = "#0c121b"
PANEL_BOTTOM = "#070a10"
DOT = "#1a2634"
LINE = "#1d2937"
LINE_STRONG = "#34475f"
TEXT_HI = "#eaf2ff"
TEXT_MID = "#9aaac0"
TEXT_DIM = "#71839b"
AMBER = "#ffb23f"
CYAN = "#5fe3ff"
GREEN = "#79ff97"

_FONTS = (
    ("MM", 400, "martian-mono-400.woff2"),
    ("MM", 700, "martian-mono-700.woff2"),
    ("MI", 400, "michroma-400.woff2"),
)

BASE_CSS = """
text{font-family:MM,ui-monospace,monospace;font-kerning:none}
.d,.d text{font-family:MI,MM,sans-serif}
.beam,.comet,.halo,.scr{opacity:0}
@media (prefers-reduced-motion:no-preference){
.draw{stroke-dasharray:1;animation:draw 1.6s cubic-bezier(.65,0,.35,1) both}
.fade{animation:fade .9s ease-out both}
.rise{animation:rise .8s cubic-bezier(.2,.8,.2,1) both}
.roll{animation:roll 2.2s cubic-bezier(.1,.7,.1,1) both}
.type{animation:type .7s ease-out both}
.grow{transform-box:fill-box;transform-origin:left;animation:grow 1.1s cubic-bezier(.3,.8,.2,1) both}
.lift{transform-box:fill-box;transform-origin:bottom;animation:lift .9s cubic-bezier(.3,.8,.2,1) both}
.beam{opacity:1;animation:beam 11s linear infinite}
.comet{opacity:1;animation:comet 10s linear infinite}
.halo{opacity:1;transform-box:fill-box;transform-origin:center;animation:halo 2.6s ease-out infinite}
.blink{animation:fade 60ms linear both,blink 1.1s steps(1) infinite}
.spin{animation:spin 30s linear infinite}
}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
@keyframes fade{from{opacity:0}}
@keyframes rise{from{opacity:0;transform:translateY(8px)}}
@keyframes roll{from{transform:translateY(0)}}
@keyframes type{0%{opacity:0;fill:#fff}25%{opacity:1;fill:#fff}}
@keyframes grow{from{transform:scaleX(0)}}
@keyframes lift{from{transform:scaleY(0)}}
@keyframes comet{to{stroke-dashoffset:-1}}
@keyframes halo{from{opacity:.75;transform:scale(1)}to{opacity:0;transform:scale(3.2)}}
@keyframes blink{50%{opacity:0}}
@keyframes spin{to{transform:rotate(360deg)}}
"""


@cache
def _font_css() -> str:
    faces = []
    for family, weight, file_name in _FONTS:
        data = base64.b64encode((FONT_DIR / file_name).read_bytes()).decode("ascii")
        faces.append(
            f"@font-face{{font-family:{family};font-weight:{weight};"
            f'src:url(data:font/woff2;base64,{data}) format("woff2")}}'
        )
    return "".join(faces)


@cache
def _display_advances() -> dict[str, float]:
    path = FONT_DIR / "michroma-advances.json"
    return json.loads(path.read_text(encoding="utf-8"))


def esc(text: str) -> str:
    """Escape text for use inside SVG markup or attribute values."""
    return escape(text, quote=True)


def num(value: float) -> str:
    """Format a coordinate compactly, dropping needless trailing zeros."""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def mono_width(text: str, size: float, spacing: float = 0.0) -> float:
    """Width of `text` set in the embedded monospace font at `size` px."""
    return len(text) * (MONO_ADVANCE * size + spacing)


def display_width(text: str, size: float, spacing: float = 0.0) -> float:
    """Width of `text` set in the embedded display font at `size` px."""
    advances = _display_advances()
    return sum(advances.get(char, 0.95) * size + spacing for char in text)


def wrap(text: str, width: int, max_lines: int) -> list[str]:
    """Wrap `text` to `width` characters, ending with "..." when it is cut short."""
    lines = textwrap.wrap(" ".join(text.split()), width=width)
    if len(lines) <= max_lines:
        return lines
    kept = lines[:max_lines]
    kept[-1] = kept[-1][: width - 3].rstrip(" ,.;:-") + "..."
    return kept


def readable(color: str | None, fallback: str = CYAN, minimum: float = 3.0) -> str:
    """Lighten `color` toward white until it has `minimum` contrast on a panel."""
    base = (color or fallback).lstrip("#")
    if len(base) != 6:
        base = fallback.lstrip("#")
    channels = [int(base[i : i + 2], 16) for i in (0, 2, 4)]
    panel = _luminance([int(PANEL_BOTTOM[i : i + 2], 16) for i in (1, 3, 5)])
    for step in range(11):
        mixed = [round(c + (255 - c) * step / 10) for c in channels]
        if (_luminance(mixed) + 0.05) / (panel + 0.05) >= minimum:
            return "#" + "".join(f"{c:02x}" for c in mixed)
    return "#ffffff"


def _luminance(channels: list[int]) -> float:
    linear = []
    for channel in channels:
        c = channel / 255
        linear.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def chamfer(x: float, y: float, w: float, h: float, cut: float) -> str:
    """Path for a rectangle with its top-left and bottom-right corners cut off."""
    return (
        f"M{num(x + cut)},{num(y)}H{num(x + w)}V{num(y + h - cut)}"
        f"L{num(x + w - cut)},{num(y + h)}H{num(x)}V{num(y + cut)}Z"
    )


@dataclass
class Svg:
    """Collects the CSS, definitions and body markup of one SVG document."""

    width: int
    height: int
    title: str
    description: str
    css: list[str] = field(default_factory=list)
    defs: list[str] = field(default_factory=list)
    body: list[str] = field(default_factory=list)
    _next_id: int = field(default=0, repr=False)

    def uid(self, prefix: str) -> str:
        """Return an id that is unique inside this document."""
        self._next_id += 1
        return f"{prefix}{self._next_id}"

    def add(self, *markup: str) -> None:
        """Append markup to the document body, painted after earlier markup."""
        self.body.extend(markup)

    def render(self) -> str:
        """Return the complete SVG document."""
        style = _font_css() + BASE_CSS + "".join(self.css)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
            f'height="{self.height}" viewBox="0 0 {self.width} {self.height}" '
            f'fill="none" role="img" aria-labelledby="title desc">'
            f'<title id="title">{esc(self.title)}</title>'
            f'<desc id="desc">{esc(self.description)}</desc>'
            f"<style><![CDATA[{style}]]></style>"
            f"<defs>{''.join(self.defs)}</defs>{''.join(self.body)}</svg>\n"
        )


def frame(
    svg: Svg,
    label: str,
    meta: str = "",
    dot: str | None = None,
    *,
    delay: float = 0.0,
) -> None:
    """Paint the panel: background, border, ambient motion and header strip.

    Args:
        svg: The document to draw into.
        label: Header text on the left, set in the display font.
        meta: Optional header text on the right.
        dot: Optional color of a pulsing indicator in front of `meta`.
        delay: Seconds to offset the ambient loops, so cards drift apart.
    """
    x, y = MARGIN, MARGIN
    w, h = svg.width - 2 * MARGIN, svg.height - 2 * MARGIN
    shape = chamfer(x, y, w, h, CUT)
    fill, dots, glow, clip, beam = (
        svg.uid(name) for name in ("fill", "dots", "glow", "clip", "beam")
    )
    svg.defs.append(
        f'<linearGradient id="{fill}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{PANEL_TOP}"/>'
        f'<stop offset="1" stop-color="{PANEL_BOTTOM}"/></linearGradient>'
        f'<pattern id="{dots}" width="14" height="14" patternUnits="userSpaceOnUse">'
        f'<circle cx="1" cy="1" r=".75" fill="{DOT}"/></pattern>'
        f'<radialGradient id="{glow}" cx="0" cy="0" r="1" '
        f'gradientUnits="userSpaceOnUse" '
        f'gradientTransform="translate({x} {y}) scale({num(w * 0.6)} {num(h * 1.2)})">'
        f'<stop offset="0" stop-color="{AMBER}" stop-opacity=".09"/>'
        f'<stop offset="1" stop-color="{AMBER}" stop-opacity="0"/></radialGradient>'
        f'<clipPath id="{clip}"><path d="{shape}"/></clipPath>'
        f'<linearGradient id="{beam}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>'
        f'<stop offset=".8" stop-color="{CYAN}" stop-opacity=".05"/>'
        f'<stop offset="1" stop-color="{CYAN}" stop-opacity=".11"/></linearGradient>'
    )
    svg.css.append(f"@keyframes beam{{to{{transform:translateY({h + 90}px)}}}}")
    svg.add(
        f'<path d="{shape}" fill="url(#{fill})"/>',
        f'<path d="{shape}" fill="url(#{dots})"/>',
        f'<path d="{shape}" fill="url(#{glow})"/>',
        f'<g clip-path="url(#{clip})"><rect class="beam" x="{x}" y="{y - 90}" '
        f'width="{w}" height="90" fill="url(#{beam})" '
        f'style="animation-delay:{num(delay + 2.5)}s"/></g>',
        f'<path class="draw" d="{shape}" pathLength="1" stroke="{LINE_STRONG}"/>',
    )
    for dashes, width, opacity in (("0 .9 .1 0", 1.2, 0.3), ("0 .975 .025 0", 1.8, 1)):
        svg.add(
            f'<path class="comet" d="{shape}" pathLength="1" stroke="{AMBER}" '
            f'stroke-width="{width}" stroke-opacity="{opacity}" '
            f'stroke-dasharray="{dashes}" style="animation-delay:{num(delay)}s"/>'
        )
    corner = 14
    svg.add(
        f'<path d="M{x},{y + CUT + corner}V{y + CUT}L{x + CUT},{y}H{x + CUT + corner}'
        f"M{x + w},{y + h - CUT - corner}V{y + h - CUT}L{x + w - CUT},{y + h}"
        f'H{x + w - CUT - corner}" stroke="{AMBER}" stroke-width="1.6"/>',
        f'<path d="M{x + w - 9},{y}H{x + w}V{y + 9}M{x},{y + h - 9}V{y + h}H{x + 9}" '
        f'stroke="{TEXT_DIM}"/>',
    )

    base = y + 24
    left = x + 21
    right = x + w - 21
    label_x = left + 14
    svg.add(
        f'<path class="fade" d="M{left},{base}h7v-7z" fill="{AMBER}"/>',
        f'<text class="d fade" x="{label_x}" y="{base}" font-size="8" '
        f'letter-spacing="2.4" fill="{TEXT_MID}">{esc(label)}</text>',
    )
    line_end = right
    if meta:
        spacing = 2.0
        meta_width = display_width(meta, 8, spacing)
        svg.add(
            f'<text class="d fade" x="{num(right + spacing)}" y="{base}" '
            f'font-size="8" letter-spacing="{spacing}" text-anchor="end" '
            f'fill="{TEXT_MID}">{esc(meta)}</text>'
        )
        line_end = right - meta_width - 12
        if dot:
            cx = line_end - 2
            svg.add(
                f'<circle class="halo" cx="{num(cx)}" cy="{base - 3}" r="2.6" '
                f'fill="{dot}" style="animation-delay:{num(delay)}s"/>',
                f'<circle cx="{num(cx)}" cy="{base - 3}" r="2.6" fill="{dot}"/>',
            )
            line_end -= 14
    line_start = label_x + display_width(label, 8, 2.4) + 10
    # a shorter rule would strike through the label text or read as a stray stub
    if line_end - line_start >= 20:
        svg.add(
            f'<path class="draw" d="M{num(line_start)},{base - 3.5}H{num(line_end)}" '
            f'pathLength="1" stroke="{LINE}" style="animation-delay:.3s"/>'
        )


def rolling_number(
    svg: Svg,
    text: str,
    *,
    x: float,
    y: float,
    size: float,
    fill: str = TEXT_HI,
    anchor: str = "start",
    delay: float = 0.0,
) -> None:
    """Draw `text` in bold monospace with each digit rolling in like an odometer.

    Digits spin through a full cycle before they settle, and every other
    character fades in place. `anchor` is "start", "middle" or "end".
    """
    advance = MONO_ADVANCE * size
    width = advance * len(text)
    left = {"start": x, "middle": x - width / 2, "end": x - width}[anchor]
    step = size * 1.3
    clip = svg.uid("roll")
    svg.defs.append(
        f'<clipPath id="{clip}"><rect x="{num(left - 2)}" y="{num(y - size)}" '
        f'width="{num(width + 4)}" height="{num(size * 1.3)}"/></clipPath>'
    )
    glyphs = []
    for index, char in enumerate(text):
        cx = num(left + index * advance)
        start = num(delay + index * 0.08)
        if char.isdigit():
            rows = "".join(
                f'<tspan x="{cx}" dy="{num(step) if row else 0}">{row % 10}</tspan>'
                for row in range(20)
            )
            offset = num((10 + int(char)) * step)
            glyphs.append(
                f'<text class="roll" y="{num(y)}" style="transform:'
                f'translateY(-{offset}px);animation-delay:{start}s">{rows}</text>'
            )
        else:
            glyphs.append(
                f'<text class="fade" x="{cx}" y="{num(y)}" '
                f'style="animation-delay:{start}s">{esc(char)}</text>'
            )
    svg.add(
        f'<g clip-path="url(#{clip})" font-size="{num(size)}" font-weight="700" '
        f'fill="{fill}">{"".join(glyphs)}</g>'
    )


def typed_text(
    svg: Svg,
    text: str,
    *,
    x: float,
    y: float,
    size: float,
    fill: str,
    start: float,
    pace: float,
) -> float:
    """Draw `text` one monospace character at a time, like a terminal printing it.

    Returns the time in seconds at which the next character would appear.
    """
    advance = MONO_ADVANCE * size
    glyphs = []
    moment = start
    for index, char in enumerate(text):
        if char != " ":
            glyphs.append(
                f'<text class="type" x="{num(x + index * advance)}" y="{num(y)}" '
                f'style="animation-delay:{num(moment)}s">{esc(char)}</text>'
            )
        moment += pace
    svg.add(f'<g font-size="{num(size)}" fill="{fill}">{"".join(glyphs)}</g>')
    return moment


def label_spacing(size: float) -> float:
    """Letter-spacing label() applies at `size`, so callers can measure widths."""
    return round(size * 0.26, 2)


def label(
    svg: Svg,
    text: str,
    *,
    x: float,
    y: float,
    size: float = 8,
    fill: str = TEXT_DIM,
    anchor: str = "start",
    css_class: str = "fade",
    delay: float = 0.0,
) -> None:
    """Draw a small letter-spaced caption in the display font."""
    spacing = label_spacing(size)
    shift = spacing if anchor == "end" else 0
    svg.add(
        f'<text class="d {css_class}" x="{num(x + shift)}" y="{num(y)}" '
        f'font-size="{num(size)}" letter-spacing="{spacing}" text-anchor="{anchor}" '
        f'fill="{fill}" style="animation-delay:{num(delay)}s">{esc(text)}</text>'
    )
