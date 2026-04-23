"""
Explainable AI Module (Grad-CAM/EigenCAM)
Provides heatmap visualization and XAI metadata for YOLO predictions.
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


class HeatmapExplainer:
    """
    XAI Explainer using EigenCAM for YOLO object detection models.
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

    def generate_heatmap(self, image: np.ndarray, target_layer_idx: int = -2) -> np.ndarray:
        """
        Generate EigenCAM heatmap for the input image.

        Args:
            image: BGR image (OpenCV format) or RGB image as numpy array
            target_layer_idx: Target layer index for CAM (default: -2, usually C2fCIB block)

        Returns:
            np.ndarray: Heatmap overlay image in RGB format, or None if generation fails
        """
        if not GRADCAM_AVAILABLE:
            print("[XAI WARNING] pytorch-grad-cam not installed. Heatmap generation skipped.")
            return None

        try:
            # Ensure image is RGB format
            if image.shape[2] == 3 and len(image.shape) == 3:
                if image.dtype == np.uint8:
                    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image[0, 0, 0] > image[0, 0, 2] else image
                else:
                    img_rgb = image
            else:
                return None

            # Wrap the model for grad-cam compatibility
            wrapped_model = YoloModelWrapper(self.model.model)
            wrapped_model.eval()

            # Define target layers (typically the last convolutional blocks)
            target_layers = [self.model.model.model[target_layer_idx]]

            # Preprocess image for YOLO (640x640)
            img_resized = cv2.resize(img_rgb, (640, 640))
            input_tensor = torch.from_numpy(img_resized).permute(2, 0, 1).unsqueeze(0).float() / 255.0
            input_tensor = input_tensor.to(self.device)

            # Initialize EigenCAM
            cam = EigenCAM(model=wrapped_model, target_layers=target_layers)

            # Generate grayscale CAM
            grayscale_cam = cam(input_tensor=input_tensor)[0, :]

            # Resize CAM back to original image size
            cam_resized = cv2.resize(grayscale_cam, (img_rgb.shape[1], img_rgb.shape[0]))

            # Overlay on original image
            rgb_norm = img_rgb / 255.0
            cam_image = show_cam_on_image(rgb_norm, cam_resized, use_rgb=True)

            return cam_image

        except Exception as e:
            print(f"[XAI WARNING] Heatmap generation failed: {e}")
            return None

    def explain_prediction(self, image: np.ndarray, results) -> dict:
        """
        Full XAI explanation including detection metadata and optional heatmap.

        Args:
            image: Input image (BGR format from OpenCV)
            results: YOLO prediction results

        Returns:
            dict: XAI report with detection info and heatmap if applicable
        """
        # Get detection metadata
        detections = self.get_detection_metadata(results)

        # Determine if heatmap is needed (rotten/defective fruit)
        heatmap = None
        is_defective = False

        for det in detections:
            class_name = det.get("class", "")
            if "Rotten" in class_name or "Disease" in class_name or "Defect" in class_name:
                is_defective = True
                break

        # Generate heatmap for defective fruit
        if is_defective:
            heatmap = self.generate_heatmap(image)

        return {
            "detections": detections,
            "heatmap": heatmap,
            "is_defective": is_defective,
            "model_device": str(self.device)
        }
