import json
import re
from html import escape
from pathlib import Path
from urllib.parse import quote_plus


# -----------------------------
# Site and file locations
# -----------------------------

SITE_URL = "https://40400meals.com"
RECIPES_DIR = Path("recipes")
TEMPLATE_FILE = Path("templates/recipe-template.html")

# -----------------------------
# Amazon affiliate ingredient links
# -----------------------------
# Every branded product named in an ingredient line gets auto-linked to an
# Amazon search for that product, tagged with the 40/400 Meals Associate ID.
# To add a new brand: add one line below. No other code changes needed —
# every recipe (past and future) picks it up the next time pages render.

AMAZON_ASSOCIATE_TAG = "40400meals-20"

# Ordered longest-phrase-first so a specific match (e.g. "Frank's RedHot")
# is found before a shorter one that might also appear in the same line.
BRAND_LINKS = {
    "Frank's RedHot": "Frank's RedHot buffalo wings sauce",
    "Member's Mark": "Member's Mark grilled chicken bites",
    "Realgood Foods": "Real Good Foods chicken",
    "Clean Simple Eats": "Clean Simple Eats protein powder",
    "The Only Bean": "The Only Bean butter beans",
    "Ocean Spray": "Ocean Spray Craisins dried cranberries",
    "Birds Eye": "Birds Eye Steamfresh riced cauliflower",
    "Kikkoman": "Kikkoman less sodium soy sauce",
    "Philadelphia": "Philadelphia cream cheese",
    "Chobani": "Chobani nonfat plain Greek yogurt",
    "Marukan": "Marukan rice vinegar",
    "Barilla": "Barilla protein pasta",
    "Kinder's": "Kinder's seasoning",
    "Whisps": "Whisps parmesan crisps",
    "Shirakiku": "Shirakiku",
    "Mission": "Mission Carb Balance tortillas",
    "Quest": "Quest Nutrition protein chips",
    "Daisy": "Daisy cottage cheese",
}


def amazon_search_url(query):
    return f"https://www.amazon.com/s?k={quote_plus(query)}&tag={AMAZON_ASSOCIATE_TAG}"


def linkify_ingredient(raw_text):
    """Wrap the first recognized brand mention in an ingredient line with
    an Amazon affiliate search link. Leaves everything else untouched."""
    for brand, query in BRAND_LINKS.items():
        idx = raw_text.find(brand)
        if idx == -1:
            continue

        before = raw_text[:idx]
        matched = raw_text[idx:idx + len(brand)]
        after = raw_text[idx + len(brand):]

        return (
            escape(before)
            + f'<a href="{amazon_search_url(query)}" target="_blank" '
              f'rel="nofollow sponsored noopener">{escape(matched)}</a>'
            + escape(after)
        )

    return escape(raw_text)


# Image-generation directions should never appear in reader-facing recipe copy.
PROMPT_RESIDUE_PHRASES = (
    "naturally uneven",
    "irregularly diced",
    "diced into irregular pieces",
    "loosely beside",
    "rather than shaping it",
    "perfect scoop",
    "symmetrical sections",
    "believable imperfections",
    "natural ingredient overlap",
    "restrained colors",
    "identical cubes",
    "extra garnish",
    "unlisted ingredients",
    "restaurant-style bowl",
)


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


def absolute_site_url(value):
    value = str(value or "").strip()

    if not value:
        return ""

    if value.startswith(("https://", "http://")):
        return value

    if value.startswith("//"):
        return f"https:{value}"

    return f"{SITE_URL}/{value.lstrip('/')}"


def normalize_keywords(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]

    return []


