import os
import json
import base64
import hashlib
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
# -----------------------------

PROMPT_VERSION = "2.2-restaurant-human-realism"
REGENERATE_EXISTING_PHOTOS = False

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
            "Show the dish fully prepared, assembled, and ready to eat. "
            "Do not display the ingredients as separate preparation piles."
        )

    numbered_steps = []

    for index, instruction in enumerate(instructions, start=1):
        numbered_steps.append(f"{index}. {instruction}")

    return "\n".join(numbered_steps)


# -----------------------------
# Prompt cache helpers
# -----------------------------

def create_prompt_hash(prompt):
    content = f"{PROMPT_VERSION}\n{prompt}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def photo_cache_is_current(photo_file, metadata_file, prompt_hash):
    if not photo_file.exists():
        return False

    if not metadata_file.exists():
        return False

    try:
        metadata = load_json(metadata_file)
    except (json.JSONDecodeError, OSError):
        return False

    return (
        metadata.get("prompt_version") == PROMPT_VERSION
        and metadata.get("prompt_hash") == prompt_hash
    )


# -----------------------------
# AI food photo generation
# -----------------------------

def build_food_photo_prompt(recipe, design):
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

REALISTIC, IMPERFECT PLATING (important):
- Ingredients should overlap and blend into each other naturally, the way
  they actually settle in a bowl — not arranged in clean, separated
  quadrants or wedges.
- Sauce should look like it was spooned on by hand: uneven pooling, a few
  drips down the side of the bowl, some areas with more coverage than others.
- Vary ingredient piece sizes and edges. Real chopped vegetables are not
  uniform cubes.
- Slight realism is good: a few natural crumbs, a tiny sauce smear,
  uneven sauce coverage, and natural ingredient overlap.
- The bowl doesn't need to be perfectly full or perfectly centered in frame.

HUMAN FOOD TEXTURE AND ARRANGEMENT RULES:
- Every visible ingredient must have natural variation in size, shape, color,
  orientation, and spacing. Avoid repeated patterns that reveal AI generation.
- Shredded or sliced chicken must have irregular lengths, torn edges, varied
  thickness, overlapping pieces, and different orientations. Never arrange
  chicken in matching curls, parallel strips, or symmetrical clusters.
- Fresh herbs such as cilantro must appear casually torn or roughly chopped,
  with varied leaf sizes, a few stems, uneven spacing, and natural clumping.
  Never scatter herbs evenly across the entire dish like confetti.
- Avocado, when included, must have natural color variation, slightly uneven
  hand-cut slices, varied thickness, and casual placement. Never create a
  perfect fan, identical slices, neon-green color, or symmetrical arrangement.
- Beans, corn, vegetables, and other repeated ingredients must not appear
  cloned. Vary their size, angle, visibility, spacing, and surface texture.
- Garnishes should be sparse and slightly irregular. Some areas of the dish
  should have more garnish than others, and some should have none.
- Preserve believable cooked textures. Meat should look fibrous, vegetables
  should have natural wrinkles and edges, and herbs should not look plastic.
- The final image should feel like a real restaurant plate photographed before
  someone begins eating, not a computer-generated ideal of the recipe.

AI-PATTERN AVOIDANCE:
- No perfect radial arrangements, repeated curves, mirrored placement,
  equal spacing, identical ingredient pieces, or centered garnish patterns.
- No neon greens, uniformly golden meat, excessive gloss, plastic surfaces,
  overly crisp edges, or identical highlights.
- Do not make every ingredient equally visible. Natural food has partial
  overlap, hidden pieces, mixed textures, and visual randomness.
    
PHOTOREALISM REQUIREMENTS:
- Must look like an actual unedited photograph, not a rendered or
  AI-generated image.
- Lighting should be a little uneven — real kitchens have mixed light
  sources, minor shadows, and occasional slight overexposure near windows.
- Avoid glossy, waxy, or airbrushed surfaces on sauces and food — matte,
  slightly dull highlights read as more real than glassy shine.
- Avoid oversaturated colors. Real restaurant and food-blog photography uses
  believable ingredient colors, warm tones, and restrained saturation.
- Include a believable restaurant table, wood surface, or stone countertop
  with subtle natural texture and minor imperfections.
- Use realistic photographic detail with gentle grain, natural depth of field,
  and soft focus falloff rather than artificial edge-to-edge sharpness.
- Add subtle grain/noise consistent with a phone camera in indoor lighting,
  not a clean studio sensor.

PHOTOGRAPHY DIRECTION:
- Lighting: {image_style}
- Camera composition: {photo_composition}
- Color mood: {color_mood}
- Simple restaurant table or natural food-blog setting without staged clutter
- Looks like a genuine restaurant or food-blog photograph, not an advertisement
- Food remains the clear focal point but framing can be slightly imperfect

DO NOT INCLUDE:
- People
- Hands
- Text
- Logos
- Labels
- Packaging
- Decorative ingredients not in the recipe
- Perfectly symmetrical plating
- Studio-quality glossy lighting
- Illustration or digital-art styling

Create one square photograph with no text overlay.
"""

    return prompt.strip()

def generate_ai_food_photo(recipe, design):
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    PHOTO_METADATA_DIR.mkdir(parents=True, exist_ok=True)

    slug = recipe["slug"]

    photo_file = PHOTO_DIR / f"{slug}-food-photo.png"
    metadata_file = PHOTO_METADATA_DIR / f"{slug}-food-photo.json"
    if photo_file.exists() and not REGENERATE_EXISTING_PHOTOS:
        print(
            f"Preserving existing food photo: {photo_file}. "
            "Set REGENERATE_EXISTING_PHOTOS to True to replace it."
        )
        return Image.open(photo_file).convert("RGB")          

    prompt = build_food_photo_prompt(recipe, design)
    prompt_hash = create_prompt_hash(prompt)

    if photo_cache_is_current(
        photo_file,
        metadata_file,
        prompt_hash
    ):
        print(f"Using current AI food photo: {photo_file}")
        return Image.open(photo_file).convert("RGB")

    if photo_file.exists():
        print(
            "Existing food photo is stale because the recipe or image "
            "prompt changed. Regenerating it."
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
            "prompt_version": PROMPT_VERSION,
            "prompt_hash": prompt_hash,
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
