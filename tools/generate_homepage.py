import html
import json
import re
from pathlib import Path
from textwrap import shorten


RECIPES_DIR = Path("recipes")
INDEX_FILE = Path("index.html")
RECIPES_INDEX_FILE = Path("recipes.html")
SITEMAP_FILE = Path("sitemap.xml")
SITE_URL = "https://40400meals.com/"

START_MARKER = "        <!-- BEAR:RECIPE-CARDS:START -->"
END_MARKER = "        <!-- BEAR:RECIPE-CARDS:END -->"
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


def food_image(data, homepage, slug):
    images = data.get("images", {}) or {}
    image_path = clean_text(
        images.get("hero_image_url")
        or homepage.get("food_image_path")
        or homepage.get("image_path")
        or f"outputs/images/food_photos/{slug}-food-photo.png"
    )

    if image_path.startswith(SITE_URL):
        return image_path[len(SITE_URL):]

    return image_path


def recipe_sort_value(data, recipe, homepage):
    return clean_text(
        homepage.get("published_at")
        or recipe.get("published_at")
        or recipe.get("date_published")
        or data.get("date_published")
        or "0000-00-00"
    )


def load_publishable_recipes():
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

        published_at = recipe_sort_value(data, recipe, homepage)

        cards.append(
            {
                "slug": slug,
                "title": title,
                "summary": summary,
                "tags": tags[:3],
                "image_path": food_image(data, homepage, slug),
                "published_at": published_at,
                "lastmod": published_at[:10] if published_at else "",
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

    return cards


def render_card(card, indent="        "):
    slug = html.escape(card["slug"], quote=True)
    title = html.escape(card["title"])
    summary = html.escape(card["summary"])
    image_path = html.escape(card["image_path"], quote=True)

    tag_lines = "\n".join(
        f'{indent}        <span class="tag">{html.escape(tag)}</span>'
        for tag in card["tags"]
    )

    return f'''{indent}<article class="recipe-card">
{indent}  <a href="recipes/{slug}.html">
{indent}    <img
{indent}      class="recipe-img"
{indent}      src="{image_path}"
{indent}      alt="{title}"
{indent}      loading="lazy"
{indent}    />
{indent}    <div class="recipe-body">
{indent}      <h3>{title}</h3>
{indent}      <p>{summary}</p>
{indent}      <div class="tags">
{tag_lines}
{indent}      </div>
{indent}    </div>
{indent}  </a>
{indent}</article>'''


def replace_marked_cards(index_html, rendered_cards):
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        flags=re.DOTALL,
    )

    replacement = START_MARKER + "\n" + rendered_cards + "\n" + END_MARKER
    updated_html, replacements = pattern.subn(
        lambda _: replacement,
        index_html,
        count=1,
    )

    if replacements != 1:
        raise ValueError("Bear homepage markers were not found exactly once.")

    return updated_html


def install_markers_and_cards(index_html, rendered_cards):
    recipes_open = '      <div class="recipes">'
    method_section = '    <section id="method">'

    open_index = index_html.find(recipes_open)
    method_index = index_html.find(method_section)

    if open_index == -1 or method_index == -1:
        raise ValueError("Could not locate the homepage recipe grid or method section.")

    content_start = index_html.find("\n", open_index)
    if content_start == -1:
        raise ValueError("Could not locate the recipe-grid opening line.")
    content_start += 1

    content_end = index_html.rfind("      </div>", content_start, method_index)
    if content_end == -1:
        raise ValueError("Could not locate the closing div for the homepage recipe grid.")

    managed_block = START_MARKER + "\n" + rendered_cards + "\n" + END_MARKER + "\n"
    return index_html[:content_start] + managed_block + index_html[content_end:]


def update_homepage(cards):
    homepage_cards = cards[:MAX_HOMEPAGE_RECIPES]
    rendered_cards = "\n\n".join(render_card(card) for card in homepage_cards)
    index_html = INDEX_FILE.read_text(encoding="utf-8")

    if START_MARKER in index_html or END_MARKER in index_html:
        if index_html.count(START_MARKER) != 1 or index_html.count(END_MARKER) != 1:
            raise ValueError("Homepage has invalid Bear recipe marker counts.")
        updated_html = replace_marked_cards(index_html, rendered_cards)
    else:
        updated_html = install_markers_and_cards(index_html, rendered_cards)

    # The homepage shows the newest recipes. These links take visitors to the
    # complete, automatically generated recipe library.
    updated_html = updated_html.replace(
        '<a href="#recipes">Recipes</a>',
        '<a href="recipes.html">Recipes</a>',
    )
    updated_html = updated_html.replace(
        '<a href="#recipes" class="btn btn-primary">Browse Recipes</a>',
        '<a href="recipes.html" class="btn btn-primary">Browse All Recipes</a>',
    )

    view_all = '''\n      <div style="text-align:center; margin-top:34px;">\n        <a href="recipes.html" class="btn btn-primary">View All Recipes</a>\n      </div>'''
    recipes_section_end = '      </div>\n    </section>\n\n    <section id="method">'
    if 'href="recipes.html" class="btn btn-primary">View All Recipes</a>' not in updated_html:
        updated_html = updated_html.replace(
            recipes_section_end,
            '      </div>' + view_all + '\n    </section>\n\n    <section id="method">',
            1,
        )

    if updated_html != index_html:
        INDEX_FILE.write_text(updated_html, encoding="utf-8")
        print(f"Homepage updated with {len(homepage_cards)} latest recipe cards.")
    else:
        print("Homepage recipe cards and recipe-library links are already current.")


def render_recipes_index(cards):
    rendered_cards = "\n\n".join(render_card(card, indent="      ") for card in cards)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>All High-Protein Recipes | 40/400 Meals</title>
  <meta name="description" content="Browse every 40/400 Meals recipe in one place: practical high-protein meals built around roughly 40 grams of protein and about 400 calories." />
  <link rel="canonical" href="https://40400meals.com/recipes.html" />
  <style>
    :root {{
      --cream: #faf7f2;
      --chocolate: #2b2118;
      --orange: #a4571b;
      --soft-sage: #eef4ea;
      --white: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--cream);
      color: var(--chocolate);
      line-height: 1.6;
    }}
    header {{
      background: var(--white);
      padding: 22px 8%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 4px 20px rgba(43, 33, 24, 0.08);
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    .logo {{
      display: flex;
      align-items: center;
      gap: 12px;
      color: var(--chocolate);
      font-size: 26px;
      font-weight: 800;
      letter-spacing: -1px;
      text-decoration: none;
    }}
    .logo-mark {{
      display: grid;
      width: 52px;
      height: 52px;
      place-items: center;
      border: 2px solid #c98046;
      border-radius: 50%;
      background: var(--cream);
      font-size: 13px;
      line-height: 1;
      letter-spacing: -0.8px;
    }}
    nav a {{
      margin-left: 28px;
      text-decoration: none;
      color: var(--chocolate);
      font-weight: 700;
    }}
    .intro {{
      padding: 74px 8% 42px;
      text-align: center;
      max-width: 920px;
      margin: auto;
    }}
    .eyebrow {{
      display: inline-block;
      background: var(--soft-sage);
      color: #4f674d;
      padding: 9px 16px;
      border-radius: 999px;
      font-weight: 800;
      margin-bottom: 18px;
    }}
    h1 {{
      font-size: clamp(44px, 7vw, 72px);
      line-height: 1;
      letter-spacing: -2.5px;
      margin: 0 0 20px;
    }}
    .intro p {{
      color: #6b5d52;
      font-size: 19px;
      margin: 0 auto;
      max-width: 720px;
    }}
    .library {{ padding: 26px 8% 80px; }}
    .library-count {{
      text-align: center;
      font-weight: 800;
      color: #6b5d52;
      margin-bottom: 30px;
    }}
    .recipes {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 26px;
      max-width: 1400px;
      margin: auto;
    }}
    .recipe-card {{
      background: white;
      border-radius: 28px;
      overflow: hidden;
      box-shadow: 0 14px 35px rgba(43, 33, 24, 0.10);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .recipe-card:hover {{
      transform: translateY(-5px);
      box-shadow: 0 20px 44px rgba(43, 33, 24, 0.15);
    }}
    .recipe-card > a {{ color: inherit; text-decoration: none; }}
    .recipe-img {{
      display: block;
      width: 100%;
      aspect-ratio: 2 / 3;
      object-fit: cover;
      object-position: top;
    }}
    .recipe-body {{ padding: 24px; }}
    .recipe-body h3 {{ margin: 0 0 12px; font-size: 24px; line-height: 1.15; }}
    .recipe-body p {{ color: #6b5d52; }}
    .tags {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }}
    .tag {{
      background: var(--soft-sage);
      color: #4d634a;
      padding: 7px 11px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 800;
    }}
    .planner-cta {{
      max-width: 920px;
      margin: 0 auto 80px;
      padding: 42px 28px;
      text-align: center;
      background: #fbf1df;
      border: 1px solid #ead8c9;
      border-radius: 30px;
    }}
    .planner-cta h2 {{ margin: 0 0 10px; font-size: 34px; }}
    .planner-cta p {{ color: #6b5d52; margin-bottom: 24px; }}
    .btn {{
      display: inline-block;
      padding: 15px 28px;
      border-radius: 999px;
      text-decoration: none;
      font-weight: 800;
      background: var(--orange);
      color: white;
    }}
    footer {{ text-align: center; padding: 45px 8%; color: #76675c; }}
    footer a {{ color: #76675c; font-weight: 700; margin: 0 8px; text-decoration: none; }}
    @media (max-width: 850px) {{
      header {{ flex-direction: column; gap: 12px; }}
      nav {{ text-align: center; }}
      nav a {{ margin: 0 9px; }}
    }}
  </style>
</head>
<body>
  <header>
    <a class="logo" href="index.html">
      <span class="logo-mark">40/400</span>
      <span>40/400 Meals</span>
    </a>
    <nav>
      <a href="recipes.html">Recipes</a>
      <a href="index.html#method">Start Here</a>
      <a href="index.html#weekly-planner">Weekly Planner</a>
      <a href="about.html">About</a>
      <a href="contact.html">Contact</a>
    </nav>
  </header>

  <main>
    <section class="intro">
      <div class="eyebrow">The complete 40/400 recipe library</div>
      <h1>All Recipes</h1>
      <p>Browse every published 40/400 meal in one place. High-protein, practical recipes designed for real schedules, real families, and food you actually want to eat.</p>
    </section>

    <section class="library">
      <div class="library-count">{len(cards)} recipes and growing</div>
      <div class="recipes">
{rendered_cards}
      </div>
    </section>

    <section class="planner-cta">
      <h2>Want the week planned for you?</h2>
      <p>Get seven complete high-protein meals, a grocery list, and a simple prep plan in the 40/400 Weekly Planner.</p>
      <a class="btn" href="index.html#weekly-planner">See the Weekly Planner</a>
    </section>
  </main>

  <footer>
    <p>
      <a href="recipes.html">All Recipes</a>
      <a href="about.html">About</a>
      <a href="contact.html">Contact</a>
      <a href="privacy.html">Privacy</a>
      <a href="affiliate-disclosure.html">Affiliate Disclosure</a>
    </p>
    <p>© 2026 40/400 Meals • Powered by Bear OS</p>
  </footer>
</body>
</html>
'''


def update_recipes_index(cards):
    content = render_recipes_index(cards)
    if RECIPES_INDEX_FILE.exists() and RECIPES_INDEX_FILE.read_text(encoding="utf-8") == content:
        print("All Recipes page is already current.")
        return
    RECIPES_INDEX_FILE.write_text(content, encoding="utf-8")
    print(f"All Recipes page updated with {len(cards)} recipes.")


def sitemap_entry(location, lastmod=""):
    line = f"    <loc>{html.escape(location)}</loc>"
    if lastmod:
        line += f"\n    <lastmod>{html.escape(lastmod)}</lastmod>"
    return f"  <url>\n{line}\n  </url>"


def update_sitemap(cards):
    entries = [
        sitemap_entry(SITE_URL, "2026-09-02"),
        sitemap_entry(f"{SITE_URL}recipes.html", "2026-09-02"),
        sitemap_entry(f"{SITE_URL}about.html"),
        sitemap_entry(f"{SITE_URL}contact.html"),
        sitemap_entry(f"{SITE_URL}privacy.html"),
        sitemap_entry(f"{SITE_URL}affiliate-disclosure.html"),
    ]

    entries.extend(
        sitemap_entry(
            f"{SITE_URL}recipes/{card['slug']}.html",
            card.get("lastmod", ""),
        )
        for card in cards
    )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )

    if SITEMAP_FILE.exists() and SITEMAP_FILE.read_text(encoding="utf-8") == sitemap:
        print("Sitemap is already current.")
        return

    SITEMAP_FILE.write_text(sitemap, encoding="utf-8")
    print(f"Sitemap updated with {len(cards)} recipe URLs plus site pages.")


def main():
    if not INDEX_FILE.exists():
        raise FileNotFoundError(f"Homepage not found: {INDEX_FILE}")

    cards = load_publishable_recipes()
    if not cards:
        raise ValueError("No publishable recipe JSON files were found.")

    update_homepage(cards)
    update_recipes_index(cards)
    update_sitemap(cards)


if __name__ == "__main__":
    main()
