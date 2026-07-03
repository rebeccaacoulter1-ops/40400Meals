import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

RECIPE_FILE = Path("recipes/chocolate-protein-mug-cake.json")
DESIGN_FILE = Path("outputs/design/selected_template.json")
OUTPUT_DIR = Path("outputs/images/pinterest")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_font(size):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
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


def create_placeholder_food_image(width, height):
    image = Image.new("RGB", (width, height), "#F6F1EA")
    draw = ImageDraw.Draw(image)

    # Simple placeholder plate/bowl design
    center_x = width // 2
    center_y = height // 2
    bowl_radius = min(width, height) // 3

    draw.ellipse(
        [
            center_x - bowl_radius,
            center_y - bowl_radius,
            center_x + bowl_radius,
            center_y + bowl_radius,
        ],
        fill="#FFFFFF",
        outline="#DDD6CE",
        width=8,
    )

    inner_radius = int(bowl_radius * 0.78)
    draw.ellipse(
        [
            center_x - inner_radius,
            center_y - inner_radius,
            center_x + inner_radius,
            center_y + inner_radius,
        ],
        fill="#4B2418",
    )

    drizzle_radius = int(inner_radius * 0.35)
    draw.ellipse(
        [
            center_x - drizzle_radius,
            center_y - drizzle_radius,
            center_x + drizzle_radius,
            center_y + drizzle_radius,
        ],
        fill="#2A120C",
    )

    return image


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

    image_area_height = 990
    text_area_height = height - image_area_height

    background = Image.new("RGB", (width, height), "#FFFFFF")

    food_image = create_placeholder_food_image(width, image_area_height)
    background.paste(food_image, (0, 0))

    draw = ImageDraw.Draw(background)

    title_font = get_font(82)
    macro_font = get_font(36)
    brand_font = get_font(28)

    title_color = "#4F4843"
    macro_color = "#6B625C"
    brand_color = "#6B625C"

    title_lines = wrap_text(title, title_font, 900)

    title_y = image_area_height + 55
    line_spacing = 8

    for line in title_lines:
        bbox = title_font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2
        draw.text((x, title_y), line, font=title_font, fill=title_color)
        title_y += 88 + line_spacing

    macro_text = f"{protein}g Protein • {calories} Calories"
    macro_bbox = macro_font.getbbox(macro_text)
    macro_width = macro_bbox[2] - macro_bbox[0]
    macro_x = (width - macro_width) // 2
    macro_y = image_area_height + 315
    draw.text((macro_x, macro_y), macro_text, font=macro_font, fill=macro_color)

    brand_text = "40/400 Meals"
    brand_bbox = brand_font.getbbox(brand_text)
    brand_width = brand_bbox[2] - brand_bbox[0]
    brand_x = (width - brand_width) // 2
    brand_y = image_area_height + 415
    draw.text((brand_x, brand_y), brand_text, font=brand_font, fill=brand_color)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{slug}-pinterest-pin.png"

    background.save(output_file)

    print(f"Pinterest image created: {output_file}")


if __name__ == "__main__":
    create_pinterest_pin()
