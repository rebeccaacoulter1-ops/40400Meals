import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MAKE_WEBHOOK_URL", "https://example.com/test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from design_engine import normalize_recipe_category
from generate_pinterest import PIN_VARIANTS, build_pin_data
from image_engine import build_pin_variants, render_benefit_pin
from PIL import Image


def sample_recipe():
    return {
        "recipe_id": "test-lunch",
        "slug": "test-lunch",
        "title": "Chicken Lunch Box",
        "protein": 40,
        "calories": 395,
        "pinterest_title": "Chicken Lunch Box",
        "pinterest_description": "An easy portable lunch.",
        "destination_url": "https://40400meals.com/recipes/test-lunch.html",
        "hashtags": ["#LunchBoxIdeas"],
        "image_prompt": "A realistic chicken lunch box.",
        "image_alt_text": "Chicken lunch box.",
        "seo_keywords": ["high protein lunch"],
        "category": "Quick & Easy Lunch",
        "published_at": "2026-08-25T09:25:00-05:00",
    }


def sample_design():
    return {
        "template_name": "P07 Fall",
        "template_type": "seasonal",
        "season": "fall",
        "month": 8,
        "color_mood": "warm",
        "accent_colors": ["#FFF7ED", "#F97316"],
        "text_style": "clean",
        "overlay_style": "minimal",
        "icon_style": "minimal",
        "optimization": {},
        "version": "2.5",
        "status": "ready",
    }


def test_human_categories_are_normalized():
    assert normalize_recipe_category("Quick & Easy Lunch") == "lunch"
    assert normalize_recipe_category("Grab-and-Go Breakfast") == "breakfast"
    assert normalize_recipe_category("Protein Snack") == "snack"
    assert normalize_recipe_category("Family Dinner") == "dinner"


def test_four_variants_have_unique_templates_tracking_and_dates():
    recipe = sample_recipe()
    pins = [build_pin_data(recipe, sample_design(), item) for item in PIN_VARIANTS]

    assert [pin["variant_id"] for pin in pins] == ["v1", "v2", "v3", "v4"]
    assert [pin["pin_template"] for pin in pins] == [
        "classic",
        "editorial",
        "food_first",
        "benefit",
    ]
    assert len({pin["destination_url"] for pin in pins}) == 4
    assert [datetime.fromisoformat(pin["scheduled_at"]).day for pin in pins] == [
        25,
        28,
        1,
        5,
    ]
    assert pins[0]["image_filename"] == "test-lunch-pinterest-pin.png"
    assert pins[3]["image_filename"] == "test-lunch-pinterest-v4.png"
    assert all(pin["design_brain"]["recipe_category"] == "lunch" for pin in pins)


def test_image_engine_builds_four_materially_different_variants():
    recipe = sample_recipe()
    variants = build_pin_variants(recipe)
    assert [item[1] for item in variants] == [
        "classic",
        "editorial",
        "food_first",
        "benefit",
    ]
    canvas = render_benefit_pin(Image.new("RGB", (1024, 1024), "#B8A58D"), recipe)
    assert canvas.size == (1000, 1500)

