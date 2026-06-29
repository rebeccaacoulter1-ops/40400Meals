import json
import os
import urllib.request
from pathlib import Path

WEBHOOK = os.environ["MAKE_WEBHOOK_URL"]

QUEUE = Path("outputs/make_queue")

if not QUEUE.exists():
    print("No make_queue folder found.")
    quit()

files = list(QUEUE.glob("*.json"))

if not files:
    print("No queue files to send.")
    quit()

for file in files:
    print(f"Sending {file.name}")

    with open(file, "rb") as f:
        data = f.read()

    request = urllib.request.Request(
        WEBHOOK,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request) as response:
            print(f"Sent {file.name} ({response.status})")

        # Delete the queue file only after Make.com receives it successfully
        file.unlink()
        print(f"Removed {file.name} from queue")

    except Exception as e:
        print(f"Failed to send {file.name}")
        print(e)
