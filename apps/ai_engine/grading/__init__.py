"""
Fruit/Vegetable Grading Module

Provides YOLO-based detection and OpenCV-based quality grading
with explainable AI (xAI) heatmap visualization.
"""

from .grader import QualityGrader
from .detector import FruitDetector
from .explainer import HeatmapExplainer, YoloModelWrapper
from .services import GradingService
from .inference import predict, predict_from_array, predict_batch
from .loader import get_detector

__all__ = [
    'QualityGrader',
    'FruitDetector',
    'HeatmapExplainer',
    'YoloModelWrapper',
    'GradingService',
    'predict',
    'predict_from_array',
    'predict_batch',
    'get_detector',
]