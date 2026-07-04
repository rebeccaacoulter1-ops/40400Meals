import json
import shutil
from pathlib import Path

from drive_config import PLATFORM_FOLDERS


# -----------------------------
# File locations
# -----------------------------

RECIPES_DIR = Path("recipes")
DESIGN_TEMPLATE_FILE = Path("outputs/design/selected_template.json")


# -----------------------------
# Helper functions
# -----------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_design_template():
    if DESIGN_TEMPLATE_FILE.exists():
        return load_json(DESIGN_TEMPLATE_FILE)

    return {
        "platform": "pinterest",
        "template_name": "P01 Classic Recipe v1.0",
        "template_type": "evergreen",
        "season": "evergreen",
        "month": None,
        "recipe_category": "general",
        "image_style": "bright natural light",
        "photo_composition": "45-degree angle",
        "color_mood": "clean",
        "accent_colors": ["#FFFFFF", "#10B981", "#1F2937"],
        "text_style": "clean and modern",
        "overlay_style": "minimal",
        "icon_style": "minimal",
        "layout_recommendation": "P01 classic layout",
        "optimization": {
            "visual_appeal": "high",
            "save_potential": "high",
            "click_potential": "high"
        },
        "version": "1.0",
        "status": "fallback_template"
    }


def build_slug(data, recipe_file):
    if "slug" in data:
        return data["slug"]

    if "recipe" in data and "slug" in data["recipe"]:
        return data["recipe"]["slug"]

    return recipe_file.stem


def normalize_recipe(data, recipe_file):
    slug = build_slug(data, recipe_file)

    if "recipe" in data:
        recipe = data["recipe"]
        images = data.get("images", {})
        social = data.get("social", {})
        seo = data.get("seo", {})
        pinterest = social.get("pinterest", {})

        return {
            "recipe_id": data.get("recipe_id", slug),
            "slug": slug,
            "title": recipe.get("title", slug.replace("-", " ").title()),
            "protein": recipe.get("macros", {}).get("protein_g", ""),
            "calories": recipe.get("macros", {}).get("calories", ""),
            "pinterest_title": pinterest.get("title", recipe.get("title", "")),
            "pinterest_description": pinterest.get("description", recipe.get("summary", "")),
            "destination_url": pinterest.get(
                "destination_url",
                f"https://40400meals.com/recipes/{slug}.html"
            ),
            "hashtags": pinterest.get(
                "hashtags",
                ["#HighProteinRecipes", "#LowSugarRecipes", "#40400Meals"]
            ),
            "image_prompt": images.get(
                "image_prompt",
                f"Premium food blog photography of {recipe.get('title', '')}"
            ),
            "image_alt_text": images.get("alt_text", recipe.get("title", "")),
            "seo_keywords": seo.get(
                "keywords",
                ["high protein recipes", "low sugar recipes", "40400 meals"]
            ),
        }

    title = data.get("title", slug.replace("-", " ").title())
    description = data.get("description", "")

    return {
        "recipe_id": data.get("recipe_id", slug),
        "slug": slug,
        "title": title,
        "protein": data.get("protein", ""),
        "calories": data.get("calories", ""),
        "pinterest_title": data.get("pinterest_title", f"{title} | 40/400 Meals"),
        "pinterest_description": data.get("pinterest_description", description),
        "destination_url": f"https://40400meals.com/recipes/{slug}.html",
        "hashtags": data.get(
            "hashtags",
            ["#HighProteinRecipes", "#LowSugarRecipes", "#EasyDinner", "#40400Meals"]
        ),
        "image_prompt": data.get(
            "image_prompt",
            f"Premium food blog photography of {title}, bright natural light, clean neutral styling."
        ),
        "image_alt_text": data.get("image_alt_text", title),
        "seo_keywords": data.get(
            "seo_keywords",
            ["high protein recipes", "low sugar recipes", "macro friendly meals"]
        ),
    }


# -----------------------------
# Pinterest data builder
# -----------------------------

def build_pin_data(recipe, design_template):
    slug = recipe["slug"]

    return {
        "recipe_id": recipe["recipe_id"],
        "platform": "pinterest",
        "title": recipe["pinterest_title"],
        "description": recipe["pinterest_description"],
        "destination_url": recipe["destination_url"],
        "hashtags": recipe["hashtags"],
        "image_prompt": recipe["image_prompt"],
        "image_alt_text": recipe["image_alt_text"],
        "pin_filename": f"{slug}-pinterest-pin.png",
        "image_filename": f"{slug}-pinterest-pin.png",
        "image_path": f"outputs/images/pinterest/{slug}-pinterest-pin.png",
        "image_mime_type": "image/png",

        "design_brain": {
            "template_name": design_template.get("template_name"),
            "template_type": design_template.get("template_type"),
            "season": design_template.get("season"),
            "month": design_template.get("month"),
            "recipe_category": design_template.get("recipe_category"),
            "image_style": design_template.get("image_style"),
            "photo_composition": design_template.get("photo_composition"),
            "color_mood": design_template.get("color_mood"),
            "accent_colors": design_template.get("accent_colors"),
            "text_style": design_template.get("text_style"),
            "overlay_style": design_template.get("overlay_style"),
            "icon_style": design_template.get("icon_style"),
            "layout_recommendation": design_template.get("layout_recommendation"),
            "optimization": design_template.get("optimization"),
            "version": design_template.get("version"),
            "status": design_template.get("status")
        },

        "canva_text_overlay": {
            "headline": recipe["title"],
            "subheadline": f'{recipe["protein"]}g Protein • {recipe["calories"]} Calories',
            "brand": "40/400 Meals"
        },

        "seo_keywords": recipe["seo_keywords"],
        "status": "ready_for_make"
    }


def process_recipe(recipe_file, design_template):
    data = load_json(recipe_file)
    recipe = normalize_recipe(data, recipe_file)
    slug = recipe["slug"]

    pin_data = build_pin_data(recipe, design_template)

    pinterest_dir = PLATFORM_FOLDERS["pinterest"]
    make_queue_dir = PLATFORM_FOLDERS["make_queue"]

    pinterest_dir.mkdir(parents=True, exist_ok=True)
    make_queue_dir.mkdir(parents=True, exist_ok=True)

    pinterest_file = pinterest_dir / f"{slug}.json"
    make_queue_file = make_queue_dir / f"{slug}-pinterest.json"

    with open(pinterest_file, "w", encoding="utf-8") as f:
        json.dump(pin_data, f, indent=2)

    shutil.copyfile(pinterest_file, make_queue_file)

    print(f"Pinterest file created: {pinterest_file}")
    print(f"Make queue file created: {make_queue_file}")


# -----------------------------
# Main process
# -----------------------------

def main():
    design_template = load_design_template()
    recipe_files = sorted(RECIPES_DIR.glob("*.json"))

    if not recipe_files:
        print("No recipe JSON files found.")
        return

    for recipe_file in recipe_files:
        print(f"\nProcessing Pinterest package for {recipe_file}")
        process_recipe(recipe_file, design_template)


if __name__ == "__main__":
    main()
