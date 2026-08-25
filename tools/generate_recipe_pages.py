import html
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
        "recipe.macros.sugar_g",
        "recipe.macros.fiber_g",
        "recipe.times.prep_minutes",
        "recipe.times.cook_minutes",
        "recipe.servings",
        "recipe.serving_size",
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

    return "\n".join(f"<li>{html.escape(str(item))}</li>" for item in items)


def build_ingredient_sections(recipe):
    sections = recipe.get("ingredient_sections") or []
    if not sections:
        return f"<ul>{build_list_items(recipe.get('ingredients', []))}</ul>"

    blocks = []
    for section in sections:
        title = html.escape(str(section.get("title", "Ingredients")))
        items = build_list_items(section.get("items", []))
        blocks.append(f"<h3>{title}</h3>\n<ul>{items}</ul>")
    return "\n".join(blocks)


def build_ordered_section(title, items):
    if not items:
        return ""
    return (
        '<div class="recipe-card">'
        f'<h2>{html.escape(title)}</h2><ol>{build_list_items(items)}</ol>'
        '</div>'
    )


def build_optional_sections(sections):
    blocks = []
    for section in sections or []:
        title = html.escape(str(section.get("title", "Optional Pairing")))
        intro = html.escape(str(section.get("intro", "")))
        items = build_list_items(section.get("items", []))
        macros = html.escape(str(section.get("macros", "")))
        body = f"<p>{intro}</p>" if intro else ""
        body += f"<ul>{items}</ul>" if items else ""
        body += f'<p><strong>{macros}</strong></p>' if macros else ""
        blocks.append(f'<div class="recipe-card"><h2>{title}</h2>{body}</div>')
    return "\n".join(blocks)


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

    page_html = replace_nested_placeholders(template, data)

    ingredients = get_nested_value(data, "recipe.ingredients", [])
    instructions = get_nested_value(data, "recipe.instructions", [])
    tips = get_nested_value(data, "recipe.tips", [])

    page_html = page_html.replace("{{ingredients_list}}", build_list_items(ingredients))
    page_html = page_html.replace("{{instructions_list}}", build_list_items(instructions))
    page_html = page_html.replace("{{tips_list}}", build_list_items(tips))
    recipe = data.get("recipe", {})
    page_html = page_html.replace("{{ingredient_sections}}", build_ingredient_sections(recipe))
    page_html = page_html.replace(
        "{{freezer_storage_section}}",
        build_ordered_section("Freezer Storage", recipe.get("freezer_storage", [])),
    )
    page_html = page_html.replace(
        "{{reheating_section}}",
        build_ordered_section("Reheating Instructions", recipe.get("reheating_instructions", [])),
    )
    page_html = page_html.replace(
        "{{optional_sections}}", build_optional_sections(recipe.get("optional_sections", []))
    )

    cook_minutes = get_nested_value(data, "recipe.times.cook_minutes", "")
    cook_line = (
        f'<p><strong>Cook Time:</strong> {cook_minutes} minutes</p>'
        if cook_minutes not in (None, "", 0)
        else ""
    )
    page_html = page_html.replace("{{cook_time_line}}", cook_line)

    story = get_nested_value(data, "recipe.story", "")
    story_section = (
        f'<div class="story-card"><p>{html.escape(str(story))}</p></div>'
        if story else ""
    )
    page_html = page_html.replace("{{story_section}}", story_section)
    canonical = get_nested_value(data, "social.pinterest.destination_url", "")
    page_html = page_html.replace("{{canonical_url}}", str(canonical))
    page_html = page_html.replace("{{recipe_schema}}", json.dumps({
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": recipe.get("title", ""),
        "description": recipe.get("summary", ""),
        "recipeYield": str(recipe.get("servings", "")),
        "recipeIngredient": recipe.get("ingredients", []),
        "recipeInstructions": [
            {"@type": "HowToStep", "text": step}
            for step in recipe.get("instructions", [])
        ],
    }, indent=2))

    output_file = RECIPES_DIR / f"{slug}.html"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(page_html)

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
