import json
from pathlib import Path


# -----------------------------
# File locations
# -----------------------------

RECIPES_DIR = Path("recipes")
OUTPUTS_DIR = Path("outputs")


# -----------------------------
# Helper functions
# -----------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

    print(f"Created {path}")


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
        seo = data.get("seo", {})
        images = data.get("images", {})
        social = data.get("social", {})
        email = data.get("email", {})

        return {
            "slug": slug,
            "title": recipe.get("title", slug.replace("-", " ").title()),
            "summary": recipe.get("summary", ""),
            "protein": recipe.get("macros", {}).get("protein_g", ""),
            "calories": recipe.get("macros", {}).get("calories", ""),
            "seo_title": seo.get("meta_title", recipe.get("title", "")),
            "seo_description": seo.get("meta_description", recipe.get("summary", "")),
            "image_prompt": images.get("image_prompt", ""),
            "alt_text": images.get("alt_text", recipe.get("title", "")),
            "pinterest_title": social.get("pinterest", {}).get(
                "title",
                f"{recipe.get('title', '')} | 40/400 Meals"
            ),
            "pinterest_description": social.get("pinterest", {}).get(
                "description",
                recipe.get("summary", "")
            ),
            "destination_url": social.get("pinterest", {}).get(
                "destination_url",
                f"https://40400meals.com/recipes/{slug}.html"
            ),
            "pinterest_hashtags": social.get("pinterest", {}).get(
                "hashtags",
                ["#HighProteinRecipes", "#LowSugarRecipes", "#40400Meals"]
            ),
            "instagram_caption": social.get("instagram", {}).get(
                "caption",
                recipe.get("summary", "")
            ),
            "instagram_hashtags": social.get("instagram", {}).get(
                "hashtags",
                ["#HighProteinRecipes", "#LowSugarRecipes", "#40400Meals"]
            ),
            "facebook_caption": social.get("facebook", {}).get(
                "caption",
                recipe.get("summary", "")
            ),
            "email_subject": email.get(
                "subject",
                f"New recipe: {recipe.get('title', '')}"
            ),
            "email_preview_text": email.get(
                "preview_text",
                recipe.get("summary", "")
            ),
            "email_body_intro": email.get(
                "body_intro",
                recipe.get("summary", "")
            ),
            "youtube_hook": social.get("youtube_short", {}).get(
                "hook",
                f"Need a high protein meal fast? Try this {recipe.get('title', '')}."
            ),
            "youtube_script": social.get("youtube_short", {}).get(
                "script",
                [
                    f"Start with {recipe.get('title', '')}.",
                    "Build it around protein first.",
                    "Keep it simple, satisfying, and realistic for busy days."
                ]
            ),
            "youtube_cta": social.get("youtube_short", {}).get(
                "cta",
                "Get the full recipe at 40400Meals.com."
            ),
        }

    title = data.get("title", slug.replace("-", " ").title())
    description = data.get("description", "")
    pinterest_title = data.get("pinterest_title", f"{title} | 40/400 Meals")
    pinterest_description = data.get("pinterest_description", description)
    destination_url = f"https://40400meals.com/recipes/{slug}.html"

    return {
        "slug": slug,
        "title": title,
        "summary": description,
        "protein": data.get("protein", ""),
        "calories": data.get("calories", ""),
        "seo_title": pinterest_title,
        "seo_description": pinterest_description,
        "image_prompt": f"Premium food blog photography of {title}, bright natural light, clean neutral background, appetizing and realistic.",
        "alt_text": title,
        "pinterest_title": pinterest_title,
        "pinterest_description": pinterest_description,
        "destination_url": destination_url,
        "pinterest_hashtags": ["#HighProteinRecipes", "#LowSugarRecipes", "#EasyDinner", "#40400Meals"],
        "instagram_caption": f"{title}: {description}\n\n{data.get('protein', '')}g protein, {data.get('calories', '')} calories, and made for real life.",
        "instagram_hashtags": ["#HighProteinRecipes", "#LowSugarRecipes", "#MacroFriendly", "#40400Meals"],
        "facebook_caption": f"New recipe on 40/400 Meals: {title}. {description}",
        "email_subject": f"New recipe: {title}",
        "email_preview_text": description,
        "email_body_intro": f"This {title} is simple, satisfying, and built around the 40/400 method.",
        "youtube_hook": f"Pizza craving? Make this {title} instead.",
        "youtube_script": [
            f"Start with {title}.",
            "Build it around protein first.",
            "Keep the ingredients simple.",
            "Serve it hot and enjoy a macro-friendly craving fix."
        ],
        "youtube_cta": "Get the full recipe at 40400Meals.com.",
    }


# -----------------------------
# Content builders
# -----------------------------

def build_pinterest_content(recipe):
    return f"""
PINTEREST TITLE:
{recipe["pinterest_title"]}

PINTEREST DESCRIPTION:
{recipe["pinterest_description"]}

DESTINATION URL:
{recipe["destination_url"]}

HASHTAGS:
{" ".join(recipe["pinterest_hashtags"])}
"""


def build_instagram_content(recipe):
    return f"""
INSTAGRAM CAPTION:
{recipe["instagram_caption"]}

HASHTAGS:
{" ".join(recipe["instagram_hashtags"])}
"""


def build_facebook_content(recipe):
    return f"""
FACEBOOK CAPTION:
{recipe["facebook_caption"]}
"""


def build_email_content(recipe):
    return f"""
EMAIL SUBJECT:
{recipe["email_subject"]}

PREVIEW TEXT:
{recipe["email_preview_text"]}

BODY INTRO:
{recipe["email_body_intro"]}
"""


def build_youtube_short_content(recipe):
    return f"""
YOUTUBE SHORT HOOK:
{recipe["youtube_hook"]}

SCRIPT:
{chr(10).join("- " + line for line in recipe["youtube_script"])}

CTA:
{recipe["youtube_cta"]}
"""


def build_image_prompt_content(recipe):
    return f"""
MASTER IMAGE PROMPT:
{recipe["image_prompt"]}

ALT TEXT:
{recipe["alt_text"]}

SEO META TITLE:
{recipe["seo_title"]}

SEO META DESCRIPTION:
{recipe["seo_description"]}
"""


# -----------------------------
# Main process
# -----------------------------

def process_recipe(recipe_file):
    data = load_json(recipe_file)
    recipe = normalize_recipe(data, recipe_file)

    output_dir = OUTPUTS_DIR / recipe["slug"]
    output_dir.mkdir(parents=True, exist_ok=True)

    write_file(output_dir / "pinterest.txt", build_pinterest_content(recipe))
    write_file(output_dir / "instagram.txt", build_instagram_content(recipe))
    write_file(output_dir / "facebook.txt", build_facebook_content(recipe))
    write_file(output_dir / "email.txt", build_email_content(recipe))
    write_file(output_dir / "youtube-short.txt", build_youtube_short_content(recipe))
    write_file(output_dir / "image-prompt.txt", build_image_prompt_content(recipe))

    print(f"Social content generated successfully for {recipe['title']}.")


def main():
    recipe_files = sorted(RECIPES_DIR.glob("*.json"))

    if not recipe_files:
        print("No recipe JSON files found.")
        return

    for recipe_file in recipe_files:
        print(f"\nProcessing social content for {recipe_file}")
        process_recipe(recipe_file)


if __name__ == "__main__":
    main()
