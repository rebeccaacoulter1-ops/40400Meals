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


def build_slug(recipe_data, recipe_file):
    if "slug" in recipe_data:
        return recipe_data["slug"]

    if "recipe" in recipe_data and "slug" in recipe_data["recipe"]:
        return recipe_data["recipe"]["slug"]

    return recipe_file.stem


def normalize_recipe(data, recipe_file):
    slug = build_slug(data, recipe_file)

    if "recipe" in data:
        recipe = data["recipe"]
        seo = data.get("seo", {})
        images = data.get("images", {})
        social = data.get("social", {})

        return {
            "title": recipe.get("title", slug.replace("-", " ").title()),
            "summary": recipe.get("summary", ""),
            "category": recipe.get("category", "High Protein"),
            "protein": recipe.get("macros", {}).get("protein_g", ""),
            "calories": recipe.get("macros", {}).get("calories", ""),
            "carbs": recipe.get("macros", {}).get("carbs_g", ""),
            "fat": recipe.get("macros", {}).get("fat_g", ""),
            "prep_minutes": recipe.get("times", {}).get("prep_minutes", ""),
            "cook_minutes": recipe.get("times", {}).get("cook_minutes", ""),
            "total_minutes": recipe.get("times", {}).get("total_minutes", ""),
            "servings": recipe.get("servings", ""),
            "ingredients": recipe.get("ingredients", []),
            "instructions": recipe.get("instructions", []),
            "tips": recipe.get("tips", []),
            "hero_image_url": images.get("hero_image_url", ""),
            "alt_text": images.get("alt_text", recipe.get("title", "")),
            "meta_title": seo.get("meta_title", recipe.get("title", "")),
            "meta_description": seo.get("meta_description", recipe.get("summary", "")),
            "destination_url": social.get("pinterest", {}).get(
                "destination_url",
                f"https://40400meals.com/recipes/{slug}.html"
            ),
            "slug": slug,
        }

    return {
        "title": data.get("title", slug.replace("-", " ").title()),
        "summary": data.get("description", ""),
        "category": data.get("tags", ["High Protein"])[0] if data.get("tags") else "High Protein",
        "protein": data.get("protein", ""),
        "calories": data.get("calories", ""),
        "carbs": data.get("carbs", ""),
        "fat": data.get("fat", ""),
        "prep_minutes": data.get("prep_time", "").replace(" minutes", ""),
        "cook_minutes": data.get("cook_time", "").replace(" minutes", ""),
        "total_minutes": data.get("total_time", "").replace(" minutes", ""),
        "servings": data.get("servings", ""),
        "ingredients": data.get("ingredients", []),
        "instructions": data.get("instructions", []),
        "tips": data.get("tips", [
            "Adjust seasoning to taste.",
            "Prep ingredients ahead to make this recipe even faster.",
            "Store leftovers in an airtight container in the refrigerator."
        ]),
        "hero_image_url": data.get("image", ""),
        "alt_text": data.get("title", ""),
        "meta_title": data.get("pinterest_title", data.get("title", "")),
        "meta_description": data.get("pinterest_description", data.get("description", "")),
        "destination_url": f"https://40400meals.com/recipes/{slug}.html",
        "slug": slug,
    }


def build_ingredients_html(ingredients):
    lines = []

    for ingredient in ingredients:
        if isinstance(ingredient, dict):
            amount = ingredient.get("amount", "")
            unit = ingredient.get("unit", "")
            item = ingredient.get("item", "")
            line = f"{amount} {unit} {item}".strip()
        else:
            line = str(ingredient)

        lines.append(f"<li>{line}</li>")

    return "\n".join(lines)


def build_list_html(items):
    return "\n".join(f"<li>{item}</li>" for item in items)


def generate_recipe_page(recipe_file):
    data = load_json(recipe_file)
    html = load_template()
    recipe = normalize_recipe(data, recipe_file)

    replacements = {
        "{{seo.meta_title}}": recipe["meta_title"],
        "{{seo.meta_description}}": recipe["meta_description"],
        "{{recipe.title}}": recipe["title"],
        "{{recipe.summary}}": recipe["summary"],
        "{{recipe.category}}": recipe["category"],
        "{{recipe.macros.protein_g}}": str(recipe["protein"]),
        "{{recipe.macros.calories}}": str(recipe["calories"]),
        "{{recipe.macros.carbs_g}}": str(recipe["carbs"]),
        "{{recipe.macros.fat_g}}": str(recipe["fat"]),
        "{{recipe.times.prep_minutes}}": str(recipe["prep_minutes"]),
        "{{recipe.times.cook_minutes}}": str(recipe["cook_minutes"]),
        "{{recipe.times.total_minutes}}": str(recipe["total_minutes"]),
        "{{recipe.servings}}": str(recipe["servings"]),
        "{{images.hero_image_url}}": recipe["hero_image_url"],
        "{{images.alt_text}}": recipe["alt_text"],
        "{{social.pinterest.destination_url}}": recipe["destination_url"],
        "{{ingredients_list}}": build_ingredients_html(recipe["ingredients"]),
        "{{instructions_list}}": build_list_html(recipe["instructions"]),
        "{{tips_list}}": build_list_html(recipe["tips"]),
    }

    for key, value in replacements.items():
        html = html.replace(key, value)

    output_file = RECIPES_DIR / f"{recipe['slug']}.html"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print("Recipe page created!")
    print(output_file)


# -----------------------------
# Main process
# -----------------------------

recipe_files = sorted(RECIPES_DIR.glob("*.json"))

if not recipe_files:
    print("No recipe JSON files found.")
    quit()

for recipe_file in recipe_files:
    print(f"Generating page for {recipe_file}")
    generate_recipe_page(recipe_file)
