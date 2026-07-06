import json
from datetime import datetime, timezone
from pathlib import Path


# -----------------------------
# File locations
# -----------------------------

MANIFEST_FILE = Path("memory/bear_manifest.json")


# -----------------------------
# Core manifest helpers
# -----------------------------

def load_manifest():
    if not MANIFEST_FILE.exists():
        return {"recipes": {}}

    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest):
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def ensure_recipe(manifest, slug):
    if "recipes" not in manifest:
        manifest["recipes"] = {}

    if slug not in manifest["recipes"]:
        manifest["recipes"][slug] = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "steps": {}
        }

    if "steps" not in manifest["recipes"][slug]:
        manifest["recipes"][slug]["steps"] = {}

    return manifest["recipes"][slug]


# -----------------------------
# Public Bear Memory functions
# -----------------------------

def is_step_complete(slug, step_name):
    manifest = load_manifest()
    recipe = ensure_recipe(manifest, slug)

    return recipe["steps"].get(step_name, {}).get("complete", False)


def mark_step_complete(slug, step_name, details=None):
    manifest = load_manifest()
    recipe = ensure_recipe(manifest, slug)

    now = datetime.now(timezone.utc).isoformat()

    recipe["steps"][step_name] = {
        "complete": True,
        "completed_at_utc": now,
        "details": details or {}
    }

    recipe["updated_at_utc"] = now

    save_manifest(manifest)


def mark_step_failed(slug, step_name, error_message):
    manifest = load_manifest()
    recipe = ensure_recipe(manifest, slug)

    now = datetime.now(timezone.utc).isoformat()

    recipe["steps"][step_name] = {
        "complete": False,
        "failed_at_utc": now,
        "error": str(error_message)
    }

    recipe["updated_at_utc"] = now

    save_manifest(manifest)


def get_recipe_status(slug):
    manifest = load_manifest()
    recipe = ensure_recipe(manifest, slug)

    return recipe
