import subprocess
import sys


GENERATORS = [
    "tools/generate_recipe.py",
    "tools/generate_social_content.py",
    "tools/design_engine.py",
    "tools/image_engine.py",
    "tools/generate_pinterest.py",
]


def run_generator(path):
    print(f"\nRunning {path}...", flush=True)

    try:
        subprocess.run(
            [sys.executable, path],
            check=True,
            timeout=900,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"{path} exceeded the 15-minute safety limit."
        ) from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            f"{path} failed with exit code {error.returncode}."
        ) from error

    print(f"Finished {path}", flush=True)


def main():
    print("Starting Bear OS Generator Engine...", flush=True)

    for generator in GENERATORS:
        run_generator(generator)

    print(
        "\nBear OS content generation complete. "
        "Publishing will begin after generated files are committed.",
        flush=True,
    )


if __name__ == "__main__":
    main()
