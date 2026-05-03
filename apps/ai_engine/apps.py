from django.apps import AppConfig
from django.conf import settings
import sys


class AiEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_engine"
    verbose_name = "AI Engine"

    def ready(self):
        # Auto-download AI models if missing (runs after Django is fully ready)
        self._auto_download_models()

    def _auto_download_models(self):
        """Auto-download models if they don't exist (silent mode for Docker compatibility)."""
        # Get paths directly from settings
        grading_path = getattr(settings, "AI_GRADING_BEST_PT_PATH", None)
        recommendation_path = getattr(settings, "AI_RECOMMENDATION_MODEL_PATH", None)

        grading_exists = grading_path and grading_path.exists()
        recommendation_exists = recommendation_path and recommendation_path.exists()

        if grading_exists and recommendation_exists:
            return  # All models exist, nothing to do

        # Models are missing - download them
        print("AI models not found. Auto-downloading...", file=sys.stderr)

        try:
            # Import kagglehub functions directly (without triggering Django setup)
            from .download_models import download_grading_model, download_recommendation_model

            if not grading_exists:
                download_grading_model()

            if not recommendation_exists:
                download_recommendation_model()

            print("AI models downloaded successfully.")
        except Exception as e:
            # Log error but don't block server startup
            print(f"Warning: Could not auto-download AI models: {e}", file=sys.stderr)
