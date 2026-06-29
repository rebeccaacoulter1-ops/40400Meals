import json
from pathlib import Path

RECIPE_FILE = Path("recipes/chocolate-protein-mug-cake.json")

with open(RECIPE_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

recipe = data["recipe"]
images = data["images"]
social = data["social"]
seo = data["seo"]

slug = recipe["slug"]

output_dir = Path("outputs") / slug / "pinterest"
output_dir.mkdir(parents=True, exist_ok=True)

pin_data = {
    "recipe_id": data["recipe_id"],
    "title": social["pinterest"]["title"],
    "description": social["pinterest"]["description"],
    "destination_url": social["pinterest"]["destination_url"],
    "hashtags": social["pinterest"]["hashtags"],
    "image_prompt": images["image_prompt"],
    "image_alt_text": images["alt_text"],
    "pin_filename": f"{slug}-pinterest-pin.png",
    "canva_text_overlay": {
        "headline": recipe["title"],
        "subheadline": f'{recipe["macros"]["protein_g"]}g Protein • {recipe["macros"]["calories"]} Calories',
        "brand": "40/400 Meals"
    },
    "seo_keywords": seo["keywords"],
    "status": "ready_for_make"
}

output_file = output_dir / "pinterest.json"

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(pin_data, f, indent=2)

print(f"Pinterest file created: {output_file}")
