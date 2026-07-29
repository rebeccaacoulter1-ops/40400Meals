import os
import json
import base64
import hashlib
import shutil
from io import BytesIO
from pathlib import Path

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont, ImageOps


# -----------------------------
# OpenAI client
# -----------------------------

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# -----------------------------
# Image prompt version
# Keep the prepared-recipe version stable so existing approved food photos
# are not regenerated merely because packaged-snack support was added.
# -----------------------------

PROMPT_VERSION = "2.2-restaurant-human-realism"


# -----------------------------
# File locations
# -----------------------------

RECIPES_DIR = Path("recipes")
DESIGN_FILE = Path("outputs/design/selected_template.json")
OUTPUT_DIR = Path("outputs/images/pinterest")
PHOTO_DIR = Path("outputs/images/food_photos")
PHOTO_METADATA_DIR = Path("outputs/images/food_photo_metadata")


# -----------------------------
# Load helpers
# -----------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_font(size, bold=False):
    font_paths = [
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        (
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
        ),
    ]

    for font_path in font_paths:
        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size)

    return ImageFont.load_default()


def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)

            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


# -----------------------------
# Recipe normalization
# -----------------------------

def build_slug(data, recipe_file):
    if "slug" in data:
        return data["slug"]

    if "recipe" in data and "slug" in data["recipe"]:
        return data["recipe"]["slug"]

    return recipe_file.stem


def normalize_instructions(instructions):
    normalized = []

    if not instructions:
        return normalized

    if isinstance(instructions, str):
        return [instructions.strip()]

    if isinstance(instructions, list):
        for step in instructions:
            if isinstance(step, dict):
                text = (
                    step.get("text")
                    or step.get("instruction")
                    or step.get("description")
                    or step.get("step")
                    or ""
                )
            else:
                text = str(step)

            text = text.strip()

            if text:
                normalized.append(text)

    return normalized


def normalize_recipe(data, recipe_file):
    slug = build_slug(data, recipe_file)
    image_settings = data.get("images", {}) or {}

    if "recipe" in data:
        recipe = data["recipe"]

        instructions = (
            recipe.get("instructions")
            or recipe.get("directions")
            or recipe.get("steps")
            or []
        )

        return {
            "slug": slug,
            "title": recipe.get(
                "title",
                slug.replace("-", " ").title()
            ),
            "ingredients": recipe.get("ingredients", []),
            "instructions": normalize_instructions(instructions),
            "protein": recipe.get("macros", {}).get("protein_g", ""),
            "calories": recipe.get("macros", {}).get("calories", ""),
            "images": image_settings,
        }

    instructions = (
        data.get("instructions")
        or data.get("directions")
        or data.get("steps")
        or []
    )

    return {
        "slug": slug,
        "title": data.get(
            "title",
            slug.replace("-", " ").title()
        ),
        "ingredients": data.get("ingredients", []),
        "instructions": normalize_instructions(instructions),
        "protein": data.get("protein", ""),
        "calories": data.get("calories", ""),
        "images": image_settings,
    }


def get_ingredient_names(ingredients):
    ingredient_names = []

    for item in ingredients:
        if isinstance(item, dict):
            name = (
                item.get("item")
                or item.get("name")
                or item.get("ingredient")
                or ""
            )
        else:
            name = str(item)

        name = name.strip()

        if name:
            ingredient_names.append(name)

    return ingredient_names


def get_instruction_text(instructions):
    if not instructions:
        return (
            "Show the recipe fully prepared and ready to eat. "
            "Do not display unrelated ingredients."
        )

    numbered_steps = []

    for index, instruction in enumerate(instructions, start=1):
        numbered_steps.append(f"{index}. {instruction}")

    return "\n".join(numbered_steps)


# -----------------------------
# Prompt and source cache helpers
# -----------------------------

def create_prompt_hash(prompt):
    content = f"{PROMPT_VERSION}\n{prompt}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_file_hash(path):
    digest = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def photo_cache_is_current(photo_file, metadata_file, source_hash):
    if not photo_file.exists() or not metadata_file.exists():
        return False

    try:
        metadata = load_json(metadata_file)
    except (json.JSONDecodeError, OSError):
        return False

    return metadata.get("source_hash") == source_hash


# -----------------------------
# Image mode prompts
# -----------------------------

