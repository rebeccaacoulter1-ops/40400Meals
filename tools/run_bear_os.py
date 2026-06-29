import subprocess
import sys

GENERATORS = [
    "tools/generate_recipe.py",
    "tools/generate_social_content.py",
    "tools/generate_pinterest.py",
    "tools/send_to_make.py",
]

def run_generator(path):
    print(f"\nRunning {path}...")
    result = subprocess.run([sys.executable, path], capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"{path} failed")

    print(f"Finished {path}")

def main():
    print("Starting Bear OS Generator Engine...")

    for generator in GENERATORS:
        run_generator(generator)

    print("\nBear OS Generator Engine complete.")

if __name__ == "__main__":
    main()
