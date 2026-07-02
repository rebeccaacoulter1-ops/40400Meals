import json
from datetime import datetime
from pathlib import Path

DESIGN_OUTPUT_DIR = Path("outputs/design")
DESIGN_OUTPUT_FILE = DESIGN_OUTPUT_DIR / "selected_template.json"


def get_seasonal_template(month):
    seasonal_templates = {
        1: "P01 Classic Recipe v1.0",
        2: "P11 Valentine's",
        3: "P01 Classic Recipe v1.0",
        4: "P12 Easter",
        5: "P05 Spring",
        6: "P06 Summer",
        7: "P06 Summer",
        8: "P01 Classic Recipe v1.0",
        9: "P07 Fall",
        10: "P08 Halloween",
        11: "P09 Thanksgiving",
        12: "P10 Christmas",
    }

    return seasonal_templates.get(month, "P01 Classic Recipe v1.0")


def choose_template(platform="pinterest", recipe_category="general"):
    today = datetime.now()
    month = today.month
    template = get_seasonal_template(month)

    return {
        "platform": platform,
        "template_name": template,
        "template_type": "seasonal" if template != "P01 Classic Recipe v1.0" else "evergreen",
        "month": month,
        "recipe_category": recipe_category,
        "version": "1.0",
        "status": "template_selected"
    }


def main():
    DESIGN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    selected = choose_template()

    with open(DESIGN_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(selected, f, indent=2)

    print("Bear OS Design Engine selected:")
    print(selected)
    print(f"Design template saved to: {DESIGN_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
