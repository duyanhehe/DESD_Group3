"""
Explainable AI Module (EigenCAM)
Provides heatmap visualization and XAI metadata for YOLO predictions.

This module mirrors the proven approach from notebook 03_yolov10_xai_visualization.ipynb:
- Uses YoloModelWrapper for pytorch-grad-cam compatibility
- Generates EigenCAM heatmaps on 640x640 resized images
- Overlays heatmap on the resized image (matching notebook behavior)
"""

import cv2
import numpy as np
import torch
from pathlib import Path

try:
    from pytorch_grad_cam import EigenCAM
    from pytorch_grad_cam.utils.image import show_cam_on_image
    GRADCAM_AVAILABLE = True
except ImportError:
    GRADCAM_AVAILABLE = False


class YoloModelWrapper(torch.nn.Module):
    """
    Wrapper to make YOLOv10 compatible with pytorch-grad-cam.
    Ensures the forward pass returns a tensor instead of a tuple.

    This is identical to the wrapper used in notebook 03.
    """
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, x):
        # YOLOv10 forward pass returns a tuple/list
        # We return only the first element (the predictions tensor)
        results = self.model(x)
        if isinstance(results, (list, tuple)):
            return results[0]
        return results


def get_yolo_xai_data(results):
    """
    [METHOD 1] Inherent Explainability: Extract detection metadata from YOLO results.
    Extracts boxes, confidence and labels — directly from notebook 03.

    Args:
        results: YOLO prediction results

    Returns:
        list: List of detection metadata dicts with class, confidence, bbox
    """
    xai_data = []
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            confidence = round(box.conf[0].item() * 100, 2)
            class_id = int(box.cls[0].item())
            class_name = r.names[class_id]

            xai_data.append({
                "class": class_name,
                "confidence": f"{confidence}%",
                "bbox": [int(x1), int(y1), int(x2), int(y2)]
            })
    return xai_data


def generate_yolo_heatmap(model, img_rgb, target_layer_idx=-2):
    """
    [METHOD 2] Heatmap Visualization using EigenCAM.
    Uses YoloModelWrapper for compatibility.

    This function is directly ported from notebook 03_yolov10_xai_visualization.ipynb
    to ensure identical heatmap quality.

    Args:
        model: YOLO model instance (from ultralytics)
        img_rgb: RGB image as numpy array (uint8, HxWx3)
        target_layer_idx: Target layer index for CAM (default: -2, C2fCIB block before head)

    Returns:
        np.ndarray: Heatmap overlay image in RGB format, or None if generation fails
    """
    if not GRADCAM_AVAILABLE:
        print("[XAI WARNING] pytorch-grad-cam not installed. Heatmap generation skipped.")
        return None

    try:
        # 1. Wrap the model for grad-cam compatibility
        wrapped_model = YoloModelWrapper(model.model)
        wrapped_model.eval()

        # 2. Define Target Layer (C2fCIB block before head)
        target_layers = [model.model.model[target_layer_idx]]

        # 3. Device Detection
        device = next(model.model.parameters()).device

        # 4. Preprocess image — resize to 640x640 as expected by YOLO
        img_resized = cv2.resize(img_rgb, (640, 640))
        input_tensor = torch.from_numpy(img_resized).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        input_tensor = input_tensor.to(device)

        # 5. Initialize EigenCAM with Wrapped Model
        cam = EigenCAM(model=wrapped_model, target_layers=target_layers)

        # 6. Generate grayscale cam
        grayscale_cam = cam(input_tensor=input_tensor)[0, :]

        # 7. Overlay on the RESIZED image (key difference vs old code)
        #    The notebook overlays on img_resized/255.0, NOT on the original image.
        #    This ensures the heatmap aligns perfectly with what the model actually sees.
        rgb_norm = img_resized / 255.0
        cam_image = show_cam_on_image(rgb_norm, grayscale_cam, use_rgb=True)

        return cam_image

    except Exception as e:
        print(f"[XAI WARNING] Heatmap generation failed: {e}")
        return None


class HeatmapExplainer:
    """
    XAI Explainer using EigenCAM for YOLO object detection models.
    Wraps the standalone functions for use in the Django API pipeline.
    """

    def __init__(self, model):
        """
        Initialize explainer with YOLO model.
        Args:
            model: YOLO model instance from ultralytics
        """
        self.model = model
        self.device = next(model.model.parameters()).device if hasattr(model, 'model') else torch.device('cpu')

    def get_detection_metadata(self, results):
        """
        Extract XAI metadata from YOLO detection results.
        Delegates to the standalone function matching notebook 03.
        """
        return get_yolo_xai_data(results)

    def generate_heatmap(self, image_bgr: np.ndarray, target_layer_idx: int = -2) -> np.ndarray:
        """
        Generate EigenCAM heatmap for the input image.
        Mirrors the exact logic from notebook 03.

        Args:
            image_bgr: BGR image (OpenCV format) as numpy array
            target_layer_idx: Target layer index for CAM (default: -2)

        Returns:
            np.ndarray: Heatmap overlay image in RGB format, or None if generation fails
        """
        # Convert BGR to RGB (notebook 03 works with RGB throughout)
        img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        return generate_yolo_heatmap(self.model, img_rgb, target_layer_idx)

    def explain_prediction(self, image_bgr: np.ndarray, results) -> dict:
        """
        Full XAI explanation including detection metadata and optional heatmap.
        Only generates heatmap for Rotten/Defective fruit (matching notebook 03 behavior).

        Args:
            image_bgr: Input image (BGR format from OpenCV)
            results: YOLO prediction results

        Returns:
            dict: XAI report with detection info and heatmap if applicable
        """
        # Get detection metadata
        detections = self.get_detection_metadata(results)

        # Determine if heatmap is needed (only for rotten/defective fruit)
        heatmap = None
        is_defective = False

        for det in detections:
            class_name = det.get("class", "")
            # Check condition — notebook 03 uses class_name.split('_')[1] == 'Rotten'
            if "Rotten" in class_name or "Disease" in class_name or "Defect" in class_name:
                is_defective = True
                break

        # Generate heatmap only for defective fruit
        if is_defective:
            heatmap = self.generate_heatmap(image_bgr)

        return {
            "detections": detections,
            "heatmap": heatmap,
            "is_defective": is_defective,
            "model_device": str(self.device)
        }
