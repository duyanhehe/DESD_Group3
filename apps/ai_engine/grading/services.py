"""
Grading Service - High-level interface for fruit quality grading.
Provides methods for analyzing images from files or memory.
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Union, Optional
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings

from apps.ai_engine.grading.inference import predict, predict_from_array


class GradingService:
    """
    Service class for fruit grading operations.
    Handles both file-based and in-memory image analysis.
    """

    @staticmethod
    def analyze(image_path: str) -> dict:
        """
        Analyze fruit quality from an image file path.

        Args:
            image_path: Path to the image file

        Returns:
            dict: Grading result with grade, metrics, and XAI report
        """
        return predict(image_path)

    @staticmethod
    def analyze_array(image: np.ndarray, source_path: Optional[str] = None) -> dict:
        """
        Analyze fruit quality from a numpy array (OpenCV BGR image).

        Args:
            image: OpenCV BGR image as numpy array
            source_path: Optional source path for reference

        Returns:
            dict: Grading result with grade, metrics, and XAI report
        """
        return predict_from_array(image, source_path)

    @staticmethod
    def analyze_upload(uploaded_file: UploadedFile, save_temp: bool = False) -> dict:
        """
        Analyze fruit quality from an uploaded file (Django request).

        Args:
            uploaded_file: Django UploadedFile object
            save_temp: Whether to save the uploaded file temporarily

        Returns:
            dict: Grading result with grade, metrics, and XAI report
        """
        # Read image from uploaded file
        file_bytes = uploaded_file.read()
        nparr = np.frombuffer(file_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            return {
                "success": False,
                "error": "Could not decode image from uploaded file",
                "grade": "Unknown",
                "metrics": {}
            }

        result = predict_from_array(image, uploaded_file.name)

        # Optionally save temp file
        if save_temp and result.get("success"):
            temp_dir = Path(settings.MEDIA_ROOT) / "temp" / "grading"
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / uploaded_file.name
            cv2.imwrite(str(temp_path), image)
            result["temp_path"] = str(temp_path)

        return result

    @staticmethod
    def save_heatmap(heatmap: np.ndarray, filename: str) -> str:
        """
        Save heatmap image to media storage.

        Args:
            heatmap: RGB heatmap image as numpy array
            filename: Name for the saved file

        Returns:
            str: URL path to the saved heatmap
        """
        if heatmap is None:
            return None

        xai_dir = Path(settings.MEDIA_ROOT) / "xai" / "heatmaps"
        xai_dir.mkdir(parents=True, exist_ok=True)

        # Ensure filename has extension
        if not filename.endswith(('.png', '.jpg', '.jpeg')):
            filename += '.png'

        save_path = xai_dir / filename

        # Convert RGB to BGR for OpenCV
        if len(heatmap.shape) == 3 and heatmap.shape[2] == 3:
            heatmap_bgr = cv2.cvtColor(heatmap, cv2.COLOR_RGB2BGR)
        else:
            heatmap_bgr = heatmap

        cv2.imwrite(str(save_path), heatmap_bgr)

        # Return media URL
        media_url = f"{settings.MEDIA_URL}xai/heatmaps/{filename}"
        return media_url