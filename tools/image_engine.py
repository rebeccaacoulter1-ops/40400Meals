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

BRAND_COLORS = {
    "cream": "#FBF8F1",
    "paper": "#FFFDF8",
    "ink": "#28322D",
    "muted": "#68716C",
    "sage": "#DCE7DF",
    "sage_dark": "#315F50",
    "sand": "#E8DED1",
    "terracotta": "#B86F4C",
}


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


def normalize_pin_template(value):
    template = str(value or "").strip().lower()
    aliases = {
        "p01": "classic",
        "p01 classic": "classic",
        "p01 classic recipe v1.0": "classic",
        "classic recipe": "classic",
        "p02": "food_first",
        "food first": "food_first",
        "food-first": "food_first",
        "p03": "editorial",
        "clean editorial": "editorial",
        "clean-editorial": "editorial",
        "p04": "mug_series",
        "mug series": "mug_series",
        "mug-series": "mug_series",
    }

    return aliases.get(template, template)


def choose_pin_template(recipe, design):
    image_settings = recipe.get("images", {})

    requested = (
        image_settings.get("pin_template")
        or image_settings.get("pinterest_template")
        or ""
    )

    requested = normalize_pin_template(requested)

    if requested in {"classic", "food_first", "editorial", "mug_series"}:
        return requested

    design_template = normalize_pin_template(
        design.get("template_name", "")
    )

    if design_template in {"food_first", "editorial", "mug_series"}:
        return design_template

    # Existing recipes stay on the approved classic layout unless their
    # recipe JSON explicitly opts into a new template.
    return "classic"


def fit_title(text, max_width, max_lines, start_size, min_size=42):
    for size in range(start_size, min_size - 1, -2):
        font = get_font(size, bold=True)
        lines = wrap_text(text, font, max_width)

        if len(lines) <= max_lines:
            return font, lines

    font = get_font(min_size, bold=True)
    return font, wrap_text(text, font, max_width)[:max_lines]


def draw_centered_lines(
    draw,
    lines,
    font,
    width,
    start_y,
    fill,
    line_gap=12,
):
    y = start_y
    bbox = font.getbbox("Ag")
    line_height = bbox[3] - bbox[1]

    for line in lines:
        line_bbox = font.getbbox(line)
        line_width = line_bbox[2] - line_bbox[0]
        x = (width - line_width) // 2
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height + line_gap

    return y


def draw_left_lines(
    draw,
    lines,
    font,
    x,
    start_y,
    fill,
    line_gap=10,
):
    y = start_y
    bbox = font.getbbox("Ag")
    line_height = bbox[3] - bbox[1]

    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height + line_gap

    return y


