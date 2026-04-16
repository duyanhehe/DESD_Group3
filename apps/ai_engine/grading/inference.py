import os
import sys
import cv2
from pathlib import Path

# ── Django Setup ──
BASE_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django

django.setup()

from apps.ai_engine.grading.loader import get_detector
from apps.ai_engine.grading.detector import FruitDetector
from apps.ai_engine.grading.grader import QualityGrader

grader = QualityGrader()


def predict(image_path: str):
    image = cv2.imread(image_path)

    model = get_detector()

    detector = FruitDetector()
    detector.model = model  # inject loaded model

    bbox, class_name = detector.detect(image_path)

    if bbox is None:
        return {"error": "No fruit detected"}

    cropped = detector.crop_image(image, bbox)

    img_no_bg, fruit_mask = grader.remove_background(cropped)

    lower_hsv = (0, 50, 50)
    upper_hsv = (30, 255, 255)

    result = grader.find_defects(img_no_bg, fruit_mask, lower_hsv, upper_hsv)

    fruit_area, rot_area, *_ = result

    ratio = rot_area / fruit_area if fruit_area else 0
    grade, percent = grader.calculate_grade(ratio)

    return {
        "class": class_name,
        "grade": grade,
        "defect_percent": percent,
    }
