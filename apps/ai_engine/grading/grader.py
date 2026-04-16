import cv2
import numpy as np

class QualityGrader:
    def remove_background(self, cropped_img):
        """
        Apply GrabCut algorithm to remove the background, keeping only the fruit pixels.
        
        Returns:
            img_no_bg: Image with black background after removal.
            fruit_mask: Binary mask of the fruit (1 for fruit, 0 for bg).
        """
        mask = np.zeros(cropped_img.shape[:2], np.uint8)
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)
        
        h, w = cropped_img.shape[:2]
        
        # Assume the fruit is mainly in the center, leave a 5-10% padding margin
        margin = max(5, int(min(w, h) * 0.05))
        rect = (margin, margin, w - margin*2, h - margin*2)
        
        try:
            cv2.grabCut(cropped_img, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
        except cv2.error:
            # If the bbox is too small or grabcut fails, fallback to full mask
            mask.fill(1)
            
        # Extract foreground mask (pixels marked as 1 and 3)
        fruit_mask = np.where((mask==2)|(mask==0), 0, 1).astype('uint8')
        
        # Apply mask to image
        img_no_bg = cropped_img * fruit_mask[:, :, np.newaxis]
        
        return img_no_bg, fruit_mask

    def find_defects(self, img_no_bg, fruit_mask, lower_hsv, upper_hsv):
        """
        Find defective regions using HSV thresholds and calculate areas.
        Now returns intermediary masks to help explain the AI's decision.
        
        Returns:
           total_fruit_area: int
           total_rot_area: int
           highlighted_img: Original image with drawn red contours
           rot_mask_raw: The pure HSV boolean mask
           rot_mask_clean: The morphological cleaned mask
           extracted_rot: The isolated rotting parts (cropped bits)
        """
        # Calculate total useful pixels
        total_fruit_area = cv2.countNonZero(fruit_mask)
        if total_fruit_area == 0:
            blank_mask = np.zeros(fruit_mask.shape, dtype=np.uint8)
            return 0, 0, img_no_bg.copy(), blank_mask, blank_mask, img_no_bg.copy()
            
        hsv_img = cv2.cvtColor(img_no_bg, cv2.COLOR_BGR2HSV)
        
        # Raw color thresholding
        rot_mask_raw = cv2.inRange(hsv_img, lower_hsv, upper_hsv)
        
        # Ensure defects are strictly inside the fruit area (mitigate grabcut noise)
        rot_mask_raw = cv2.bitwise_and(rot_mask_raw, rot_mask_raw, mask=fruit_mask)
        
        # Morphological noise reduction (remove pepper noise, fill holes)
        kernel = np.ones((5,5), np.uint8)
        rot_mask_clean = cv2.morphologyEx(rot_mask_raw, cv2.MORPH_OPEN, kernel)
        rot_mask_clean = cv2.morphologyEx(rot_mask_clean, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(rot_mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        total_rot_area = sum(cv2.contourArea(c) for c in contours)
        
        # Draw on image
        highlighted_img = img_no_bg.copy()
        cv2.drawContours(highlighted_img, contours, -1, (0, 0, 255), 2)
        
        # Extract purely the rotting pixels for visualization
        extracted_rot = cv2.bitwise_and(img_no_bg, img_no_bg, mask=rot_mask_clean)
        
        return total_fruit_area, total_rot_area, highlighted_img, rot_mask_raw, rot_mask_clean, extracted_rot
        
    def calculate_grade(self, rot_ratio):
        """
        Grade the fruit based on defect percentage.
        A: < 2% defect
        B: 2% - 15% defect
        C: > 15% defect
        """
        percent = rot_ratio * 100
        if percent < 2.0:
            return "Class A (Premium)", percent
        elif percent <= 15.0:
            return "Class B (Standard)", percent
        else:
            return "Class C (Rejected)", percent
