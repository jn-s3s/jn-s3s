"""Build the WOFF2 font subsets that the profile SVGs embed.

SVGs shown through an <img> tag cannot load external fonts, so every card
embeds these subsets as data URIs. This is a one-off developer tool and
CI never runs it. It needs `pip install fonttools brotli` and network
access to the google/fonts repository.

Usage:
    python scripts/build_fonts.py
"""

import io
import json
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

SOURCE_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "profile_kit" / "fonts"
MONO_WIDTH = 87.5
BASIC_LATIN = "U+0020-007E"
TEXT_UNICODES = f"{BASIC_LATIN},U+00A0-00FF,U+2013-2014,U+2018-201D,U+2022,U+2026"


def _download(path: str) -> bytes:
    with urllib.request.urlopen(f"{SOURCE_URL}/{path}", timeout=60) as response:
        return response.read()


def _write_subset(font: TTFont, unicodes: str, target: Path) -> None:
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["kern", "liga", "calt"]
    options.name_IDs = ["*"]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=subset.parse_unicodes(unicodes))
    subsetter.subset(font)
    font.flavor = "woff2"
    font.save(target)
    print(f"Wrote {target.name} ({target.stat().st_size} bytes)")


def _write_advances(font: TTFont, target: Path) -> None:
    """Save per-character advance widths in em, so layout code can measure text."""
    units = font["head"].unitsPerEm
    metrics = font["hmtx"]
    advances = {
        chr(code): round(metrics[glyph][0] / units, 4)
        for code, glyph in sorted(font.getBestCmap().items())
    }
    target.write_text(json.dumps(advances, indent=0) + "\n", encoding="utf-8")
    print(f"Wrote {target.name} ({len(advances)} characters)")


def main() -> None:
    """Download the source fonts, then write the subsets, metrics and licenses."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    mono_source = _download("martianmono/MartianMono%5Bwdth,wght%5D.ttf")
    for weight in (400, 700):
        variable = TTFont(io.BytesIO(mono_source))
        static = instancer.instantiateVariableFont(
            variable, {"wght": weight, "wdth": MONO_WIDTH}
        )
        _write_subset(
            static, TEXT_UNICODES, OUTPUT_DIR / f"martian-mono-{weight}.woff2"
        )

    display = TTFont(io.BytesIO(_download("michroma/Michroma-Regular.ttf")))
    _write_subset(display, BASIC_LATIN, OUTPUT_DIR / "michroma-400.woff2")
    _write_advances(display, OUTPUT_DIR / "michroma-advances.json")

    for family, license_name in (
        ("martianmono", "MartianMono"),
        ("michroma", "Michroma"),
    ):
        license_text = _download(f"{family}/OFL.txt")
        (OUTPUT_DIR / f"OFL-{license_name}.txt").write_bytes(license_text)


if __name__ == "__main__":
    main()
