"""Hero banner: operator name, the encrypted bio transmission and a radar scope."""

import math
import random
import zlib

from profile_kit.github_api import Repo, UserProfile
from profile_kit.svg import (
    AMBER,
    CYAN,
    GREEN,
    LINE,
    LINE_STRONG,
    MARGIN,
    MONO_ADVANCE,
    TEXT_DIM,
    TEXT_HI,
    TEXT_MID,
    Svg,
    display_width,
    esc,
    frame,
    label,
    label_spacing,
    mono_width,
    num,
    typed_text,
    wrap,
)

WIDTH, HEIGHT = 840, 300
TRANSMISSION_LABEL = "INCOMING TRANSMISSION // ENCRYPTED"
SCRAMBLE_GLYPHS = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#%+=/<>"
NAME_SIZE, NAME_SPACING = 58, 6
BIO_SIZE, BIO_LINE = 13, 19
LEFT = 28
TEXT_RIGHT = 548
RADAR_X, RADAR_Y, RADAR_R = 700, 150, 104
SWEEP_SECONDS = 6

HERO_CSS = """
@media (prefers-reduced-motion:no-preference){
.scr{animation:scr 70ms steps(1)}
.fin{animation:fade 60ms linear both}
.sweep{animation:spin 6s linear infinite}
.blip{animation:blip 6s linear infinite}
.twinkle{animation:twinkle 4s ease-in-out infinite}
.glitch-a{animation:glitch-a 9s steps(1) infinite}
.glitch-b{animation:glitch-b 9s steps(1) infinite}
}
.glitch-a,.glitch-b{opacity:0}
@keyframes scr{from,to{opacity:1}}
@keyframes blip{0%{opacity:1}55%,100%{opacity:.18}}
@keyframes twinkle{50%{opacity:.08}}
@keyframes glitch-a{0%{opacity:.75;transform:translate(-4px,0)}
1.4%{transform:translate(3px,-1px)}2.8%,100%{opacity:0;transform:none}}
@keyframes glitch-b{0%{opacity:.6;transform:translate(4px,1px)}
1.4%{transform:translate(-2px,0)}2.8%,100%{opacity:0;transform:none}}
"""


def _polar(radius: float, degrees: float) -> tuple[float, float]:
    """Point on the radar at `degrees` clockwise from north."""
    angle = math.radians(degrees)
    return RADAR_X + radius * math.sin(angle), RADAR_Y - radius * math.cos(angle)


def _stars(svg: Svg, rng: random.Random) -> None:
    dots = []
    for index in range(46):
        x = rng.uniform(MARGIN + 12, WIDTH - MARGIN - 12)
        y = rng.uniform(MARGIN + 34, HEIGHT - MARGIN - 10)
        radius = rng.uniform(0.35, 1.05)
        opacity = rng.uniform(0.12, 0.45)
        twinkle = ""
        if index % 5 == 0:
            twinkle = (
                f' class="twinkle" style="animation-delay:-{num(rng.uniform(0, 4))}s;'
                f'animation-duration:{num(rng.uniform(3, 6))}s"'
            )
        dots.append(
            f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(radius)}" '
            f'fill="{TEXT_HI}" opacity="{num(opacity)}"{twinkle}/>'
        )
    svg.add("".join(dots))


def _scanlines(svg: Svg) -> None:
    pattern = svg.uid("lines")
    svg.defs.append(
        f'<pattern id="{pattern}" width="4" height="3" patternUnits="userSpaceOnUse">'
        f'<rect width="4" height="1" fill="{TEXT_HI}" opacity=".022"/></pattern>'
    )
    svg.add(
        f'<rect x="{MARGIN}" y="{MARGIN}" width="{WIDTH - 2 * MARGIN}" '
        f'height="{HEIGHT - 2 * MARGIN}" fill="url(#{pattern})"/>'
    )


def _ruler(svg: Svg) -> None:
    ticks = []
    for index, y in enumerate(range(52, 262, 8)):
        length = 7 if index % 5 == 0 else 3.5
        ticks.append(f"M{MARGIN + 8},{y}h{length}")
    svg.add(f'<path class="fade" d="{"".join(ticks)}" stroke="{LINE_STRONG}"/>')


