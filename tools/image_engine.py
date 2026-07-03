import os
import json
import base64
from io import BytesIO
from pathlib import Path

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

RECIPE_FILE = Path("recipes/chocolate-protein-mug-cake.json")
DESIGN_FILE = Path("outputs/design/selected_template.json")
OUTPUT_DIR = Path("outputs/images/pinterest")
PHOTO_DIR = Path("outputs/images/food_photos")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_font(size, bold=False):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
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


def build_food_photo_prompt(recipe, design):
    title = recipe.get("title", "high protein recipe")
    ingredients = recipe.get("ingredients", [])
    ingredient_names = []

    for item in ingredients:
        if isinstance(item, dict):
            ingredient_names.append(item.get("name", ""))
        else:
            ingredient_names.append(str(item))

    ingredient_text = ", ".join([name for name in ingredient_names if name])

    image_style = design.get("image_style", "bright natural light")
    photo_composition = design.get("photo_composition", "45-degree angle")
    color_mood = design.get("color_mood", "warm neutral")
    season = design.get("season", "evergreen")

    prompt = f"""
Professional realistic food photography for a Pinterest recipe pin.

Recipe: {title}

Show the finished food only. Make it look delicious, realistic, homemade, and high-protein.

Important visual details:
- Food should clearly match this recipe: {title}
- Ingredients to visually inspire the styling: {ingredient_text}
- Lighting style: {image_style}
- Camera angle: {photo_composition}
- Color mood: {color_mood}
- Seasonal styling: {season}
- Clean countertop styling
- Bright natural window light
- Soft shadows
- Premium food blog photography
- Pinterest-worthy composition
- No people
- No hands
- No text
- No logos
- No packaging
- No utensils blocking the food
- Realistic food texture
- Appetizing but not fake or cartoonish

Create a polished vertical food photo suitable for a premium healthy recipe brand.
"""
    return prompt.strip()


def generate_ai_food_photo(recipe, design, slug):
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    photo_file = PHOTO_DIR / f"{slug}-food-photo.png"

    prompt = build_food_photo_prompt(recipe, design)

    print("Generating AI food photo...")
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

    print(f"AI food photo created: {photo_file}")

    return image


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


def create_pinterest_pin():
    data = load_json(RECIPE_FILE)
    design = load_json(DESIGN_FILE) if DESIGN_FILE.exists() else {}

    recipe = data["recipe"]
    slug = recipe["slug"]
    title = recipe["title"]

    protein = recipe["macros"]["protein_g"]
    calories = recipe["macros"]["calories"]

    width = 1000
    height = 1500

    image_area_height = 900
    text_area_height = height - image_area_height

    background = Image.new("RGB", (width, height), "#FFFFFF")

    food_image = generate_ai_food_photo(recipe, design, slug)
    food_image = food_image.resize((width, image_area_height), Image.LANCZOS)
    background.paste(food_image, (0, 0))

    text_panel = Image.new("RGB", (width, text_area_height + 80), "#FFFDF8")
    wave_mask = create_soft_wave_mask(width, text_area_height + 80)
    background.paste(text_panel, (0, image_area_height - 80), wave_mask)

    draw = ImageDraw.Draw(background)

    title_font = get_font(82, bold=True)
    macro_font = get_font(36)
    brand_font = get_font(34)
    small_font = get_font(28)

    title_color = "#4F4843"
    macro_color = "#6B625C"
    brand_color = "#4F4843"
    accent_color = "#C8B6A6"

    title_lines = wrap_text(title, title_font, 880)

    title_y = image_area_height + 35
    line_spacing = 10

    for line in title_lines:
        bbox = title_font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2
        draw.text((x, title_y), line, font=title_font, fill=title_color)
        title_y += 92 + line_spacing

    macro_text = f"{protein}g Protein  •  {calories} Calories"
    macro_bbox = macro_font.getbbox(macro_text)
    macro_width = macro_bbox[2] - macro_bbox[0]
    macro_x = (width - macro_width) // 2
    macro_y = title_y + 25
    draw.text((macro_x, macro_y), macro_text, font=macro_font, fill=macro_color)

    divider_y = macro_y + 90
    draw.line((330, divider_y, 455, divider_y), fill=accent_color, width=3)
    draw.ellipse((485, divider_y - 18, 515, divider_y + 12), fill=accent_color)
    draw.line((545, divider_y, 670, divider_y), fill=accent_color, width=3)

    brand_text = "40/400 Meals"
    brand_bbox = brand_font.getbbox(brand_text)
    brand_width = brand_bbox[2] - brand_bbox[0]
    brand_x = (width - brand_width) // 2
    brand_y = divider_y + 55
    draw.text((brand_x, brand_y), brand_text, font=brand_font, fill=brand_color)

    tagline_text = "High protein recipes made simple"
    tagline_bbox = small_font.getbbox(tagline_text)
    tagline_width = tagline_bbox[2] - tagline_bbox[0]
    tagline_x = (width - tagline_width) // 2
    tagline_y = brand_y + 55
    draw.text((tagline_x, tagline_y), tagline_text, font=small_font, fill=macro_color)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{slug}-pinterest-pin.png"

    background.save(output_file)

    print(f"Pinterest image created: {output_file}")


if __name__ == "__main__":
    create_pinterest_pin()
