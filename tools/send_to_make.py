import json
import os
import time
import uuid
import urllib.request
from pathlib import Path

from bear_memory import (
    is_step_complete,
    mark_step_complete,
    mark_step_failed,
)


WEBHOOK = os.environ["MAKE_WEBHOOK_URL"]
SITE_BASE_URL = os.environ.get(
    "SITE_BASE_URL",
    "https://40400meals.com",
).rstrip("/")

QUEUE = Path("outputs/make_queue")
PINTEREST_IMAGE_DIR = Path("outputs/images/pinterest")

PUBLIC_IMAGE_WAIT_SECONDS = 180
PUBLIC_IMAGE_RETRY_SECONDS = 10


def load_json(path, default=None):
    if not path.exists():
        return default

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def find_pinterest_image(payload, slug):
    candidates = []

    image_path = payload.get("image_path")
    image_filename = (
        payload.get("image_filename")
        or payload.get("pin_filename")
    )

    if image_path:
        candidates.append(Path(image_path))

    if image_filename:
        candidates.append(PINTEREST_IMAGE_DIR / image_filename)

    if slug:
        candidates.append(
            PINTEREST_IMAGE_DIR / f"{slug}-pinterest-pin.png"
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def add_image_metadata(payload, image_file):
    payload["image_filename"] = image_file.name
    payload["image_path"] = str(image_file)
    payload["image_mime_type"] = "image/png"
    payload["image_url"] = (
        f"{SITE_BASE_URL}/{str(image_file).lstrip('/')}"
    )

    return payload


def wait_for_public_image(image_url):
    deadline = time.monotonic() + PUBLIC_IMAGE_WAIT_SECONDS

    while time.monotonic() < deadline:
        request = urllib.request.Request(
            image_url,
            headers={"User-Agent": "BearOS/1.0"},
            method="HEAD",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=15,
            ) as response:
                if 200 <= response.status < 400:
                    print(
                        f"Public Pinterest image is ready: {image_url}",
                        flush=True,
                    )
                    return
        except Exception as error:
            print(
                f"Image not live yet: {image_url} ({error})",
                flush=True,
            )

        time.sleep(PUBLIC_IMAGE_RETRY_SECONDS)

    raise RuntimeError(
        "Pinterest image did not become publicly available "
        f"within {PUBLIC_IMAGE_WAIT_SECONDS} seconds: {image_url}"
    )


def build_multipart_payload(payload, image_file):
    boundary = f"----BearOSBoundary{uuid.uuid4().hex}"
    body = bytearray()

    def add_field(name, value):
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; '
                f'name="{name}"\r\n\r\n'
            ).encode("utf-8")
        )

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    def add_file(field_name, file_path, mime_type):
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; '
                f'name="{field_name}"; '
                f'filename="{file_path.name}"\r\n'
            ).encode("utf-8")
        )
        body.extend(
            f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8")
        )
        body.extend(file_path.read_bytes())
        body.extend(b"\r\n")

    for key, value in payload.items():
        add_field(key, value)

    add_file("pinterest_image", image_file, "image/png")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    return (
        bytes(body),
        f"multipart/form-data; boundary={boundary}",
    )


def send_payload_to_make(payload, image_file, file_name):
    data, content_type = build_multipart_payload(
        payload,
        image_file,
    )

    request = urllib.request.Request(
        WEBHOOK,
        data=data,
        headers={"Content-Type": content_type},
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=60,
    ) as response:
        print(
            f"Sent {file_name} to Make ({response.status})",
            flush=True,
        )
        return response.status


def main():
    if not QUEUE.exists():
        print("No make_queue folder found.")
        return

    files = sorted(QUEUE.glob("*.json"))

    if not files:
        print("No queue files to send.")
        return

    failures = []

    for file in files:
        print(f"Preparing {file.name}", flush=True)

        payload = load_json(file, default={})
        slug = payload.get("slug")

        if not slug:
            slug = file.stem.replace("-pinterest", "")
            payload["slug"] = slug

        if is_step_complete(slug, "pinterest"):
            print(
                f"Pinterest already completed for {slug}",
                flush=True,
            )
            file.unlink()
            print(
                f"Removed duplicate queue file: {file.name}",
                flush=True,
            )
            continue

        image_file = find_pinterest_image(payload, slug)

        if not image_file:
            error = (
                f"No Pinterest image found for recipe: {slug}"
            )
            print(error, flush=True)
            mark_step_failed(slug, "pinterest", error)
            failures.append(error)
            continue

        payload = add_image_metadata(payload, image_file)

        try:
            wait_for_public_image(payload["image_url"])

            status = send_payload_to_make(
                payload,
                image_file,
                file.name,
            )

            if not 200 <= status < 300:
                raise RuntimeError(
                    f"Make returned HTTP {status}"
                )

            mark_step_complete(
                slug,
                "pinterest",
                {
                    "destination_url": payload.get(
                        "destination_url"
                    ),
                    "image_url": payload.get("image_url"),
                    "file_name": file.name,
                },
            )

            file.unlink()

            print(
                f"Recorded Pinterest completion for {slug}",
                flush=True,
            )
            print(
                f"Removed {file.name} from queue",
                flush=True,
            )

        except Exception as error:
            message = f"{slug}: {error}"
            print(
                f"Pinterest publishing failed: {message}",
                flush=True,
            )
            mark_step_failed(
                slug,
                "pinterest",
                str(error),
            )
            failures.append(message)

    if failures:
        raise RuntimeError(
            "Pinterest publishing failed for: "
            + " | ".join(failures)
        )


if __name__ == "__main__":
    main()
