import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from drive_config import PLATFORM_FOLDERS
from design_engine import CATEGORY_STYLES, normalize_recipe_category


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
            "category": recipe.get("category", ""),
            "published_at": data.get("homepage", {}).get(
                "published_at",
                recipe.get("date_published", ""),
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
        "category": data.get("category", ""),
        "published_at": data.get("published_at", data.get("date_published", "")),
    }


# -----------------------------
# Pinterest data builder
# -----------------------------

PIN_VARIANTS = (
    {"number": 1, "template": "classic", "offset_days": 0, "hook": "recipe"},
    {"number": 2, "template": "editorial", "offset_days": 3, "hook": "benefit"},
    {"number": 3, "template": "food_first", "offset_days": 7, "hook": "macros"},
    {"number": 4, "template": "benefit", "offset_days": 11, "hook": "save"},
)


def parse_published_at(value):
    text = str(value or "").strip()
    if not text:
        return datetime.now().astimezone()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now().astimezone()


def add_variant_tracking(url, variant_number, template):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({
        "utm_source": "pinterest",
        "utm_medium": "organic_social",
        "utm_campaign": "recipe_variations",
        "utm_content": f"v{variant_number}-{template}",
    })
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def variant_headline(recipe, hook):
    category = normalize_recipe_category(recipe.get("category"))
    if hook == "macros":
        return f'{recipe["protein"]}g Protein • {recipe["calories"]} Calories'
    if hook == "save":
        return f'Save This Easy {category.title()} Recipe'
    if hook == "benefit":
        return f'Easy High-Protein {category.title()}'
    return recipe["title"]


def build_pin_data(recipe, design_template, variant):
    slug = recipe["slug"]
    number = variant["number"]
    template = variant["template"]
    category = normalize_recipe_category(recipe.get("category"))
    category_style = CATEGORY_STYLES.get(category, CATEGORY_STYLES["general"])
    legacy = number == 1
    file_stem = f"{slug}-pinterest-pin" if legacy else f"{slug}-pinterest-v{number}"
    scheduled_at = parse_published_at(recipe.get("published_at")) + timedelta(
        days=variant["offset_days"]
    )

    return {
        "recipe_id": recipe["recipe_id"],
        "platform": "pinterest",
        "title": variant_headline(recipe, variant["hook"]),
        "description": recipe["pinterest_description"],
        "destination_url": add_variant_tracking(
            recipe["destination_url"], number, template
        ),
        "hashtags": recipe["hashtags"],
        "image_prompt": recipe["image_prompt"],
        "image_alt_text": recipe["image_alt_text"],
        "variant_id": f"v{number}",
        "variant_number": number,
        "scheduled_at": scheduled_at.isoformat(),
        "pin_template": template,
        "pin_headline": variant_headline(recipe, variant["hook"]),
        "pin_filename": f"{file_stem}.png",
        "image_filename": f"{file_stem}.png",
        "image_path": f"outputs/images/pinterest/{file_stem}.png",
        "image_mime_type": "image/png",

        "design_brain": {
            "template_name": design_template.get("template_name"),
            "template_type": design_template.get("template_type"),
            "season": design_template.get("season"),
            "month": design_template.get("month"),
            "recipe_category": category,
            "image_style": category_style["image_style"],
            "photo_composition": category_style["photo_composition"],
            "color_mood": design_template.get("color_mood"),
            "accent_colors": design_template.get("accent_colors"),
            "text_style": design_template.get("text_style"),
            "overlay_style": design_template.get("overlay_style"),
            "icon_style": design_template.get("icon_style"),
            "layout_recommendation": template,
            "optimization": design_template.get("optimization"),
            "version": design_template.get("version"),
            "status": design_template.get("status")
        },

        "canva_text_overlay": {
            "headline": variant_headline(recipe, variant["hook"]),
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

    pinterest_dir = PLATFORM_FOLDERS["pinterest"]
    make_queue_dir = PLATFORM_FOLDERS["make_queue"]

    pinterest_dir.mkdir(parents=True, exist_ok=True)
    make_queue_dir.mkdir(parents=True, exist_ok=True)

    for variant in PIN_VARIANTS:
        pin_data = build_pin_data(recipe, design_template, variant)
        number = variant["number"]
        legacy = number == 1
        metadata_name = f"{slug}.json" if legacy else f"{slug}-v{number}.json"
        queue_name = (
            f"{slug}-pinterest.json"
            if legacy
            else f"{slug}-pinterest-v{number}.json"
        )
        pinterest_file = pinterest_dir / metadata_name
        make_queue_file = make_queue_dir / queue_name

        with open(pinterest_file, "w", encoding="utf-8") as f:
            json.dump(pin_data, f, indent=2)

        shutil.copyfile(pinterest_file, make_queue_file)
        print(f"Pinterest variant created: {pinterest_file}")
        print(f"Make queue variant created: {make_queue_file}")


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
