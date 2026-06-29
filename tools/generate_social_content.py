import json
from pathlib import Path

RECIPE_FILE = Path("recipes/chocolate-protein-mug-cake.json")

with open(RECIPE_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

recipe = data["recipe"]
seo = data["seo"]
images = data["images"]
social = data["social"]
email = data["email"]

slug = recipe["slug"]
output_dir = Path("outputs") / slug
output_dir.mkdir(parents=True, exist_ok=True)

def write_file(filename, content):
    path = output_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"Created {path}")

pinterest_content = f"""
PINTEREST TITLE:
{social["pinterest"]["title"]}

PINTEREST DESCRIPTION:
{social["pinterest"]["description"]}

DESTINATION URL:
{social["pinterest"]["destination_url"]}

HASHTAGS:
{" ".join(social["pinterest"]["hashtags"])}
"""

instagram_content = f"""
INSTAGRAM CAPTION:
{social["instagram"]["caption"]}

HASHTAGS:
{" ".join(social["instagram"]["hashtags"])}
"""

facebook_content = f"""
FACEBOOK CAPTION:
{social["facebook"]["caption"]}
"""

email_content = f"""
EMAIL SUBJECT:
{email["subject"]}

PREVIEW TEXT:
{email["preview_text"]}

BODY INTRO:
{email["body_intro"]}
"""

youtube_short_content = f"""
YOUTUBE SHORT HOOK:
{social["youtube_short"]["hook"]}

SCRIPT:
{chr(10).join("- " + line for line in social["youtube_short"]["script"])}

CTA:
{social["youtube_short"]["cta"]}
"""

image_prompt_content = f"""
MASTER IMAGE PROMPT:
{images["image_prompt"]}

ALT TEXT:
{images["alt_text"]}

SEO META TITLE:
{seo["meta_title"]}

SEO META DESCRIPTION:
{seo["meta_description"]}
"""

write_file("pinterest.txt", pinterest_content)
write_file("instagram.txt", instagram_content)
write_file("facebook.txt", facebook_content)
write_file("email.txt", email_content)
write_file("youtube-short.txt", youtube_short_content)
write_file("image-prompt.txt", image_prompt_content)

print("Social content generated successfully.")
