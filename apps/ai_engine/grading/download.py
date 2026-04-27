import os
import sys
from pathlib import Path
import kagglehub
import shutil

# ── Django Setup ──
BASE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django

django.setup()

from django.conf import settings

MODEL_NAME = "cazofi/fruit-disease-v2/pyTorch/default"
MODEL_DIR = settings.AI_GRADING_BEST_PT_PATH.parent


def download_model():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading model from Kaggle...")

    try:
        path = Path(kagglehub.model_download(MODEL_NAME))
        print(f"Kaggle path: {path}")

        # Check if the cache directory is empty (common if 'move' was used previously)
        files = list(path.glob("*"))
        if not files:
            print("Cache is empty! Clearing and forcing re-download...")
            shutil.rmtree(path)
            path = Path(kagglehub.model_download(MODEL_NAME))
            files = list(path.glob("*"))

        if not files:
            print("Warning: No files found in the model download.")
            return

        # Copy files to your model directory
        for file in files:
            print(f"Copying {file.name} to project...")
            shutil.copy(str(file), MODEL_DIR / file.name)

        print("Model ready at:", MODEL_DIR)

    except Exception as e:
        raise RuntimeError(f"Failed to download model: {e}")


if __name__ == "__main__":
    download_model()