def normalize_recipe(data, recipe_file):
    slug = build_slug(data, recipe_file)
    canonical_url = f"{SITE_URL}/recipes/{slug}.html"

    if "recipe" in data:
        recipe = data["recipe"]
        seo = data.get("seo", {})
        images = data.get("images", {})
        social = data.get("social", {})

        return {
            "title": recipe.get("title", slug.replace("-", " ").title()),
            "summary": recipe.get("summary", ""),
            "story": recipe.get("story", ""),
            "category": recipe.get("category", "High Protein"),
            "cuisine": recipe.get("cuisine", ""),
            "date_published": recipe.get(
                "date_published",
                data.get("date_published", "")
            ),
            "keywords": normalize_keywords(seo.get("keywords", [])),
            "protein": recipe.get("macros", {}).get("protein_g", ""),
            "calories": recipe.get("macros", {}).get("calories", ""),
            "carbs": recipe.get("macros", {}).get("carbs_g", ""),
            "fat": recipe.get("macros", {}).get("fat_g", ""),
            "sugar": recipe.get("macros", {}).get("sugar_g", ""),
            "fiber": recipe.get("macros", {}).get("fiber_g", ""),
            "prep_minutes": recipe.get("times", {}).get("prep_minutes", ""),
            "cook_minutes": recipe.get("times", {}).get("cook_minutes", ""),
            "total_minutes": recipe.get("times", {}).get("total_minutes", ""),
            "servings": recipe.get("servings", ""),
            "serving_size": recipe.get("serving_size", ""),
            "ingredients": recipe.get("ingredients", []),
            "ingredient_sections": recipe.get("ingredient_sections", []),
            "instructions": recipe.get("instructions", []),
            "freezer_storage": recipe.get("freezer_storage", []),
            "reheating_instructions": recipe.get("reheating_instructions", []),
            "optional_sections": recipe.get("optional_sections", []),
            "tips": recipe.get("tips", []),
            "hero_image_url": absolute_site_url(images.get("hero_image_url", "")),
            "alt_text": images.get("alt_text", recipe.get("title", "")),
            "meta_title": seo.get("meta_title", recipe.get("title", "")),
            "meta_description": seo.get(
                "meta_description",
                recipe.get("summary", "")
            ),
            "destination_url": social.get("pinterest", {}).get(
                "destination_url",
                canonical_url
            ),
            "canonical_url": canonical_url,
            "slug": slug,
        }

    tags = data.get("tags", [])
    category = tags[0] if tags else "High Protein"

    return {
        "title": data.get("title", slug.replace("-", " ").title()),
        "summary": data.get("description", ""),
        "story": data.get("story", ""),
        "category": category,
        "cuisine": data.get("cuisine", ""),
        "date_published": data.get("date_published", ""),
        "keywords": normalize_keywords(data.get("keywords", tags)),
        "protein": data.get("protein", ""),
        "calories": data.get("calories", ""),
        "carbs": data.get("carbs", ""),
        "fat": data.get("fat", ""),
        "sugar": data.get("sugar", ""),
        "fiber": data.get("fiber", ""),
        "prep_minutes": str(data.get("prep_time", "")).replace(" minutes", ""),
        "cook_minutes": str(data.get("cook_time", "")).replace(" minutes", ""),
        "total_minutes": str(data.get("total_time", "")).replace(" minutes", ""),
        "servings": data.get("servings", ""),
        "serving_size": data.get("serving_size", ""),
        "ingredients": data.get("ingredients", []),
        "ingredient_sections": data.get("ingredient_sections", []),
        "instructions": data.get("instructions", []),
        "freezer_storage": data.get("freezer_storage", []),
        "reheating_instructions": data.get("reheating_instructions", []),
        "optional_sections": data.get("optional_sections", []),
        "tips": data.get("tips", [
            "Adjust seasoning to taste.",
            "Prep ingredients ahead to make this recipe even faster.",
            "Store leftovers in an airtight container in the refrigerator."
        ]),
        "hero_image_url": absolute_site_url(data.get("image", "")),
        "alt_text": data.get("title", ""),
        "meta_title": data.get("pinterest_title", data.get("title", "")),
        "meta_description": data.get(
            "pinterest_description",
            data.get("description", "")
        ),
        "destination_url": canonical_url,
        "canonical_url": canonical_url,
        "slug": slug,
    }


def validate_reader_facing_copy(recipe, recipe_file):
    fields = {
        "summary": [recipe.get("summary", "")],
        "story": [recipe.get("story", "")],
        "ingredients": recipe.get("ingredients", []),
        "instructions": recipe.get("instructions", []),
        "tips": recipe.get("tips", []),
    }

    violations = []

    for field_name, values in fields.items():
        for item_number, value in enumerate(values, start=1):
            text = str(value).lower()

            for phrase in PROMPT_RESIDUE_PHRASES:
                if phrase in text:
                    violations.append(
                        f"{field_name} item {item_number}: '{phrase}'"
                    )

    if violations:
        details = "\n  - ".join(violations)
        raise ValueError(
            f"{recipe_file} contains image-prompt language in reader-facing copy.\n"
            f"Move visual styling directions to images.image_prompt and rewrite the recipe copy.\n"
            f"  - {details}"
        )


