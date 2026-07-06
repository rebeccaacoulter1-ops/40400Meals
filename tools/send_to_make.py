import base64
import json
import os
import uuid
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


def find_pinterest_image(payload, slug):
    candidates = []

    image_path = payload.get("image_path")
    image_filename = payload.get("image_filename") or payload.get("pin_filename")

    if image_path:
        candidates.append(Path(image_path))

    if image_filename:
        candidates.append(PINTEREST_IMAGE_DIR / image_filename)

    if slug:
        candidates.append(PINTEREST_IMAGE_DIR / f"{slug}-pinterest-pin.png")

    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate

    matches = list(PINTEREST_IMAGE_DIR.glob("*-pinterest-pin.png"))

    if len(matches) == 1:
        return matches[0]

    return None


def add_image_metadata(payload, image_file):
    if not image_file:
        return payload

    payload["image_filename"] = image_file.name
    payload["image_path"] = str(image_file)
    payload["image_mime_type"] = "image/png"

    if not payload.get("image_base64"):
        image_bytes = image_file.read_bytes()
        payload["image_base64"] = base64.b64encode(image_bytes).decode("utf-8")

    return payload


def build_multipart_payload(payload, image_file):
    boundary = f"----BearOSBoundary{uuid.uuid4().hex}"
    body = bytearray()

    def add_field(name, value):
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
        )

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    def add_file(field_name, file_path, mime_type):
        file_name = file_path.name
        file_data = file_path.read_bytes()

        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{file_name}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
        body.extend(file_data)
        body.extend(b"\r\n")

    for key, value in payload.items():
        add_field(key, value)

    if image_file:
        add_file("pinterest_image", image_file, "image/png")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    content_type = f"multipart/form-data; boundary={boundary}"

    return bytes(body), content_type


def send_payload_to_make(payload, image_file, file_name):
    data, content_type = build_multipart_payload(payload, image_file)

    request = urllib.request.Request(
        WEBHOOK,
        data=data,
        headers={"Content-Type": content_type},
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

    image_file = find_pinterest_image(payload, slug)

    if image_file:
        print(f"Attached image file to payload: {image_file}")
        payload = add_image_metadata(payload, image_file)
    else:
        print(f"No Pinterest image found for slug: {slug}")

    try:
        send_payload_to_make(payload, image_file, file.name)

        file.unlink()
        print(f"Removed {file.name} from queue")

    
    except Exception as e:
        print(f"Failed to send {file.name}")
        print(e)
