import html
import json
import re
from pathlib import Path
from textwrap import shorten


RECIPES_DIR = Path("recipes")
INDEX_FILE = Path("index.html")

START_MARKER = "        <!-- BEAR:RECIPE-CARDS:START -->"
END_MARKER = "        <!-- BEAR:RECIPE-CARDS:END -->"

# Show all current recipes, then cap the homepage as the library grows.
MAX_HOMEPAGE_RECIPES = 12


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def clean_text(value):
    return " ".join(str(value or "").split())


def format_number(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def recipe_sort_value(data, recipe, homepage):
    return clean_text(
        homepage.get("published_at")
        or recipe.get("published_at")
        or recipe.get("date_published")
        or data.get("date_published")
        or "0000-00-00"
    )


def load_homepage_recipes():
    cards = []

    for recipe_file in sorted(RECIPES_DIR.glob("*.json")):
        data = load_json(recipe_file)
        recipe = data.get("recipe", data)
        homepage = data.get("homepage", {}) or {}

        if homepage.get("hidden") is True:
            continue

        slug = clean_text(
            recipe.get("slug")
            or data.get("slug")
            or recipe_file.stem
        )
        title = clean_text(
            homepage.get("title")
            or recipe.get("title")
            or slug.replace("-", " ").title()
        )

        if not slug or not title:
            raise ValueError(
                f"{recipe_file} must include a recipe slug and title."
            )

        summary = clean_text(
            homepage.get("summary")
            or recipe.get("summary")
            or "A simple high-protein 40/400 recipe."
        )
        summary = shorten(summary, width=145, placeholder="…")

        macros = recipe.get("macros", {}) or {}
        times = recipe.get("times", {}) or {}

        protein = macros.get("protein_g")
        calories = macros.get("calories")
        minutes = times.get("total_minutes")

        tags = []
        if protein not in (None, ""):
            tags.append(f"{format_number(protein)}g Protein")
        if calories not in (None, ""):
            tags.append(f"{format_number(calories)} Calories")
        if minutes not in (None, ""):
            minute_label = "Minute" if str(minutes) == "1" else "Minutes"
            tags.append(f"{format_number(minutes)} {minute_label}")

        image_path = clean_text(
            homepage.get("image_path")
            or f"outputs/images/pinterest/{slug}-pinterest-pin.png"
        )

        cards.append(
            {
                "slug": slug,
                "title": title,
                "summary": summary,
                "tags": tags[:3],
                "image_path": image_path,
                "published_at": recipe_sort_value(data, recipe, homepage),
                "priority": int(homepage.get("priority", 0) or 0),
            }
        )

    cards.sort(
        key=lambda item: (
            item["published_at"],
            item["priority"],
            item["slug"],
        ),
        reverse=True,
    )

    return cards[:MAX_HOMEPAGE_RECIPES]


def render_card(card):
    slug = html.escape(card["slug"], quote=True)
    title = html.escape(card["title"])
    summary = html.escape(card["summary"])
    image_path = html.escape(card["image_path"], quote=True)

    tag_lines = "\n".join(
        f'                <span class="tag">{html.escape(tag)}</span>'
        for tag in card["tags"]
    )

    return f'''        <article class="recipe-card">
          <a href="recipes/{slug}.html">
            <img
              class="recipe-img"
              src="{image_path}"
              alt="{title}"
            />
            <div class="recipe-body">
              <h3>{title}</h3>
              <p>{summary}</p>
              <div class="tags">
{tag_lines}
              </div>
            </div>
          </a>
        </article>'''


def replace_marked_cards(index_html, rendered_cards):
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        flags=re.DOTALL,
    )

    replacement = (
        START_MARKER
        + "\n"
        + rendered_cards
        + "\n"
        + END_MARKER
    )

    updated_html, replacements = pattern.subn(
        lambda _: replacement,
        index_html,
        count=1,
    )

    if replacements != 1:
        raise ValueError(
            "Bear homepage markers were not found exactly once."
        )

    return updated_html


def install_markers_and_cards(index_html, rendered_cards):
    recipes_open = '      <div class="recipes">'
    method_section = '    <section id="method">'

    open_index = index_html.find(recipes_open)
    method_index = index_html.find(method_section)

    if open_index == -1 or method_index == -1:
        raise ValueError(
            "Could not locate the homepage recipe grid or method section."
        )

    content_start = index_html.find("\n", open_index)
    if content_start == -1:
        raise ValueError("Could not locate the recipe-grid opening line.")

    content_start += 1

    # The recipe grid's closing div is the final six-space-indented closing
    # div before the method section.
    content_end = index_html.rfind("      </div>", content_start, method_index)

    if content_end == -1:
        raise ValueError(
            "Could not locate the closing div for the homepage recipe grid."
        )

    managed_block = (
        START_MARKER
        + "\n"
        + rendered_cards
        + "\n"
        + END_MARKER
        + "\n"
    )

    return (
        index_html[:content_start]
        + managed_block
        + index_html[content_end:]
    )


def main():
    if not INDEX_FILE.exists():
        raise FileNotFoundError(f"Homepage not found: {INDEX_FILE}")

    cards = load_homepage_recipes()

    if not cards:
        raise ValueError("No publishable recipe JSON files were found.")

    rendered_cards = "\n\n".join(render_card(card) for card in cards)
    index_html = INDEX_FILE.read_text(encoding="utf-8")

    if START_MARKER in index_html or END_MARKER in index_html:
        if index_html.count(START_MARKER) != 1:
            raise ValueError("Homepage has an invalid Bear start marker count.")
        if index_html.count(END_MARKER) != 1:
            raise ValueError("Homepage has an invalid Bear end marker count.")

        updated_html = replace_marked_cards(index_html, rendered_cards)
    else:
        updated_html = install_markers_and_cards(
            index_html,
            rendered_cards,
        )

    if updated_html == index_html:
        print("Homepage recipe cards are already current.")
        return

    INDEX_FILE.write_text(updated_html, encoding="utf-8")
    print(
        f"Homepage updated with {len(cards)} recipe card"
        f"{'' if len(cards) == 1 else 's'}."
    )


if __name__ == "__main__":
    main()