def _name(svg: Svg, name: str, rng: random.Random) -> None:
    """Draw the operator name: a scramble that locks onto each letter."""
    baseline = 110
    gradient, slices = svg.uid("name"), svg.uid("slices")
    svg.defs.append(
        f'<linearGradient id="{gradient}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset=".2" stop-color="#ffffff"/>'
        f'<stop offset="1" stop-color="#8fd8ff"/></linearGradient>'
        f'<clipPath id="{slices}">'
        f'<rect x="0" y="{baseline - 44}" width="{WIDTH}" height="9"/>'
        f'<rect x="0" y="{baseline - 24}" width="{WIDTH}" height="6"/>'
        f'<rect x="0" y="{baseline - 12}" width="{WIDTH}" height="10"/></clipPath>'
    )
    centers = []
    cursor = LEFT
    for char in name:
        advance = display_width(char, NAME_SIZE)
        centers.append(cursor + advance / 2)
        cursor += advance + NAME_SPACING

    glow, scramble, final, glitch = [], [], [], []
    for index, (char, center) in enumerate(zip(name, centers, strict=True)):
        lock = 0.45 + index * 0.13
        place = f'x="{num(center)}" y="{baseline}"'
        for step in range(5):
            glyph = rng.choice(SCRAMBLE_GLYPHS)
            moment = lock - (5 - step) * 0.07
            scramble.append(
                f'<text class="scr" {place} '
                f'style="animation-delay:{num(moment)}s">{esc(glyph)}</text>'
            )
        style = f'style="animation-delay:{num(lock)}s"'
        glow.append(f'<text class="fin" {place} {style}>{esc(char)}</text>')
        final.append(f'<text class="fin" {place} {style}>{esc(char)}</text>')
        glitch.append(f"<text {place}>{esc(char)}</text>")

    common = f'class="d" font-size="{NAME_SIZE}" text-anchor="middle"'
    svg.add(
        f'<g {common} stroke="{CYAN}" stroke-opacity=".10" stroke-width="9" '
        f'stroke-linejoin="round" fill="{CYAN}" fill-opacity=".05">{"".join(glow)}</g>',
        f'<g {common} fill="{CYAN}">{"".join(scramble)}</g>',
        f'<g {common} fill="url(#{gradient})">{"".join(final)}</g>',
    )
    for css_class, color in (("glitch-a", CYAN), ("glitch-b", AMBER)):
        svg.add(
            f'<g clip-path="url(#{slices})"><g class="{css_class}" '
            f'style="animation-delay:3.2s"><g {common} fill="{color}">'
            f"{''.join(glitch)}</g></g></g>"
        )


def _identity_rule(svg: Svg, profile: UserProfile) -> None:
    joined = profile.created_at.strftime("%Y.%m.%d")
    caption = f"OPERATOR #{profile.user_id} // ACTIVE SINCE {joined}"
    svg.add(
        f'<text class="fade" x="{LEFT}" y="136" font-size="9.5" letter-spacing="1.4" '
        f'fill="{TEXT_MID}" style="animation-delay:1.3s">{esc(caption)}</text>'
    )
    track_end = TEXT_RIGHT
    ticks = "".join(f"M{x},152v3" for x in range(LEFT, track_end + 1, 16))
    svg.add(
        f'<path d="M{LEFT},150H{track_end}" stroke="{LINE_STRONG}"/>',
        f'<path class="fade" d="{ticks}" stroke="{LINE_STRONG}" '
        f'style="animation-delay:1.2s"/>',
        f'<rect class="grow" x="{LEFT}" y="149" width="{track_end - LEFT}" '
        f'height="2" fill="{AMBER}" fill-opacity=".45" style="animation-delay:1.15s"/>',
        f'<rect class="grow" x="{LEFT}" y="147.5" width="74" height="5" '
        f'fill="{AMBER}" style="animation-delay:1.15s"/>',
    )


def _transmission(svg: Svg, bio: str) -> None:
    """Type the bio out as a transmission and park a blinking cursor after it."""
    lock_x, label_y = LEFT, 178
    svg.add(
        f'<g class="fade" style="animation-delay:1.6s" stroke="{AMBER}" '
        f'stroke-width="1.3"><rect x="{lock_x}" y="{label_y - 6}" width="8" '
        f'height="6.5" rx="1"/><path d="M{lock_x + 1.8},{label_y - 6}v-2.2'
        f'a2.2,2.2 0 0 1 4.4,0v2.2"/></g>'
    )
    label(
        svg,
        TRANSMISSION_LABEL,
        x=lock_x + 16,
        y=label_y,
        size=8,
        fill=AMBER,
        delay=1.6,
    )

    prefix = "> "
    columns = int((TEXT_RIGHT - LEFT) / (MONO_ADVANCE * BIO_SIZE)) - len(prefix)
    lines = wrap(bio, columns, 3) or ["No transmission received."]
    svg.add(
        f'<text class="fade" x="{LEFT}" y="{label_y + 26}" font-size="{BIO_SIZE}" '
        f'font-weight="700" fill="{AMBER}" style="animation-delay:1.8s">'
        f"{esc(prefix.strip())}</text>"
    )
    moment = 1.95
    text_x = LEFT + mono_width(prefix, BIO_SIZE)
    for index, line in enumerate(lines):
        y = label_y + 26 + index * BIO_LINE
        moment = typed_text(
            svg,
            line,
            x=text_x,
            y=y,
            size=BIO_SIZE,
            fill=TEXT_HI,
            start=moment,
            pace=0.034,
        )
    last_y = label_y + 26 + (len(lines) - 1) * BIO_LINE
    cursor_x = text_x + mono_width(lines[-1] + " ", BIO_SIZE)
    svg.add(
        f'<rect class="blink" x="{num(cursor_x)}" y="{last_y - 11}" width="8" '
        f'height="13" fill="{AMBER}" style="animation-delay:{num(moment)}s"/>'
    )