def build_packaged_snack_prompt(recipe, design):
    title = recipe["title"]
    custom_prompt = str(
        recipe.get("images", {}).get("image_prompt", "")
    ).strip()

    ingredient_names = get_ingredient_names(recipe["ingredients"])
    ingredient_text = "\n".join(
        f"- {ingredient}" for ingredient in ingredient_names
    )

    image_style = design.get(
        "image_style",
        "soft, natural window light"
    )
    photo_composition = design.get(
        "photo_composition",
        "casual 45-degree angle with the products easy to recognize"
    )
    color_mood = design.get(
        "color_mood",
        "warm, bright, and realistic"
    )

    prompt = f"""
Create one photorealistic square photograph for the packaged high-protein
snack named "{title}".

CUSTOM SCENE DIRECTION:
{custom_prompt}

EXACT SNACK COMPONENTS:
{ingredient_text}

PACKAGED-SNACK RULES:
- This is a grab-and-go snack assortment, not a cooked recipe or mixed dish.
- Keep each item separate and recognizable.
- Never turn a wrapped protein bar, chips, puff, protein powder, egg, drink,
  guacamole cup, or other packaged snack into loose cooked food.
- When the custom direction says an item remains wrapped, keep it fully sealed
  in its wrapper.
- Product packaging, wrappers, labels, and readable brand names are allowed
  because they are part of the snack being shown.
- Show the exact number of items requested and no extra food.
- Do not add fruit, garnish, sauce, crumbs, shredded food, side dishes, or
  decorative ingredients unless explicitly listed.
- Do not invent orange puffed food, saucy pasta, shredded chicken, or a bowl
  of mixed ingredients.
- The clear protein drink should remain translucent rather than milky.

PHOTOGRAPHY DIRECTION:
- Lighting: {image_style}
- Camera composition: {photo_composition}
- Color mood: {color_mood}
- Clean home-kitchen setting with a realistic plate or countertop
- Natural depth of field and believable shadows
- No added headline, caption, badge, or graphic text overlay
- No people or hands

Create one square photograph.
"""

    return prompt.strip()


def build_prepared_recipe_prompt(recipe, design):
    title = recipe["title"]
    ingredient_names = get_ingredient_names(recipe["ingredients"])
    ingredient_text = "\n".join(
        f"- {ingredient}" for ingredient in ingredient_names
    )

    instruction_text = get_instruction_text(recipe["instructions"])

    image_style = design.get(
        "image_style",
        "soft, slightly uneven natural window light"
    )
    photo_composition = design.get(
        "photo_composition",
        "casual 45-degree angle, handheld feel, not perfectly centered"
    )
    color_mood = design.get(
        "color_mood",
        "warm neutral, slightly muted"
    )

    prompt = f"""
Create a photorealistic photo of the finished recipe named "{title}",
photographed like an appealing dish genuinely served at a neighborhood
restaurant or captured by an experienced food blogger in natural window
light. Make it appetizing but naturally plated, not commercially styled,
digitally rendered, airbrushed, or artificially perfect.

EXACT ALLOWED INGREDIENTS:
{ingredient_text}

RECIPE PREPARATION:
{instruction_text}

INGREDIENT ACCURACY RULES:
- Use only ingredients explicitly included in the exact allowed ingredient list.
- Do not invent or add any garnish, topping, vegetable, fruit, herb, cheese,
  sauce, seasoning, side dish, decoration, or background food.
- Do not add common ingredients simply because they are often associated with
  this type of recipe.
- If an ingredient is mixed, melted, blended, seasoned, or cooked into the
  finished dish, show it naturally incorporated instead of placing it in a
  separate pile.
- Show the completed ready-to-eat recipe, not ingredient preparation or mise
  en place.

REALISTIC, IMPERFECT PLATING:
- Ingredients should overlap and blend naturally rather than sitting in clean,
  separated quadrants.
- Sauce should look spooned on by hand with believable, uneven coverage.
- Vary ingredient piece sizes, edges, spacing, and orientation.
- Slight realism is good: natural crumbs, a tiny sauce smear, and imperfect
  centering are acceptable.
- Avoid repeated patterns, cloned ingredients, symmetry, neon colors, plastic
  texture, or excessive gloss.
- Preserve believable cooked textures.

PHOTOREALISM REQUIREMENTS:
- Must look like an actual unedited photograph, not an illustration or render.
- Use believable ingredient colors, restrained saturation, natural shadows,
  gentle grain, and realistic depth of field.
- Include a simple restaurant table, wood surface, or stone countertop with
  subtle natural texture.

PHOTOGRAPHY DIRECTION:
- Lighting: {image_style}
- Camera composition: {photo_composition}
- Color mood: {color_mood}
- Food remains the clear focal point
- No people, hands, text overlay, logos, labels, or packaging
- No decorative ingredients not included in the recipe

Create one square photograph with no text overlay.
"""

    return prompt.strip()


