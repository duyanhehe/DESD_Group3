import numpy as np

"""
AGRICULTURAL RIPENESS PROFILES DICTIONARY
Contains color ranges for fresh fruit (ripe/unripe).
"""

RIPENESS_PROFILES = {
    "Apple": {
        "ripe": {"lower": np.array([0, 50, 50]), "upper": np.array([10, 255, 255])},
        "ripe_alt": {"lower": np.array([160, 50, 50]), "upper": np.array([179, 255, 255])}, 
        "unripe": {"lower": np.array([35, 50, 50]), "upper": np.array([85, 255, 255])},
        "size_config": {"min_area": 25000, "max_area": 70000}
    },
    "Banana": {
        "ripe": {"lower": np.array([20, 100, 100]), "upper": np.array([35, 255, 255])}, 
        "unripe": {"lower": np.array([35, 50, 50]), "upper": np.array([85, 255, 255])},
        "size_config": {"min_area": 30000, "max_area": 90000}
    },
    "Bellpepper": {
        "ripe": {"lower": np.array([0, 100, 50]), "upper": np.array([30, 255, 255])},   
        "ripe_alt": {"lower": np.array([160, 100, 50]), "upper": np.array([179, 255, 255])},
        "unripe": {"lower": np.array([35, 50, 50]), "upper": np.array([85, 255, 255])},
        "size_config": {"min_area": 20000, "max_area": 60000}
    },
    "Carrot": {
        "ripe": {"lower": np.array([10, 100, 100]), "upper": np.array([25, 255, 255])}, 
        "unripe": {"lower": np.array([35, 50, 50]), "upper": np.array([85, 255, 255])},
        "size_config": {"min_area": 15000, "max_area": 50000}
    },
    "Cucumber": {
        "ripe": {"lower": np.array([35, 100, 50]), "upper": np.array([85, 255, 255])},  
        "unripe": {"lower": np.array([35, 20, 50]), "upper": np.array([85, 99, 255])},
        "size_config": {"min_area": 20000, "max_area": 70000}
    },
    "Grape": {
        "ripe": {"lower": np.array([130, 50, 50]), "upper": np.array([170, 255, 255])}, 
        "ripe_alt": {"lower": np.array([0, 50, 50]), "upper": np.array([10, 255, 255])},
        "unripe": {"lower": np.array([35, 50, 50]), "upper": np.array([85, 255, 255])},
        "size_config": {"min_area": 5000, "max_area": 20000}
    },
    "Guava": {
        "ripe": {"lower": np.array([25, 50, 100]), "upper": np.array([45, 255, 255])},  
        "unripe": {"lower": np.array([40, 50, 20]), "upper": np.array([85, 255, 150])},
        "size_config": {"min_area": 30000, "max_area": 80000}
    },
    "Jujube": {
        "ripe": {"lower": np.array([5, 50, 50]), "upper": np.array([20, 255, 255])},    
        "unripe": {"lower": np.array([35, 50, 50]), "upper": np.array([85, 255, 255])},
        "size_config": {"min_area": 20000, "max_area": 50000}
    },
    "Mango": {
        "ripe": {"lower": np.array([15, 100, 100]), "upper": np.array([35, 255, 255])}, 
        "unripe": {"lower": np.array([35, 50, 50]), "upper": np.array([85, 255, 255])},
        "size_config": {"min_area": 30000, "max_area": 90000}
    },
    "Orange": {
        "ripe": {"lower": np.array([10, 100, 100]), "upper": np.array([25, 255, 255])}, 
        "unripe": {"lower": np.array([35, 50, 50]), "upper": np.array([85, 255, 255])},
        "size_config": {"min_area": 35000, "max_area": 90000}
    },
    "Pomegranate": {
        "ripe": {"lower": np.array([0, 100, 50]), "upper": np.array([10, 255, 255])},   
        "ripe_alt": {"lower": np.array([160, 100, 50]), "upper": np.array([179, 255, 255])}, 
        "unripe": {"lower": np.array([20, 20, 50]), "upper": np.array([85, 150, 255])},
        "size_config": {"min_area": 20000, "max_area": 60000}
    },
    "Potato": {
        "ripe": {"lower": np.array([10, 40, 100]), "upper": np.array([30, 255, 255])},  
        "unripe": {"lower": np.array([35, 50, 50]), "upper": np.array([85, 255, 255])},
        "size_config": {"min_area": 20000, "max_area": 70000}
    },
    "Strawberry": {
        "ripe": {"lower": np.array([0, 150, 100]), "upper": np.array([10, 255, 255])},  
        "ripe_alt": {"lower": np.array([160, 150, 100]), "upper": np.array([179, 255, 255])},
        "unripe": {"lower": np.array([20, 0, 100]), "upper": np.array([34, 100, 255])},
        "size_config": {"min_area": 8000, "max_area": 25000}
    },
    "Tomato": {
        "ripe": {"lower": np.array([0, 100, 100]), "upper": np.array([10, 255, 255])},  
        "ripe_alt": {"lower": np.array([160, 100, 100]), "upper": np.array([179, 255, 255])},
        "unripe": {"lower": np.array([35, 50, 50]), "upper": np.array([90, 255, 255])},
        "size_config": {"min_area": 20000, "max_area": 70000}
    }
}
