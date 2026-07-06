import json
from pathlib import Path


# -----------------------------
# File locations
# -----------------------------

RECIPES_DIR = Path("recipes")
TEMPLATE_FILE = Path("templates/recipe-template.html")


# -----------------------------
# Helper functions
# -----------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_template():
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        return f.read()


def get_nested_value(data, key_path, default=""):
    keys = key_path.split(".")
    value = data

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value


def replace_nested_placeholders(template, data):
    output = template

    placeholders = [
        "seo.meta_title",
        "seo.meta_description",
        "recipe.category",
        "recipe.times.total_minutes",
        "recipe.title",
        "recipe.summary",
        "recipe.macros.protein_g",
        "recipe.macros.calories",
        "recipe.macros.carbs_g",
        "recipe.macros.fat_g",
        "recipe.times.prep_minutes",
        "recipe.times.cook_minutes",
        "recipe.servings",
        "images.hero_image_url",
        "images.alt_text",
        "social.pinterest.destination_url",
    ]

    for placeholder in placeholders:
        value = get_nested_value(data, placeholder, "")
        output = output.replace("{{" + placeholder + "}}", str(value))

    return output


def build_list_items(items):
    if not isinstance(items, list):
        return ""

    return "\n".join(f"<li>{item}</li>" for item in items)


def get_slug(data, recipe_file):
    if "slug" in data:
        return data["slug"]

    if "recipe" in data and "slug" in data["recipe"]:
        return data["recipe"]["slug"]

    return recipe_file.stem


# -----------------------------
# Page generator
# -----------------------------

def generate_recipe_page(recipe_file, template):
    data = load_json(recipe_file)
    slug = get_slug(data, recipe_file)

    html = replace_nested_placeholders(template, data)

    ingredients = get_nested_value(data, "recipe.ingredients", [])
    instructions = get_nested_value(data, "recipe.instructions", [])
    tips = get_nested_value(data, "recipe.tips", [])

    html = html.replace("{{ingredients_list}}", build_list_items(ingredients))
    html = html.replace("{{instructions_list}}", build_list_items(instructions))
    html = html.replace("{{tips_list}}", build_list_items(tips))

    output_file = RECIPES_DIR / f"{slug}.html"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Recipe page created: {output_file}")


# -----------------------------
# Main process
# -----------------------------

def main():
    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(f"Missing template file: {TEMPLATE_FILE}")

    template = load_template()
    recipe_files = sorted(RECIPES_DIR.glob("*.json"))

    if not recipe_files:
        print("No recipe JSON files found.")
        return

    for recipe_file in recipe_files:
        print(f"\nGenerating HTML page for {recipe_file}")
        generate_recipe_page(recipe_file, template)


if __name__ == "__main__":
    main()
