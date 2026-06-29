import json
from pathlib import Path

# -----------------------------
# File locations
# -----------------------------

RECIPE_FILE = Path("recipes/chocolate-protein-mug-cake.json")
TEMPLATE_FILE = Path("templates/recipe-template.html")
OUTPUT_FILE = Path("recipes/chocolate-protein-mug-cake.html")


# -----------------------------
# Load JSON
# -----------------------------

with open(RECIPE_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)


# -----------------------------
# Load HTML Template
# -----------------------------

with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
    html = f.read()


recipe = data["recipe"]
seo = data["seo"]
images = data["images"]
social = data["social"]


# -----------------------------
# Build Ingredients HTML
# -----------------------------

ingredients_html = ""

for ingredient in recipe["ingredients"]:

    amount = ingredient["amount"]
    unit = ingredient["unit"]
    item = ingredient["item"]

    line = f"<li>{amount} {unit} {item}</li>"

    ingredients_html += line + "\n"


# -----------------------------
# Build Instructions HTML
# -----------------------------

instructions_html = ""

for step in recipe["instructions"]:

    instructions_html += f"<li>{step}</li>\n"


# -----------------------------
# Build Tips HTML
# -----------------------------

tips_html = ""

for tip in recipe["tips"]:

    tips_html += f"<li>{tip}</li>\n"


# -----------------------------
# Replace Template Variables
# -----------------------------

replacements = {

    "{{seo.meta_title}}":
        seo["meta_title"],

    "{{seo.meta_description}}":
        seo["meta_description"],

    "{{recipe.title}}":
        recipe["title"],

    "{{recipe.summary}}":
        recipe["summary"],

    "{{recipe.category}}":
        recipe["category"],

    "{{recipe.macros.protein_g}}":
        str(recipe["macros"]["protein_g"]),

    "{{recipe.macros.calories}}":
        str(recipe["macros"]["calories"]),

    "{{recipe.macros.carbs_g}}":
        str(recipe["macros"]["carbs_g"]),

    "{{recipe.macros.fat_g}}":
        str(recipe["macros"]["fat_g"]),

    "{{recipe.times.prep_minutes}}":
        str(recipe["times"]["prep_minutes"]),

    "{{recipe.times.cook_minutes}}":
        str(recipe["times"]["cook_minutes"]),

    "{{recipe.times.total_minutes}}":
        str(recipe["times"]["total_minutes"]),

    "{{recipe.servings}}":
        str(recipe["servings"]),

    "{{images.hero_image_url}}":
        images["hero_image_url"],

    "{{images.alt_text}}":
        images["alt_text"],

    "{{social.pinterest.destination_url}}":
        social["pinterest"]["destination_url"],

    "{{ingredients_list}}":
        ingredients_html,

    "{{instructions_list}}":
        instructions_html,

    "{{tips_list}}":
        tips_html,
}


for key, value in replacements.items():

    html = html.replace(key, value)


# -----------------------------
# Save Finished HTML
# -----------------------------

OUTPUT_FILE.parent.mkdir(exist_ok=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    f.write(html)


print("Recipe page created!")
print(OUTPUT_FILE)
