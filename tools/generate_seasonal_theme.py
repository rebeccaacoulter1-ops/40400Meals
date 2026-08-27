"""Applies the current season's accent colors to the site-wide stylesheet.

This closes the gap between tools/design_engine.py (which has always known
the correct season and its palette, and has used it for Pinterest pin
styling) and the actual website: until this script existed, nothing ever
took that seasonal palette and applied it to assets/site.css, so the live
site's colors never actually changed with the season.

Self-contained by design (matches every other tools/*.py in this repo --
no cross-module imports), so SEASON_NAMES/SEASON_PALETTES are duplicated
from design_engine.py rather than imported. If you add or change a season
there, mirror the change here too.

Safe to run every time the pipeline runs: it rewrites only the clearly
marked block below, so re-running it with the same month is a no-op.
"""

import re
from datetime import datetime
from pathlib import Path

CSS_FILE = Path("assets/site.css")

START_MARKER = "/* BEAR:SEASONAL-THEME:START */"
END_MARKER = "/* BEAR:SEASONAL-THEME:END */"

SEASON_NAMES = {
    1: "winter",
    2: "valentines",
    3: "spring",
    4: "easter",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "fall",
    9: "fall",
    10: "halloween",
    11: "thanksgiving",
    12: "christmas",
}

# background, accent (buttons/pills), deep-accent (reserved for future use)
SEASON_PALETTES = {
    "winter": ["#FFFFFF", "#3B82F6", "#1F2937"],
    "valentines": ["#FFF1F2", "#F472B6", "#7F1D1D"],
    "spring": ["#F0FDF4", "#22C55E", "#14532D"],
    "easter": ["#FEF3C7", "#A78BFA", "#166534"],
    "summer": ["#FFFFFF", "#06AED5", "#10B981"],
    "fall": ["#FFF7ED", "#F97316", "#7C2D12"],
    "halloween": ["#FFF7ED", "#F97316", "#111827"],
    "thanksgiving": ["#FFFBEB", "#B45309", "#78350F"],
    "christmas": ["#FFFFFF", "#B91C1C", "#166534"],
}


def build_theme_block():
    month = datetime.now().month
    season = SEASON_NAMES.get(month)
    palette = SEASON_PALETTES.get(season)

    if not palette:
        return ""

    background = palette[0]
    accent = palette[1] if len(palette) > 1 else palette[0]

    return (
        f"{START_MARKER}\n"
        f":root{{--cream:{background};--orange:{accent};}}\n"
        f"{END_MARKER}"
    )


def main():
    if not CSS_FILE.exists():
        raise FileNotFoundError(f"Stylesheet not found: {CSS_FILE}")

    css = CSS_FILE.read_text(encoding="utf-8")
    block = build_theme_block()

    pattern = re.compile(
        rf"\n?{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        flags=re.DOTALL,
    )

    if pattern.search(css):
        updated = pattern.sub(("\n" + block) if block else "", css, count=1)
    elif block:
        updated = css.rstrip("\n") + "\n" + block + "\n"
    else:
        updated = css

    if updated == css:
        print("Seasonal theme already current.")
        return

    CSS_FILE.write_text(updated, encoding="utf-8")
    print(f"Seasonal theme updated for {datetime.now().strftime('%B')}.")


if __name__ == "__main__":
    main()
