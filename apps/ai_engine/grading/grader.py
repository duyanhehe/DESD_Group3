import cv2
import numpy as np

from .ripeness_profiles import RIPENESS_PROFILES
from .defect_profiles import DEFECT_PROFILES


class QualityGrader:
    def remove_background(self, cropped_img):
        """Remove background using GrabCut"""
        mask = np.zeros(cropped_img.shape[:2], np.uint8)
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)
        h, w = cropped_img.shape[:2]

        # Dynamic Margin for Elongated objects (Banana, Carrot, Cucumber)
        if w > h * 1.5:
            margin_x = max(2, int(w * 0.02))
            margin_y = max(5, int(h * 0.1))
        elif h > w * 1.5:
            margin_x = max(5, int(w * 0.1))
            margin_y = max(2, int(h * 0.02))
        else:
            margin_x = max(5, int(w * 0.05))
            margin_y = max(5, int(h * 0.05))

        rect = (margin_x, margin_y, w - margin_x * 2, h - margin_y * 2)

        # Ensure rect is valid
        if rect[2] <= 0 or rect[3] <= 0:
            mask.fill(1)
        else:
            try:
                cv2.grabCut(
                    cropped_img,
                    mask,
                    rect,
                    bgdModel,
                    fgdModel,
                    5,
                    cv2.GC_INIT_WITH_RECT,
                )
            except cv2.error:
                mask.fill(1)  # Fallback if GrabCut fails

        fruit_mask = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")

        # Safety Fallback: If GrabCut removes > 90% of the image (Potato case)
        total_pixels = w * h
        fg_pixels = cv2.countNonZero(fruit_mask)

        if fg_pixels < total_pixels * 0.1:
            fruit_mask = np.ones((h, w), np.uint8)  # Cancel GrabCut

        img_no_bg = cropped_img * fruit_mask[:, :, np.newaxis]

        return img_no_bg, fruit_mask

    def calculate_edge_density(self, img_no_bg, fruit_mask):
        """Calculate the density of edges (texture) within the fruit area"""
        gray = cv2.cvtColor(img_no_bg, cv2.COLOR_BGR2GRAY)
        
        # Canny edge detection
        edges = cv2.Canny(gray, 100, 200)

        # Count edges within the fruit mask
        edge_pixels = cv2.countNonZero(cv2.bitwise_and(edges, edges, mask=fruit_mask))
        fruit_pixels = cv2.countNonZero(fruit_mask)

        if fruit_pixels == 0:
            return 0.0

        density = edge_pixels / fruit_pixels
        return round(density, 4)

    def calculate_size_score(self, fruit_mask, profile):
        """
        Calculate Size Score based on Min-Max Scaling (Relative Pixel Area).
        """
        current_area = cv2.countNonZero(fruit_mask)
        size_config = profile.get("size_config", {})
        min_area = size_config.get("min_area", 10000)
        max_area = size_config.get("max_area", 60000)

        if current_area <= min_area:
            return 0.0
        if current_area >= max_area:
            return 100.0

        size_score = ((current_area - min_area) / (max_area - min_area)) * 100
        return round(size_score, 2)

    def calculate_shape_conformity(self, fruit_mask):
        """
        Calculate Shape Conformity based on Solidity.
        Solidity = Area / Convex_Hull_Area
        """
        contours, _ = cv2.findContours(
            fruit_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return 0.0

        main_contour = max(contours, key=cv2.contourArea)
        fruit_area = cv2.contourArea(main_contour)
        hull = cv2.convexHull(main_contour)
        hull_area = cv2.contourArea(hull)

        if hull_area == 0:
            return 0.0

        solidity = (fruit_area / hull_area) * 100
        return round(solidity, 2)

    def analyze_ripeness(self, hsv_img, fruit_mask, profile):
        """Pipeline 1: Analyze ripeness for Healthy fruit"""
        # Ripe color mask
        ripe_mask = cv2.inRange(
            hsv_img, profile["ripe"]["lower"], profile["ripe"]["upper"]
        )

        if "ripe_alt" in profile:
            ripe_alt = cv2.inRange(
                hsv_img, profile["ripe_alt"]["lower"], profile["ripe_alt"]["upper"]
            )
            ripe_mask = cv2.bitwise_or(ripe_mask, ripe_alt)

        # Unripe color mask
        unripe_mask = cv2.inRange(
            hsv_img, profile["unripe"]["lower"], profile["unripe"]["upper"]
        )

        # Only count within the fruit area
        ripe_pixels = cv2.countNonZero(
            cv2.bitwise_and(ripe_mask, ripe_mask, mask=fruit_mask)
        )
        unripe_pixels = cv2.countNonZero(
            cv2.bitwise_and(unripe_mask, unripe_mask, mask=fruit_mask)
        )

        total_eval_pixels = ripe_pixels + unripe_pixels

        if total_eval_pixels == 0:
            return 0  # Undetermined

        ripeness_percentage = (ripe_pixels / total_eval_pixels) * 100
        return round(ripeness_percentage, 2)

    def analyze_defects(self, img_no_bg, hsv_img, fruit_mask, profile, fruit_type):
        """Pipeline 2: Analyze rot for Defective fruit"""
        # Pre-processing per Group
        SPHERICAL = ["Apple", "Tomato", "Orange", "Guava", "Pomegranate", "Jujube"]

        if fruit_type in SPHERICAL:
            # Safe Zone Erosion (Remove edge shadows)
            kernel = np.ones((7, 7), np.uint8)
            fruit_mask = cv2.erode(fruit_mask, kernel, iterations=1)

        if fruit_type == "Bellpepper":
            # Patch holes in Bellpepper mask
            kernel = np.ones((15, 15), np.uint8)
            fruit_mask = cv2.morphologyEx(fruit_mask, cv2.MORPH_CLOSE, kernel)

        if fruit_type == "Cucumber":
            # Smooth cucumber stripes
            hsv_img = cv2.GaussianBlur(hsv_img, (9, 9), 0)

        total_fruit_area = cv2.countNonZero(fruit_mask)

        if total_fruit_area == 0:
            return 0, img_no_bg, fruit_mask

        # Integrate both rot and mold masks
        rot_mask = cv2.inRange(
            hsv_img, profile["rot"]["lower"], profile["rot"]["upper"]
        )

        mold_mask = cv2.inRange(
            hsv_img, profile["mold"]["lower"], profile["mold"]["upper"]
        )

        if fruit_type in SPHERICAL:
            # Remove Specular Highlights (Flash/Glare) from mold
            # "False White Area" Protection
            s_limit = profile.get("specular_saturation_limit", 20)
            v_limit = profile.get("specular_value_limit", 240)
            _, s, v = cv2.split(hsv_img)
            
            highlight_mask = cv2.bitwise_and(
                cv2.inRange(v, v_limit, 255), cv2.inRange(s, 0, s_limit)
            )

            # Dilate the glare shield to swallow fuzzy boundaries
            kernel_dilate = np.ones((5, 5), np.uint8)
            highlight_mask = cv2.dilate(highlight_mask, kernel_dilate, iterations=1)
            mold_mask = cv2.bitwise_and(mold_mask, cv2.bitwise_not(highlight_mask))

        defect_mask = cv2.bitwise_or(rot_mask, mold_mask)

        # Apply ignore_zone (Calyx/Roots)
        if "ignore_zone" in profile:
            ignore_mask = cv2.inRange(
                hsv_img,
                profile["ignore_zone"]["lower"],
                profile["ignore_zone"]["upper"],
            )
            defect_mask = cv2.bitwise_and(defect_mask, cv2.bitwise_not(ignore_mask))

        # Confine to the fruit shape and remove noise
        defect_mask = cv2.bitwise_and(defect_mask, defect_mask, mask=fruit_mask)

        kernel_open = np.ones((5, 5), np.uint8)
        kernel_close = np.ones((11, 11), np.uint8)
        defect_mask = cv2.morphologyEx(defect_mask, cv2.MORPH_OPEN, kernel_open)
        defect_mask = cv2.morphologyEx(defect_mask, cv2.MORPH_CLOSE, kernel_close)

        # Fill holes within the defect contour
        # Find contours of the defect areas
        contours, _ = cv2.findContours(
            defect_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Create a new mask to fill the solid contours
        filled_defect_mask = np.zeros_like(defect_mask)

        # --- SHAPE FILTERING TO REJECT SHADOWS ---
        valid_contours = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Area Filter for Potato Eyes
            min_area = 150 if fruit_type == "Potato" else 20

            if area < min_area:  # Ignore tiny noise / potato eyes
                continue

            # Use Bounding Box aspect ratio to detect long thin shadows
            x, y, w, h = cv2.boundingRect(cnt)

            # Prevent division by zero
            if min(w, h) == 0:
                continue

            aspect_ratio = max(w, h) / min(w, h)

            # If the contour is extremely elongated (aspect ratio > 4.5), it's likely a shadow
            if aspect_ratio > 4.5:
                continue

            # --- CONVEX HULL TO FIX FRAGMENTATION (GUAVA) ---
            if fruit_type == "Guava":
                hull = cv2.convexHull(cnt)
                valid_contours.append(hull)
            else:
                valid_contours.append(cnt)

        # Draw and fill the valid contours on the new mask (-1 means fill the contour)
        cv2.drawContours(
            filled_defect_mask, valid_contours, -1, 255, thickness=cv2.FILLED
        )

        # Ensure the filled mask still stays strictly within the fruit boundary
        defect_mask = cv2.bitwise_and(
            filled_defect_mask, filled_defect_mask, mask=fruit_mask
        )

        # Calculate the final rot area based on the filled mask
        total_rot_area = cv2.countNonZero(defect_mask)
        defect_percentage = (total_rot_area / total_fruit_area) * 100

        # Get total rot threshold from Profile, default to 85.0 if not set.
        max_tolerance = profile.get("total_rot_threshold", 85.0)

        # Total rot logic based on specific fruit threshold.
        if defect_percentage >= max_tolerance:
            defect_percentage = 100.0

        # Draw XAI boundaries on the final image
        # Refind contours on the filled mask just to draw nice clean outlines
        final_contours, _ = cv2.findContours(
            defect_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        highlighted_img = img_no_bg.copy()
        cv2.drawContours(highlighted_img, final_contours, -1, (0, 0, 255), 2)

        return round(defect_percentage, 2), highlighted_img, defect_mask

    def process_fruit(self, cropped_img, yolo_class_name):
        """
        Main Pipeline Function: Branches based on YOLO results
        Example yolo_class_name: "Apple_Healthy", "Banana_Rotten"
        """

        # 1. Extract information from YOLO label
        # Normalize class name (handle double underscores from YOLO)
        safe_class_name = yolo_class_name.replace("__", "_")
        parts = safe_class_name.split("_")

        fruit_type = parts[0]  # e.g. "Apple"
        condition = parts[1] if len(parts) > 1 else "Unknown"  # "Healthy" or "Rotten"

        # 2. Check Image Size Minimum Threshold
        h, w = cropped_img.shape[:2]

        if h < 30 or w < 30:
            return (
                "Unanalyzable",
                0.0,
                "Too Small",
                "Object is too small to analyze accurately.",
            )

        ripeness_profile = RIPENESS_PROFILES.get(fruit_type)
        defect_profile = DEFECT_PROFILES.get(fruit_type)

        if not ripeness_profile or not defect_profile:
            return "Unknown", 0, cropped_img, "Class profile not found!"

        # 2. Remove background using GrabCut
        img_no_bg, fruit_mask = self.remove_background(cropped_img)

        # Apply CLAHE to handle lighting and shadow issues
        lab = cv2.cvtColor(img_no_bg, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)
        limg = cv2.merge((cl, a, b))
        img_clahe = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        hsv_img = cv2.cvtColor(img_clahe, cv2.COLOR_BGR2HSV)
        
        full_profile = {**ripeness_profile, **defect_profile}

        # CALCULATE ALL METRICS
        size_score = self.calculate_size_score(fruit_mask, full_profile)
        shape_score = self.calculate_shape_conformity(fruit_mask)
        ripeness_pct = self.analyze_ripeness(hsv_img, fruit_mask, ripeness_profile)
        defect_pct, highlighted_img, _ = self.analyze_defects(
            img_no_bg, hsv_img, fruit_mask, defect_profile, fruit_type
        )
        edge_density = self.calculate_edge_density(img_no_bg, fruit_mask)
        density_threshold = full_profile.get("edge_density_threshold", 0.15)

        grade = "Unknown"
        explain_log = []
        final_image = img_no_bg  # Default to clean image first

        if condition == "Healthy":
            # BRANCH 1: HEALTHY FRUIT -> GRADE BASED ON SCORING (NO GRADE D)
            if ripeness_pct >= 80 and shape_score >= 90:
                if size_score >= 80:
                    grade = "Grade A"
                    explain_log.append("Premium Quality: Excellent size, shape, and ripeness.")
                else:
                    grade = "Grade A-"
                    explain_log.append("Premium Quality but smaller size.")
            elif ripeness_pct >= 60 and shape_score >= 80:
                if size_score >= 60:
                    grade = "Grade B"
                    explain_log.append("Standard Quality: Acceptable parameters.")
                else:
                    grade = "Grade B-"
                    explain_log.append("Standard Quality but smaller size.")
            else:
                # Combined C and old D logic into Grade C and C-
                if size_score >= 40:
                    grade = "Grade C"
                    explain_log.append("Sub-standard Quality: Low ripeness or irregular shape.")
                else:
                    grade = "Grade C-"
                    explain_log.append("Sub-standard Quality: Low quality and very small size.")

            # If CV algorithm detects "phantom" defects (shadows, glare)
            # -> Log internal warning, DO NOT downgrade to F, DO NOT use highlighted_img
            if defect_pct > 5.0 or edge_density >= density_threshold:
                explain_log.append(
                    f"System Note: CV algorithm flagged {defect_pct}% area as potential anomaly (likely shadows/glare), but trusting YOLO 'Healthy' classification."
                )

            # final_image remains img_no_bg (clean image without red outlines)

        else:
            # BRANCH 2: YOLO DETECTED ROTTEN -> FINAL VERDICT & EXPORT EVIDENCE IMAGE
            grade = "Grade F (Rotten/Defective)"
            explain_log.append(
                f"Discarded: YOLO classified as Rotten. CV analysis verified defect area."
            )
            final_image = (
                highlighted_img  # Use image with red outlines for XAI (explanation)
            )

        # PACKAGE XAI REPORT
        xai_report = {
            "metadata": {"fruit_type": fruit_type, "yolo_prediction": condition},
            "metrics": {
                "size_score": size_score,
                "shape_solidity": shape_score,
                "ripeness_pct": ripeness_pct,
                "cv_defect_estimation": defect_pct,  # Keep this parameter for admin reference
                "texture_density": edge_density,
            },
            "decision": {"grade": grade, "reasons": explain_log},
        }

        return xai_report, final_image