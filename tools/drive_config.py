from pathlib import Path

# Bear OS output settings
# For now, Bear OS writes to a local outputs folder.
# Later, Make.com will move or read this into Google Drive.

OUTPUT_ROOT = Path("outputs")

PLATFORM_FOLDERS = {
    "pinterest": OUTPUT_ROOT / "pinterest",
    "instagram": OUTPUT_ROOT / "instagram",
    "facebook": OUTPUT_ROOT / "facebook",
    "email": OUTPUT_ROOT / "email",
    "youtube": OUTPUT_ROOT / "youtube",
    "image_prompts": OUTPUT_ROOT / "image_prompts",
    "make_queue": OUTPUT_ROOT / "make_queue",
}