def _chips(svg: Svg, chips: list[tuple[str, str]]) -> None:
    x, top = LEFT, 262
    for index, (caption, value) in enumerate(chips):
        delay = 2.0 + index * 0.12
        label(svg, caption, x=x, y=top, delay=delay, css_class="rise")
        svg.add(
            f'<text class="rise" x="{x}" y="{top + 17}" font-size="10.5" '
            f'font-weight="700" fill="{TEXT_HI}" style="animation-delay:{num(delay)}s">'
            f"{esc(value)}</text>"
        )
        width = max(
            display_width(caption, 8, label_spacing(8)), mono_width(value, 10.5)
        )
        x += width + 28
        if index < len(chips) - 1:
            svg.add(f'<path d="M{num(x - 14)},{top - 7}v26" stroke="{LINE_STRONG}"/>')


def _radar(svg: Svg, repos: list[Repo]) -> None:
    """Draw the radar scope; each featured module shows up as a blip."""
    disc = svg.uid("disc")
    svg.defs.append(
        f'<radialGradient id="{disc}"><stop offset="0" stop-color="{CYAN}" '
        f'stop-opacity=".10"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>'
        f"</radialGradient>"
    )
    origin = f"transform-origin:{RADAR_X}px {RADAR_Y}px"
    parts = [
        f'<circle cx="{RADAR_X}" cy="{RADAR_Y}" r="{RADAR_R}" fill="url(#{disc})"/>',
        f'<circle cx="{RADAR_X}" cy="{RADAR_Y}" r="{RADAR_R}" stroke="{LINE_STRONG}"/>',
    ]
    for radius in (26, 52, 78):
        parts.append(
            f'<circle cx="{RADAR_X}" cy="{RADAR_Y}" r="{radius}" stroke="{LINE}"/>'
        )
    parts.append(
        f'<path d="M{RADAR_X - RADAR_R},{RADAR_Y}H{RADAR_X + RADAR_R}'
        f'M{RADAR_X},{RADAR_Y - RADAR_R}V{RADAR_Y + RADAR_R}" stroke="{LINE}" '
        f'stroke-dasharray="2 4"/>'
    )
    ticks = []
    for degrees in range(0, 360, 6):
        inner = RADAR_R - (9 if degrees % 30 == 0 else 4)
        x1, y1 = _polar(inner, degrees)
        x2, y2 = _polar(RADAR_R, degrees)
        ticks.append(f"M{num(x1)},{num(y1)}L{num(x2)},{num(y2)}")
    parts.append(
        f'<path d="{"".join(ticks)}" stroke="{TEXT_DIM}" stroke-opacity=".7"/>'
    )
    for degrees, text in ((0, "000"), (90, "090"), (180, "180"), (270, "270")):
        x, y = _polar(RADAR_R - 17, degrees)
        parts.append(
            f'<text x="{num(x)}" y="{num(y + 2.5)}" font-size="8" text-anchor="middle" '
            f'fill="{TEXT_DIM}">{text}</text>'
        )
    parts.append(
        f'<g class="spin" style="{origin}"><circle cx="{RADAR_X}" cy="{RADAR_Y}" '
        f'r="{RADAR_R - 13}" stroke="{CYAN}" stroke-opacity=".35" '
        f'stroke-dasharray="1.5 7"/></g>'
    )
    arc_a = _polar(64, -30)
    arc_b = _polar(64, 30)
    arc_c = _polar(64, 150)
    arc_d = _polar(64, 210)
    parts.append(
        f'<g class="spin" style="{origin};animation-duration:16s;'
        f'animation-direction:reverse"><path d="M{num(arc_a[0])},{num(arc_a[1])}'
        f"A64,64 0 0 1 {num(arc_b[0])},{num(arc_b[1])}M{num(arc_c[0])},{num(arc_c[1])}"
        f'A64,64 0 0 1 {num(arc_d[0])},{num(arc_d[1])}" stroke="{AMBER}" '
        f'stroke-opacity=".55" stroke-width="1.5"/></g>'
    )

    wedges = []
    slices, span = 14, 4
    for index in range(slices):
        start = _polar(RADAR_R, -(index + 1) * span)
        end = _polar(RADAR_R, -index * span)
        opacity = 0.26 * (1 - index / slices) ** 1.6
        wedges.append(
            f'<path d="M{RADAR_X},{RADAR_Y}L{num(start[0])},{num(start[1])}'
            f'A{RADAR_R},{RADAR_R} 0 0 1 {num(end[0])},{num(end[1])}Z" '
            f'fill="{CYAN}" fill-opacity="{num(opacity)}"/>'
        )
    tip = _polar(RADAR_R, 0)
    parts.append(
        f'<g class="sweep" style="{origin}">{"".join(wedges)}'
        f'<path d="M{RADAR_X},{RADAR_Y}L{num(tip[0])},{num(tip[1])}" stroke="{CYAN}" '
        f'stroke-width="1.4"/></g>'
    )

    for index, repo in enumerate(repos[:6]):
        seed = zlib.crc32(repo.name.encode("utf-8"))
        degrees = (seed % 360 + index * 97) % 360
        radius = 30 + (seed >> 9) % 62
        x, y = _polar(radius, degrees)
        delay = num(SWEEP_SECONDS * degrees / 360 - SWEEP_SECONDS)
        parts.extend(
            (
                f'<g class="blip" style="animation-delay:{delay}s">'
                f'<circle cx="{num(x)}" cy="{num(y)}" r="2.6" fill="{AMBER}"/>'
                f'<circle cx="{num(x)}" cy="{num(y)}" r="6" stroke="{AMBER}" '
                f'stroke-opacity=".5"/></g>',
                f'<text x="{num(x + 9)}" y="{num(y + 2.5)}" font-size="8" '
                f'fill="{TEXT_MID}">M{index + 1:02d}</text>',
            )
        )

    orbit = _polar(RADAR_R, 0)
    parts.append(
        f'<g class="spin" style="{origin};animation-duration:22s">'
        f'<circle cx="{num(orbit[0])}" cy="{num(orbit[1])}" r="2.2" fill="{TEXT_HI}"/></g>',
    )
    parts.append(
        f'<circle class="halo" cx="{RADAR_X}" cy="{RADAR_Y}" r="3" fill="{GREEN}"/>'
        f'<circle cx="{RADAR_X}" cy="{RADAR_Y}" r="3" fill="{GREEN}"/>'
    )
    svg.add(f'<g class="fade" style="animation-delay:.3s">{"".join(parts)}</g>')
    label(
        svg, "SCANNING 127.0.0.1", x=RADAR_X, y=RADAR_Y + RADAR_R + 20, anchor="middle"
    )