def ingredient_to_text(ingredient):
    if isinstance(ingredient, dict):
        amount = ingredient.get("amount", "")
        unit = ingredient.get("unit", "")
        item = ingredient.get("item", "")
        return f"{amount} {unit} {item}".strip()

    return str(ingredient).strip()


def build_ingredients_html(ingredients):
    return "\n".join(
        f"<li>{linkify_ingredient(ingredient_to_text(ingredient))}</li>"
        for ingredient in ingredients
    )


def build_ingredient_sections_html(recipe):
    sections = recipe.get("ingredient_sections") or []
    if not sections:
        return f"<ul>{build_ingredients_html(recipe.get('ingredients', []))}</ul>"

    blocks = []
    for section in sections:
        title = escape(str(section.get("title", "Ingredients")))
        items = build_ingredients_html(section.get("items", []))
        blocks.append(f"<h3>{title}</h3>\n<ul>{items}</ul>")
    return "\n".join(blocks)


def build_ordered_card(title, items):
    if not items:
        return ""
    return (
        '<div class="recipe-card">\n'
        f'  <h2>{escape(title)}</h2>\n'
        f'  <ol>{build_instructions_html(items)}</ol>\n'
        '</div>'
    )


def build_optional_sections_html(sections):
    blocks = []
    for section in sections or []:
        title = escape(str(section.get("title", "Optional Pairing")))
        intro = escape(str(section.get("intro", "")))
        items = build_list_html(section.get("items", []))
        macros = escape(str(section.get("macros", "")))
        body = f"<p>{intro}</p>" if intro else ""
        body += f"<ul>{items}</ul>" if items else ""
        body += f"<p><strong>{macros}</strong></p>" if macros else ""
        blocks.append(f'<div class="recipe-card"><h2>{title}</h2>{body}</div>')
    return "\n".join(blocks)


def build_instructions_html(instructions):
    lines = []

    for index, instruction in enumerate(instructions, start=1):
        lines.append(
            f'<li id="step-{index}">{escape(str(instruction))}</li>'
        )

    return "\n".join(lines)


def build_list_html(items):
    return "\n".join(f"<li>{escape(str(item))}</li>" for item in items)


def build_story_html(story):
    story = str(story).strip()

    if not story:
        return ""

    return (
        '<div class="recipe-card story-card">\n'
        '  <h2>Behind the Recipe</h2>\n'
        f'  <p>{escape(story)}</p>\n'
        '</div>'
    )


def minutes_to_iso8601(value):
    if value in ("", None):
        return ""

    text = str(value).strip()

    if text.upper().startswith("P"):
        return text.upper()

    match = re.search(r"\d+(?:\.\d+)?", text)

    if not match:
        return ""

    minutes = float(match.group())

    if minutes <= 0:
        return ""

    if minutes.is_integer():
        minutes = int(minutes)

    return f"PT{minutes}M"


def nutrition_value(value, unit):
    if value in ("", None):
        return ""

    text = str(value).strip()

    if not text:
        return ""

    if re.search(r"[A-Za-z]", text):
        return text

    return f"{text} {unit}"


def build_recipe_schema(recipe, recipe_file):
    required = {
        "name": recipe.get("title"),
        "image": recipe.get("hero_image_url"),
        "recipeYield": recipe.get("servings"),
        "recipeIngredient": recipe.get("ingredients"),
        "recipeInstructions": recipe.get("instructions"),
    }

    missing = [name for name, value in required.items() if not value]

    if missing:
        raise ValueError(
            f"{recipe_file} is missing data required for Recipe structured data: "
            + ", ".join(missing)
        )

    canonical_url = recipe["canonical_url"]

    schema = {
        "@context": "https://schema.org/",
        "@type": "Recipe",
        "@id": f"{canonical_url}#recipe",
        "mainEntityOfPage": canonical_url,
        "url": canonical_url,
        "name": recipe["title"],
        "image": [recipe["hero_image_url"]],
        "author": {
            "@type": "Organization",
            "name": "40/400 Meals",
            "url": f"{SITE_URL}/about.html",
        },
        "description": recipe.get("summary", ""),
        "recipeCategory": recipe.get("category", ""),
        "recipeYield": str(recipe["servings"]),
        "recipeIngredient": [
            ingredient_to_text(ingredient)
            for ingredient in recipe["ingredients"]
        ],
        "recipeInstructions": [
            {
                "@type": "HowToStep",
                "position": index,
                "text": str(instruction),
                "url": f"{canonical_url}#step-{index}",
            }
            for index, instruction in enumerate(
                recipe["instructions"],
                start=1
            )
        ],
    }

    optional_values = {
        "datePublished": recipe.get("date_published", ""),
        "recipeCuisine": recipe.get("cuisine", ""),
        "keywords": ", ".join(recipe.get("keywords", [])),
        "prepTime": minutes_to_iso8601(recipe.get("prep_minutes")),
        "cookTime": minutes_to_iso8601(recipe.get("cook_minutes")),
        "totalTime": minutes_to_iso8601(recipe.get("total_minutes")),
    }

    for key, value in optional_values.items():
        if value:
            schema[key] = value

    nutrition = {
        "@type": "NutritionInformation",
        "calories": nutrition_value(recipe.get("calories"), "calories"),
        "proteinContent": nutrition_value(recipe.get("protein"), "g"),
        "carbohydrateContent": nutrition_value(recipe.get("carbs"), "g"),
        "fatContent": nutrition_value(recipe.get("fat"), "g"),
        "sugarContent": nutrition_value(recipe.get("sugar"), "g"),
        "fiberContent": nutrition_value(recipe.get("fiber"), "g"),
    }

    nutrition = {
        key: value
        for key, value in nutrition.items()
        if key == "@type" or value
    }

    if len(nutrition) > 1:
        schema["nutrition"] = nutrition

    # Protect the HTML document if a future recipe contains a literal </script>.
    return json.dumps(
        schema,
        ensure_ascii=False,
        indent=2
    ).replace("</", "<\\/")