def build_food_photo_prompt(recipe, design):
    image_mode = str(
        recipe.get("images", {}).get("image_mode", "prepared_recipe")
    ).strip().lower()

    if image_mode == "packaged_snack":
        return build_packaged_snack_prompt(recipe, design)

    return build_prepared_recipe_prompt(recipe, design)


# -----------------------------
# Food photo generation
# -----------------------------

def use_manual_source_photo(recipe, photo_file, metadata_file):
    image_settings = recipe.get("images", {})

    source_value = str(
        image_settings.get("source_photo_path", "")
    ).strip()
    base64_value = str(
        image_settings.get("source_photo_base64_path", "")
    ).strip()

    if not source_value and not base64_value:
        return None

    if source_value:
        source_path = Path(source_value)

        if not source_path.exists():
            raise FileNotFoundError(
                f"Manual source photo not found for {recipe['slug']}: "
                f"{source_path}"
            )

        source_hash = f"manual-file:{create_file_hash(source_path)}"

        if photo_cache_is_current(photo_file, metadata_file, source_hash):
            print(f"Using current approved source photo: {photo_file}")
            return Image.open(photo_file).convert("RGB")

        image = Image.open(source_path).convert("RGB")
        source_label = str(source_path)

    else:
        source_path = Path(base64_value)

        if not source_path.exists():
            raise FileNotFoundError(
                f"Base64 source photo not found for {recipe['slug']}: "
                f"{source_path}"
            )

        source_hash = f"manual-base64:{create_file_hash(source_path)}"

        if photo_cache_is_current(photo_file, metadata_file, source_hash):
            print(f"Using current approved source photo: {photo_file}")
            return Image.open(photo_file).convert("RGB")

        encoded = source_path.read_text(encoding="utf-8").strip()
        image_bytes = base64.b64decode(encoded)
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        source_label = str(source_path)

    image.save(photo_file)

    save_json(
        metadata_file,
        {
            "slug": recipe["slug"],
            "recipe_title": recipe["title"],
            "image_mode": "manual_source",
            "source_photo": source_label,
            "source_hash": source_hash,
            "photo_file": str(photo_file),
        }
    )

    print(f"Approved source photo copied to: {photo_file}")
    return image


def generate_ai_food_photo(recipe, design):
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    PHOTO_METADATA_DIR.mkdir(parents=True, exist_ok=True)

    slug = recipe["slug"]
    photo_file = PHOTO_DIR / f"{slug}-food-photo.png"
    metadata_file = PHOTO_METADATA_DIR / f"{slug}-food-photo.json"

    manual_image = use_manual_source_photo(
        recipe,
        photo_file,
        metadata_file
    )

    if manual_image is not None:
        return manual_image

    prompt = build_food_photo_prompt(recipe, design)
    prompt_hash = f"prompt:{create_prompt_hash(prompt)}"

    if photo_cache_is_current(
        photo_file,
        metadata_file,
        prompt_hash
    ):
        print(f"Using current AI food photo: {photo_file}")
        return Image.open(photo_file).convert("RGB")

    if photo_file.exists():
        print(
            "Existing food photo is stale because the recipe image prompt "
            "or image mode changed. Regenerating it."
        )
    else:
        print("No current food photo found. Generating a new image.")

    print("Generating photorealistic AI food photo...")
    print(prompt)

    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
    )

    image_base64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image.save(photo_file)

    save_json(
        metadata_file,
        {
            "slug": slug,
            "recipe_title": recipe["title"],
            "image_mode": recipe.get("images", {}).get(
                "image_mode",
                "prepared_recipe"
            ),
            "prompt_version": PROMPT_VERSION,
            "source_hash": prompt_hash,
            "photo_file": str(photo_file),
        }
    )

    print(f"AI food photo created: {photo_file}")
    print(f"Image metadata created: {metadata_file}")

    return image