def featured_stack(repos: list[Repo]) -> str:
    """Featured languages in order of first use, capped at three plus a count."""
    names = list(dict.fromkeys(repo.language for repo in repos if repo.language))
    stack = " / ".join(name.upper() for name in names[:3])
    if len(names) > 3:
        stack += f" +{len(names) - 3}"
    return stack


def render_hero(profile: UserProfile, repos: list[Repo]) -> str:
    """Build the animated hero banner SVG for `profile`.

    The featured repositories become radar blips and the stack chip.
    """
    rng = random.Random(profile.login)
    svg = Svg(
        WIDTH,
        HEIGHT,
        title=f"{profile.login} - operator profile",
        description=f"{profile.login}. {profile.bio}".strip(),
        css=[HERO_CSS],
    )
    frame(svg, "MISSION CONTROL // OPERATOR PROFILE", "UPLINK ONLINE", GREEN)
    _scanlines(svg)
    _stars(svg, rng)
    _ruler(svg)
    _radar(svg, repos)
    _name(svg, profile.login.upper(), rng)
    _identity_rule(svg, profile)
    _transmission(svg, profile.bio)

    chips = [
        ("LOCATION", profile.location or "unknown"),
        ("ONLINE SINCE", str(profile.created_at.year)),
        ("PUBLIC REPOS", str(profile.public_repos)),
    ]
    stack = featured_stack(repos)
    if stack:
        chips.append(("FEATURED STACK", stack))
    _chips(svg, chips)
    return svg.render()
