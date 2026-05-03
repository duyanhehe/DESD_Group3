"""
Unified script to download all AI models from Kaggle.

Usage:
    python apps/ai_engine/download_models.py

This downloads:
    1. Grading model (fruit-disease-v2) to AI_GRADING_BEST_PT_PATH
    2. Recommendation model to AI_RECOMMENDATION_MODEL_PATH
"""

import os
import sys
from pathlib import Path
import kagglehub
import shutil

# ── Django Setup ──
BASE_DIR = Path(__file__).resolve().parents[2]

# Only modify sys.path if not already done (prevents duplicates)
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Defer django setup to when functions are called
_django_setup_done = False
_settings = None


def _setup_django():
    global _django_setup_done, _settings
    if not _django_setup_done:
        import django

        # Check if django is already configured (e.g., from apps.py ready())
        if not django.apps.apps.ready:
            django.setup()
        from django.conf import settings

        _settings = settings
        _django_setup_done = True


GRADING_MODEL_NAME = "cazofi/fruit-disease-v2/pyTorch/default"
RECOMMENDATION_MODEL_NAME = "duyanhehe/recommendation-model/other/default"


def _get_settings():
    global _django_setup_done, _settings
    # If Django apps are already ready, use settings directly
    if not _django_setup_done:
        try:
            from django.conf import settings as django_settings

            _settings = django_settings
            _django_setup_done = True
        except Exception:
            # Django not configured yet, run setup
            _setup_django()
    return _settings


def get_grading_model_dir():
    return _get_settings().AI_GRADING_BEST_PT_PATH.parent


def get_recommendation_model_path():
    return _get_settings().AI_RECOMMENDATION_MODEL_PATH



def download_grading_model():
    """Download the grading model from Kaggle."""
    GRADING_MODEL_DIR = get_grading_model_dir()
    GRADING_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 50)
    print("Downloading GRADING model from Kaggle...")
    print(f"Model: {GRADING_MODEL_NAME}")
    print("=" * 50)

    try:
        path = Path(kagglehub.model_download(GRADING_MODEL_NAME))
        print(f"Kaggle cache path: {path}")

        # Check if the cache directory is empty
        files = list(path.glob("*"))
        if not files:
            print("Cache is empty! Clearing and forcing re-download...")
            shutil.rmtree(path)
            path = Path(kagglehub.model_download(GRADING_MODEL_NAME))
            files = list(path.glob("*"))

        if not files:
            print("Warning: No files found in the model download.")
            return False

        # Copy files to project model directory
        for file in files:
            print(f"Copying {file.name} to {GRADING_MODEL_DIR}...")
            shutil.copy(str(file), GRADING_MODEL_DIR / file.name)

        print(f"Grading model ready at: {GRADING_MODEL_DIR}")
        return True

    except Exception as e:
        print(f"Error downloading grading model: {e}")
        return False


def download_recommendation_model():
    """Download the recommendation model from Kaggle."""
    RECOMMENDATION_MODEL_PATH = get_recommendation_model_path()
    RECOMMENDATION_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 50)
    print("Downloading RECOMMENDATION model from Kaggle...")
    print(f"Model: {RECOMMENDATION_MODEL_NAME}")
    print("=" * 50)

    try:
        path = Path(kagglehub.model_download(RECOMMENDATION_MODEL_NAME))
        print(f"Kaggle cache path: {path}")

        # Check if the cache directory is empty
        files = list(path.glob("*"))
        if not files:
            print("Cache is empty! Clearing and forcing re-download...")
            shutil.rmtree(path)
            path = Path(kagglehub.model_download(RECOMMENDATION_MODEL_NAME))
            files = list(path.glob("*"))

        if not files:
            print("Warning: No files found in the model download.")
            return False

        # Copy files to project model directory
        for file in files:
            dest_path = RECOMMENDATION_MODEL_PATH.parent / file.name
            print(f"Copying {file.name} to {dest_path}...")
            if file.suffix == ".pkl":
                shutil.copy(str(file), RECOMMENDATION_MODEL_PATH)
            else:
                shutil.copy(str(file), dest_path)

        print(f"Recommendation model ready at: {RECOMMENDATION_MODEL_PATH}")
        return True

    except Exception as e:
        print(f"Error downloading recommendation model: {e}")
        return False


def check_models_exist():
    """Check if both model files exist."""
    conf_settings = _get_settings()
    grading_exists = conf_settings.AI_GRADING_BEST_PT_PATH.exists()
    recommendation_exists = get_recommendation_model_path().exists()

    print("\n" + "=" * 50)
    print("Model Status Check:")
    print("=" * 50)
    print(f"Grading model: {'✓ EXISTS' if grading_exists else '✗ MISSING'}")
    print(f"  Path: {conf_settings.AI_GRADING_BEST_PT_PATH}")
    print(f"Recommendation model: {'✓ EXISTS' if recommendation_exists else '✗ MISSING'}")
    print(f"  Path: {get_recommendation_model_path()}")

    return grading_exists and recommendation_exists


def download_all(auto_mode=False):
    """
    Download all models.

    Args:
        auto_mode: If True, skip prompts and re-download checks (for auto-download on server start)

    Returns:
        tuple: (grading_success, recommendation_success)
    """
    if not auto_mode:
        print("\n" + "=" * 50)
        print("AI MODEL DOWNLOAD UTILITY")
        print("=" * 50)

    # Check current status
    all_exist = check_models_exist()

    if all_exist and not auto_mode:
        print("\nAll models are already downloaded.")
        response = input("Re-download anyway? (y/N): ").strip().lower()
        if response not in ("y", "yes"):
            print("Download cancelled.")
            return (True, True)

    if auto_mode and not all_exist:
        print("AI models not found. Auto-downloading...")

    # Download both models
    grading_success = download_grading_model()
    recommendation_success = download_recommendation_model()

    if not auto_mode:
        # Final status
        print("\n" + "=" * 50)
        print("Download Summary:")
        print("=" * 50)
        print(f"Grading model: {'✓ SUCCESS' if grading_success else '✗ FAILED'}")
        print(f"Recommendation model: {'✓ SUCCESS' if recommendation_success else '✗ FAILED'}")

        if grading_success and recommendation_success:
            print("\nAll models downloaded successfully!")
            print("You can now run: python manage.py runserver")
        else:
            print("\nSome downloads failed. Please check the errors above.")
            sys.exit(1)
    else:
        if grading_success and recommendation_success:
            print("AI models downloaded successfully.")
        else:
            print("Warning: Some AI model downloads failed.", file=sys.stderr)

    return (grading_success, recommendation_success)


def main():
    """CLI entry point for manual downloads."""
    download_all(auto_mode=False)


if __name__ == "__main__":
    main()
