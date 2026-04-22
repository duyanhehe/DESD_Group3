import cv2
import numpy as np
import os

def nothing(x):
    pass

def tuner():
    sample_dir = os.path.join("data", "test_images")
    img_files = []
    if os.path.exists(sample_dir):
        img_files = [os.path.join(sample_dir, f) for f in os.listdir(sample_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not img_files:
        print(f"No images found in {sample_dir}. Please place images first!")
        return
        
    img_path = img_files[0]
    print(f"Using source image: {img_path}")
    image = cv2.imread(img_path)
    
    if image is None:
        print("Could not read the image!")
        return

    # Resize to fit screen
    h, w = image.shape[:2]
    max_dim = 800
    if h > max_dim or w > max_dim:
        scale = max_dim / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)))

    # Setup GUI
    cv2.namedWindow('HSV Tuner')
    cv2.createTrackbar('H Min', 'HSV Tuner', 0, 179, nothing)
    cv2.createTrackbar('S Min', 'HSV Tuner', 0, 255, nothing)
    cv2.createTrackbar('V Min', 'HSV Tuner', 0, 255, nothing)
    cv2.createTrackbar('H Max', 'HSV Tuner', 179, 179, nothing)
    cv2.createTrackbar('S Max', 'HSV Tuner', 255, 255, nothing)
    cv2.createTrackbar('V Max', 'HSV Tuner', 255, 255, nothing)
    
    # Defaults (Dark/Brown generic)
    cv2.setTrackbarPos('H Min', 'HSV Tuner', 0)
    cv2.setTrackbarPos('S Min', 'HSV Tuner', 0)
    cv2.setTrackbarPos('V Min', 'HSV Tuner', 0)
    cv2.setTrackbarPos('H Max', 'HSV Tuner', 179)
    cv2.setTrackbarPos('S Max', 'HSV Tuner', 255)
    cv2.setTrackbarPos('V Max', 'HSV Tuner', 90)

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    while True:
        h_min = cv2.getTrackbarPos('H Min', 'HSV Tuner')
        s_min = cv2.getTrackbarPos('S Min', 'HSV Tuner')
        v_min = cv2.getTrackbarPos('V Min', 'HSV Tuner')
        h_max = cv2.getTrackbarPos('H Max', 'HSV Tuner')
        s_max = cv2.getTrackbarPos('S Max', 'HSV Tuner')
        v_max = cv2.getTrackbarPos('V Max', 'HSV Tuner')
        
        lower = np.array([h_min, s_min, v_min])
        upper = np.array([h_max, s_max, v_max])
        
        mask = cv2.inRange(hsv, lower, upper)
        result = cv2.bitwise_and(image, image, mask=mask)
        
        cv2.imshow('HSV Tuner (Result)', result)
        cv2.imshow('Original Image', image)
        cv2.imshow('Binary Mask', mask)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q'): # ESC or 'q'
            break

    cv2.destroyAllWindows()
    print("Final HSV Range Selected:")
    print(f"Lower HSV: [{h_min}, {s_min}, {v_min}]")
    print(f"Upper HSV: [{h_max}, {s_max}, {v_max}]")

if __name__ == "__main__":
    tuner()
