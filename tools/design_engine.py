import json
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("outputs/design")
OUTPUT_FILE = OUTPUT_DIR / "selected_template.json"

SEASON_TEMPLATES = {
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

SEASON_NAMES = {
    1: "winter",
    2: "valentines",
    3: "spring",
    4: "easter",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "fall",
    10: "halloween",
    11: "thanksgiving",
    12: "christmas",
}

SEASON_PALETTES = {
    "winter": ["#FFFFFF", "#E8F1F2", "#1F2937"],
    "valentines": ["#FFF1F2", "#F472B6", "#7F1D1D"],
    "spring": ["#F0FDF4", "#86EFAC", "#14532D"],
    "easter": ["#FEF3C7", "#C4B5FD", "#166534"],
    "summer": ["#FFFFFF", "#FFD166", "#06AED5", "#10B981"],
    "fall": ["#FFF7ED", "#F97316", "#7C2D12"],
    "halloween": ["#111827", "#F97316", "#FFFFFF"],
    "thanksgiving": ["#FFFBEB", "#B45309", "#78350F"],
    "christmas": ["#FFFFFF", "#B91C1C", "#166534"],
}

CATEGORY_STYLES = {
    "breakfast": {
        "image_style": "bright natural light",
        "photo_composition": "top-down",
        "text_style": "clean and modern",
        "overlay_style": "minimal",
        "energy": "fresh and energetic",
    },
    "lunch": {
        "image_style": "bright realistic food photography",
        "photo_composition": "45-degree angle",
        "text_style": "bold and readable",
        "overlay_style": "clean",
        "energy": "simple and practical",
    },
    "dinner": {
        "image_style": "warm realistic food photography",
        "photo_composition": "45-degree angle",
        "text_style": "premium and trustworthy",
        "overlay_style": "minimal",
        "energy": "satisfying and family-friendly",
    },
    "dessert": {
        "image_style": "cozy realistic food photography",
        "photo_composition": "close-up",
        "text_style": "bold and modern",
        "overlay_style": "clean",
        "energy": "indulgent but goal-friendly",
    },
    "snack": {
        "image_style": "bright simple food photography",
        "photo_composition": "close-up",
        "text_style": "simple and bold",
        "overlay_style": "minimal",
        "energy": "quick and easy",
    },
    "general": {
        "image_style": "bright natural light",
        "photo_composition": "45-degree angle",
        "text_style": "clean and modern",
        "overlay_style": "minimal",
        "energy": "healthy and trustworthy",
    },
}


def get_recipe_category():
    return "general"


def choose_design_strategy(platform="pinterest"):
    today = datetime.now()
    month = today.month

    season = SEASON_NAMES.get(month, "evergreen")
    template_name = SEASON_TEMPLATES.get(month, "P01 Classic Recipe v1.0")
    recipe_category = get_recipe_category()
    category_style = CATEGORY_STYLES.get(recipe_category, CATEGORY_STYLES["general"])
    palette = SEASON_PALETTES.get(season, ["#FFFFFF", "#10B981", "#1F2937"])

    return {
        "platform": platform,
        "template_name": template_name,
        "template_type": "seasonal" if template_name != "P01 Classic Recipe v1.0" else "evergreen",
        "season": season,
        "month": month,
        "recipe_category": recipe_category,
        "image_style": category_style["image_style"],
        "photo_composition": category_style["photo_composition"],
        "color_mood": season,
        "accent_colors": palette,
        "text_style": category_style["text_style"],
        "overlay_style": category_style["overlay_style"],
        "icon_style": "minimal",
        "layout_recommendation": "P01 classic layout",
        "optimization": {
            "visual_appeal": "high",
            "save_potential": "high",
            "click_potential": "high",
        },
        "version": "1.0",
        "status": "design_strategy_ready",
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    design_strategy = choose_design_strategy()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(design_strategy, f, indent=2)

    print("Bear OS Visual Design Brain selected:")
    print(design_strategy)
    print(f"Design strategy saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
