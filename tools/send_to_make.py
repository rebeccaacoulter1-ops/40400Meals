import json
import os
import base64
import urllib.request
from pathlib import Path

# -----------------------------
# Environment variables
# -----------------------------

WEBHOOK = os.environ["MAKE_WEBHOOK_URL"]


# -----------------------------
# File locations
# -----------------------------

QUEUE = Path("outputs/make_queue")
PINTEREST_IMAGE_DIR = Path("outputs/images/pinterest")


# -----------------------------
# Helper functions
# -----------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_pinterest_image(slug):
    image_file = PINTEREST_IMAGE_DIR / f"{slug}-pinterest-pin.png"

    if image_file.exists():
        return image_file

    return None


def encode_image_base64(image_file):
    with open(image_file, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def send_payload_to_make(payload, file_name):
    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        WEBHOOK,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request) as response:
        print(f"Sent {file_name} ({response.status})")


# -----------------------------
# Main process
# -----------------------------

if not QUEUE.exists():
    print("No make_queue folder found.")
    quit()

files = list(QUEUE.glob("*.json"))

if not files:
    print("No queue files to send.")
    quit()

for file in files:
    print(f"Preparing {file.name}")

    payload = load_json(file)

    slug = payload.get("slug")

    if not slug:
        slug = file.stem.replace("-pinterest", "")

    image_file = find_pinterest_image(slug)

    if image_file:
        payload["image_filename"] = image_file.name
        payload["image_path"] = str(image_file)
        payload["image_base64"] = encode_image_base64(image_file)
        payload["image_mime_type"] = "image/png"

        print(f"Attached image to payload: {image_file}")
    else:
        print(f"No Pinterest image found for slug: {slug}")

    try:
        send_payload_to_make(payload, file.name)

        # Delete the queue file only after Make.com receives it successfully
        file.unlink()
        print(f"Removed {file.name} from queue")

    except Exception as e:
        print(f"Failed to send {file.name}")
        print(e)