def generate_recipe_page(recipe_file):
    data = load_json(recipe_file)
    html = load_template()
    recipe = normalize_recipe(data, recipe_file)

    validate_reader_facing_copy(recipe, recipe_file)
    recipe_schema = build_recipe_schema(recipe, recipe_file)

    replacements = {
        "{{seo.meta_title}}": escape(str(recipe["meta_title"]), quote=True),
        "{{seo.meta_description}}": escape(
            str(recipe["meta_description"]),
            quote=True
        ),
        "{{canonical_url}}": escape(recipe["canonical_url"], quote=True),
        "{{recipe_schema}}": recipe_schema,
        "{{recipe.title}}": escape(str(recipe["title"])),
        "{{recipe.summary}}": escape(str(recipe["summary"])),
        "{{recipe.category}}": escape(str(recipe["category"])),
        "{{recipe.macros.protein_g}}": escape(str(recipe["protein"])),
        "{{recipe.macros.calories}}": escape(str(recipe["calories"])),
        "{{recipe.macros.carbs_g}}": escape(str(recipe["carbs"])),
        "{{recipe.macros.fat_g}}": escape(str(recipe["fat"])),
        "{{recipe.macros.sugar_g}}": escape(str(recipe["sugar"])),
        "{{recipe.macros.fiber_g}}": escape(str(recipe["fiber"])),
        "{{recipe.times.prep_minutes}}": escape(
            str(recipe["prep_minutes"])
        ),
        "{{recipe.times.cook_minutes}}": escape(
            str(recipe["cook_minutes"])
        ),
        "{{recipe.times.total_minutes}}": escape(
            str(recipe["total_minutes"])
        ),
        "{{recipe.servings}}": escape(str(recipe["servings"])),
        "{{recipe.serving_size}}": escape(str(recipe["serving_size"])),
        "{{images.hero_image_url}}": escape(
            recipe["hero_image_url"],
            quote=True
        ),
        "{{images.alt_text}}": escape(
            str(recipe["alt_text"]),
            quote=True
        ),
        "{{social.pinterest.destination_url}}": escape(
            str(recipe["destination_url"]),
            quote=True
        ),
        "{{story_section}}": build_story_html(recipe["story"]),
        "{{ingredients_list}}": build_ingredients_html(
            recipe["ingredients"]
        ),
        "{{ingredient_sections}}": build_ingredient_sections_html(recipe),
        "{{instructions_list}}": build_instructions_html(
            recipe["instructions"]
        ),
        "{{freezer_storage_section}}": build_ordered_card(
            "Freezer Storage", recipe["freezer_storage"]
        ),
        "{{reheating_section}}": build_ordered_card(
            "Reheating Instructions", recipe["reheating_instructions"]
        ),
        "{{optional_sections}}": build_optional_sections_html(
            recipe["optional_sections"]
        ),
        "{{cook_time_line}}": (
            f'<p><strong>Cook Time:</strong> {escape(str(recipe["cook_minutes"]))} minutes</p>'
            if recipe["cook_minutes"] not in (None, "", 0) else ""
        ),
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
