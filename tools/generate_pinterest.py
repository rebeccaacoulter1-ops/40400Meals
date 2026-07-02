import json
import shutil
from pathlib import Path
from drive_config import PLATFORM_FOLDERS

RECIPE_FILE = Path("recipes/chocolate-protein-mug-cake.json")
DESIGN_TEMPLATE_FILE = Path("outputs/design/selected_template.json")

with open(RECIPE_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

recipe = data["recipe"]
images = data["images"]
social = data["social"]
seo = data["seo"]

slug = recipe["slug"]

if DESIGN_TEMPLATE_FILE.exists():
    with open(DESIGN_TEMPLATE_FILE, "r", encoding="utf-8") as f:
        design_template = json.load(f)
else:
    design_template = {
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

pin_data = {
    "recipe_id": data["recipe_id"],
    "platform": "pinterest",
    "title": social["pinterest"]["title"],
    "description": social["pinterest"]["description"],
    "destination_url": social["pinterest"]["destination_url"],
    "hashtags": social["pinterest"]["hashtags"],
    "image_prompt": images["image_prompt"],
    "image_alt_text": images["alt_text"],
    "pin_filename": f"{slug}-pinterest-pin.png",

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
        "subheadline": f'{recipe["macros"]["protein_g"]}g Protein • {recipe["macros"]["calories"]} Calories',
        "brand": "40/400 Meals"
    },

    "seo_keywords": seo["keywords"],
    "status": "ready_for_make"
}

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
