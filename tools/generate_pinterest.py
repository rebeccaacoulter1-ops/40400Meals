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

    "canva_template": design_template,

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
