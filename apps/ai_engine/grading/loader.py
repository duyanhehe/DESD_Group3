from ultralytics import YOLO
from pathlib import Path
from django.conf import settings

# Cache variables
_detector_model = None


def get_detector():
    global _detector_model

    if _detector_model is None:
        model_path = settings.AI_GRADING_BEST_PT_PATH

        print(f"Loading YOLO model from {model_path}")
        _detector_model = YOLO(str(model_path))

    return _detector_model