# -----------------------------
# Pinterest pin design
# -----------------------------

def create_soft_wave_mask(width, height):
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    points = []
    wave_height = 55

    for x in range(width + 1):
        y = int(wave_height * 0.5)

        if 250 < x < 750:
            y = int(wave_height * 0.9)

        points.append((x, y))

    polygon = [(0, height)] + points + [(width, height)]
    draw.polygon(polygon, fill=255)

    return mask


def create_pinterest_pin(recipe, design):
    slug = recipe["slug"]
    title = recipe["title"]
    protein = recipe["protein"]
    calories = recipe["calories"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / f"{slug}-pinterest-pin.png"

    width = 1000
    height = 1500

    image_area_height = 900
    text_area_height = height - image_area_height

    background = Image.new(
        "RGB",
        (width, height),
        "#FFFFFF"
    )

    food_image = generate_ai_food_photo(recipe, design)

    food_image = ImageOps.fit(
        food_image,
        (width, image_area_height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

    background.paste(food_image, (0, 0))

    text_panel = Image.new(
        "RGB",
        (width, text_area_height + 80),
        "#FFFDF8"
    )

    wave_mask = create_soft_wave_mask(
        width,
        text_area_height + 80
    )

    background.paste(
        text_panel,
        (0, image_area_height - 80),
        wave_mask
    )

    draw = ImageDraw.Draw(background)

    title_font = get_font(82, bold=True)
    macro_font = get_font(36)
    brand_font = get_font(34)
    small_font = get_font(28)

    title_color = "#4F4843"
    macro_color = "#6B625C"
    brand_color = "#4F4843"
    accent_color = "#C8B6A6"

    title_lines = wrap_text(
        title,
        title_font,
        880
    )

    title_y = image_area_height + 35
    line_spacing = 10

    for line in title_lines:
        bbox = title_font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2

        draw.text(
            (x, title_y),
            line,
            font=title_font,
            fill=title_color
        )

        title_y += 92 + line_spacing

    macro_text = f"{protein}g Protein  •  {calories} Calories"
    macro_bbox = macro_font.getbbox(macro_text)
    macro_width = macro_bbox[2] - macro_bbox[0]
    macro_x = (width - macro_width) // 2
    macro_y = title_y + 25

    draw.text(
        (macro_x, macro_y),
        macro_text,
        font=macro_font,
        fill=macro_color
    )

    divider_y = macro_y + 90

    draw.line(
        (330, divider_y, 455, divider_y),
        fill=accent_color,
        width=3
    )

    draw.ellipse(
        (485, divider_y - 18, 515, divider_y + 12),
        fill=accent_color
    )

    draw.line(
        (545, divider_y, 670, divider_y),
        fill=accent_color,
        width=3
    )

    brand_text = "40/400 Meals"
    brand_bbox = brand_font.getbbox(brand_text)
    brand_width = brand_bbox[2] - brand_bbox[0]
    brand_x = (width - brand_width) // 2
    brand_y = divider_y + 55

    draw.text(
        (brand_x, brand_y),
        brand_text,
        font=brand_font,
        fill=brand_color
    )

    tagline_text = "High protein, low sugar recipes made simple"
    tagline_bbox = small_font.getbbox(tagline_text)
    tagline_width = tagline_bbox[2] - tagline_bbox[0]
    tagline_x = (width - tagline_width) // 2
    tagline_y = brand_y + 55

    draw.text(
        (tagline_x, tagline_y),
        tagline_text,
        font=small_font,
        fill=macro_color
    )

    background.save(output_file)

    print(f"Pinterest image created or refreshed: {output_file}")


# -----------------------------
# Main process
# -----------------------------

def main():
    design = load_json(DESIGN_FILE) if DESIGN_FILE.exists() else {}

    recipe_files = sorted(RECIPES_DIR.glob("*.json"))

    if not recipe_files:
        print("No recipe JSON files found.")
        return

    for recipe_file in recipe_files:
        print(f"\nProcessing image for {recipe_file}")

        data = load_json(recipe_file)
        recipe = normalize_recipe(data, recipe_file)

        create_pinterest_pin(recipe, design)


if __name__ == "__main__":
    main()