def draw_macro_pill(
    draw,
    box,
    label,
    value,
    fill,
    text_color,
):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=28, fill=fill)

    label_font = get_font(23, bold=True)
    value_font = get_font(34, bold=True)

    label_bbox = label_font.getbbox(label)
    label_width = label_bbox[2] - label_bbox[0]
    value_bbox = value_font.getbbox(value)
    value_width = value_bbox[2] - value_bbox[0]

    center_x = (x1 + x2) // 2
    draw.text(
        (center_x - label_width // 2, y1 + 17),
        label,
        font=label_font,
        fill=text_color,
    )
    draw.text(
        (center_x - value_width // 2, y1 + 50),
        value,
        font=value_font,
        fill=text_color,
    )


def render_classic_pin(food_image, recipe):
    width = 1000
    height = 1500
    image_area_height = 900
    text_area_height = height - image_area_height

    background = Image.new("RGB", (width, height), "#FFFFFF")

    fitted_photo = ImageOps.fit(
        food_image,
        (width, image_area_height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    background.paste(fitted_photo, (0, 0))

    text_panel = Image.new(
        "RGB",
        (width, text_area_height + 80),
        BRAND_COLORS["paper"],
    )
    wave_mask = create_soft_wave_mask(
        width,
        text_area_height + 80,
    )
    background.paste(
        text_panel,
        (0, image_area_height - 80),
        wave_mask,
    )

    draw = ImageDraw.Draw(background)
    title_font, title_lines = fit_title(
        recipe["title"],
        max_width=880,
        max_lines=4,
        start_size=82,
        min_size=54,
    )

    title_y = draw_centered_lines(
        draw,
        title_lines,
        title_font,
        width,
        image_area_height + 35,
        BRAND_COLORS["ink"],
        line_gap=10,
    )

    macro_font = get_font(36)
    macro_text = (
        f'{recipe["protein"]}g Protein  •  '
        f'{recipe["calories"]} Calories'
    )
    macro_bbox = macro_font.getbbox(macro_text)
    macro_width = macro_bbox[2] - macro_bbox[0]
    macro_y = title_y + 18

    draw.text(
        ((width - macro_width) // 2, macro_y),
        macro_text,
        font=macro_font,
        fill=BRAND_COLORS["muted"],
    )

    divider_y = macro_y + 90
    draw.line(
        (330, divider_y, 455, divider_y),
        fill=BRAND_COLORS["sand"],
        width=3,
    )
    draw.ellipse(
        (485, divider_y - 18, 515, divider_y + 12),
        fill=BRAND_COLORS["sand"],
    )
    draw.line(
        (545, divider_y, 670, divider_y),
        fill=BRAND_COLORS["sand"],
        width=3,
    )

    brand_font = get_font(34)
    brand_text = "40/400 Meals"
    brand_bbox = brand_font.getbbox(brand_text)
    brand_width = brand_bbox[2] - brand_bbox[0]
    brand_y = divider_y + 55
    draw.text(
        ((width - brand_width) // 2, brand_y),
        brand_text,
        font=brand_font,
        fill=BRAND_COLORS["ink"],
    )

    small_font = get_font(28)
    tagline = "High protein, low sugar recipes made simple"
    tagline_bbox = small_font.getbbox(tagline)
    tagline_width = tagline_bbox[2] - tagline_bbox[0]
    draw.text(
        ((width - tagline_width) // 2, brand_y + 55),
        tagline,
        font=small_font,
        fill=BRAND_COLORS["muted"],
    )

    return background


def render_food_first_pin(food_image, recipe):
    width = 1000
    height = 1500
    image_height = 1030

    background = Image.new(
        "RGB",
        (width, height),
        BRAND_COLORS["cream"],
    )
    fitted_photo = ImageOps.fit(
        food_image,
        (width, image_height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    background.paste(fitted_photo, (0, 0))

    draw = ImageDraw.Draw(background)
    draw.rectangle(
        (0, image_height, width, image_height + 8),
        fill=BRAND_COLORS["terracotta"],
    )

    label_font = get_font(23, bold=True)
    draw.text(
        (62, 1068),
        "40/400 MEALS",
        font=label_font,
        fill=BRAND_COLORS["sage_dark"],
    )

    draw_macro_pill(
        draw,
        (515, 1052, 710, 1140),
        "PROTEIN",
        f'{recipe["protein"]}g',
        BRAND_COLORS["sage"],
        BRAND_COLORS["ink"],
    )
    draw_macro_pill(
        draw,
        (730, 1052, 938, 1140),
        "CALORIES",
        str(recipe["calories"]),
        BRAND_COLORS["sand"],
        BRAND_COLORS["ink"],
    )

    title_font, title_lines = fit_title(
        recipe["title"],
        max_width=875,
        max_lines=3,
        start_size=72,
        min_size=50,
    )
    title_end_y = draw_left_lines(
        draw,
        title_lines,
        title_font,
        62,
        1180,
        BRAND_COLORS["ink"],
        line_gap=9,
    )

    small_font = get_font(25)
    tagline_y = min(title_end_y + 18, 1445)
    draw.text(
        (62, tagline_y),
        "High protein. Real food. Made simple.",
        font=small_font,
        fill=BRAND_COLORS["muted"],
    )

    return background


def render_editorial_pin(food_image, recipe, mug_series=False):
    width = 1000
    height = 1500

    fitted_photo = ImageOps.fit(
        food_image,
        (width, height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.48),
    ).convert("RGBA")

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    overlay_draw.rounded_rectangle(
        (55, 865, 945, 1435),
        radius=46,
        fill=(251, 248, 241, 244),
    )
    overlay_draw.rounded_rectangle(
        (82, 902, 315, 960),
        radius=28,
        fill=(
            49,
            95,
            80,
            255,
        ),
    )

    background = Image.alpha_composite(fitted_photo, overlay)
    draw = ImageDraw.Draw(background)

    badge_font = get_font(22, bold=True)
    badge_text = "MUG SERIES" if mug_series else "40/400 MEALS"
    badge_bbox = badge_font.getbbox(badge_text)
    badge_width = badge_bbox[2] - badge_bbox[0]
    draw.text(
        (198 - badge_width // 2, 920),
        badge_text,
        font=badge_font,
        fill="#FFFFFF",
    )

    title_font, title_lines = fit_title(
        recipe["title"],
        max_width=810,
        max_lines=3,
        start_size=76,
        min_size=50,
    )
    title_end_y = draw_left_lines(
        draw,
        title_lines,
        title_font,
        92,
        990,
        BRAND_COLORS["ink"],
        line_gap=10,
    )

    macro_y = min(title_end_y + 28, 1280)
    draw_macro_pill(
        draw,
        (92, macro_y, 440, macro_y + 102),
        "PROTEIN",
        f'{recipe["protein"]}g',
        BRAND_COLORS["sage"],
        BRAND_COLORS["ink"],
    )
    draw_macro_pill(
        draw,
        (462, macro_y, 850, macro_y + 102),
        "CALORIES",
        str(recipe["calories"]),
        BRAND_COLORS["sand"],
        BRAND_COLORS["ink"],
    )

    brand_font = get_font(27, bold=True)
    footer_y = macro_y + 130
    draw.text(
        (92, footer_y),
        "40/400 Meals",
        font=brand_font,
        fill=BRAND_COLORS["sage_dark"],
    )

    tagline_font = get_font(23)
    draw.text(
        (320, footer_y + 2),
        "High-protein recipes made simple",
        font=tagline_font,
        fill=BRAND_COLORS["muted"],
    )

    return background.convert("RGB")


def create_pinterest_pin(recipe, design):
    slug = recipe["slug"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{slug}-pinterest-pin.png"

    food_image = generate_ai_food_photo(recipe, design)
    template = choose_pin_template(recipe, design)

    if template == "food_first":
        background = render_food_first_pin(food_image, recipe)
    elif template == "editorial":
        background = render_editorial_pin(
            food_image,
            recipe,
            mug_series=False,
        )
    elif template == "mug_series":
        background = render_editorial_pin(
            food_image,
            recipe,
            mug_series=True,
        )
    else:
        background = render_classic_pin(food_image, recipe)

    background.save(output_file)

    print(
        f"Pinterest image created or refreshed: {output_file} "
        f"(template: {template})"
    )


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