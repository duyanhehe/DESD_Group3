import numpy as np

"""
AGRICULTURAL DEFECT PROFILES DICTIONARY
Contains data on rot, mold, ignore zones, and threshold limits.
"""

DEFECT_PROFILES = {
"Apple": {
        "rot": {"lower": np.array([12, 40, 20]), "upper": np.array([30, 255, 220])},     
        "mold": {"lower": np.array([0, 0, 180]), "upper": np.array([179, 50, 255])},
        "black_rot": {"lower": np.array([0, 0, 0]), "upper": np.array([179, 255, 25])}, 
        "ignore_zone": {"lower": np.array([0, 20, 0]), "upper": np.array([30, 255, 50])},
        "total_rot_threshold": 70.0,
        "specular_saturation_limit": 25,
        "specular_value_limit": 235,
        "edge_density_threshold": 0.08
    },
    "Banana": {
        "rot": {"lower": np.array([0, 0, 0]), "upper": np.array([179, 255, 80])},       
        "mold": {"lower": np.array([0, 0, 180]), "upper": np.array([179, 50, 255])},
        "total_rot_threshold": 90.0,
        "edge_density_threshold": 0.12
    },
    "Bellpepper": {
        "rot": {"lower": np.array([0, 0, 0]), "upper": np.array([179, 255, 80])},       
        "mold": {"lower": np.array([0, 0, 150]), "upper": np.array([179, 60, 255])},
        "total_rot_threshold": 70.0,
        "edge_density_threshold": 0.10
    },
    "Carrot": {
        "rot": {"lower": np.array([0, 0, 0]), "upper": np.array([20, 255, 80])},        
        "mold": {"lower": np.array([0, 0, 180]), "upper": np.array([179, 50, 255])},     
        "ignore_zone": {"lower": np.array([35, 50, 20]), "upper": np.array([85, 255, 150])},
        "total_rot_threshold": 80.0,
        "edge_density_threshold": 0.15
    },
    "Cucumber": {
        "rot": {"lower": np.array([20, 50, 50]), "upper": np.array([34, 255, 255])},    
        "mold": {"lower": np.array([0, 0, 0]), "upper": np.array([179, 255, 80])},
        "total_rot_threshold": 70.0,
        "edge_density_threshold": 0.12
    },
    "Grape": {
        "rot": {"lower": np.array([10, 40, 20]), "upper": np.array([25, 255, 100])},    
        "mold": {"lower": np.array([0, 0, 100]), "upper": np.array([179, 50, 200])},
        "total_rot_threshold": 60.0,
        "edge_density_threshold": 0.15
    },
    "Guava": {
        "rot": {"lower": np.array([0, 0, 0]), "upper": np.array([179, 255, 60])},       
        "mold": {"lower": np.array([10, 50, 20]), "upper": np.array([25, 255, 120])},
        "total_rot_threshold": 70.0,
        "edge_density_threshold": 0.08
    },
    "Jujube": {
        "rot": {"lower": np.array([0, 0, 0]), "upper": np.array([179, 255, 50])},       
        "mold": {"lower": np.array([0, 0, 180]), "upper": np.array([179, 50, 255])},
        "total_rot_threshold": 70.0,
        "edge_density_threshold": 0.08
    },
    "Mango": {
        "rot": {"lower": np.array([0, 0, 0]), "upper": np.array([179, 255, 80])},       
        "mold": {"lower": np.array([0, 0, 100]), "upper": np.array([179, 50, 180])},
        "total_rot_threshold": 80.0,
        "edge_density_threshold": 0.10
    },
    "Orange": {
        "rot": {"lower": np.array([5, 50, 20]), "upper": np.array([20, 255, 100])},     
        "mold": {"lower": np.array([30, 10, 80]), "upper": np.array([120, 150, 255])},   
        "total_rot_threshold": 70.0,
        "specular_saturation_limit": 30,
        "specular_value_limit": 230,
        "edge_density_threshold": 0.15
    },
    "Pomegranate": {
        "rot": {"lower": np.array([5, 40, 20]), "upper": np.array([20, 255, 80])},      
        "mold": {"lower": np.array([0, 0, 180]), "upper": np.array([179, 50, 255])},
        "total_rot_threshold": 70.0,
        "edge_density_threshold": 0.10
    },
    "Potato": {
        "rot": {"lower": np.array([0, 0, 0]), "upper": np.array([179, 255, 60])},       
        "mold": {"lower": np.array([0, 0, 180]), "upper": np.array([179, 40, 255])},
        "total_rot_threshold": 60.0,
        "edge_density_threshold": 0.12
    },
    "Strawberry": {
        "rot": {"lower": np.array([0, 50, 0]), "upper": np.array([179, 255, 80])},      
        "mold": {"lower": np.array([0, 0, 100]), "upper": np.array([179, 50, 200])},     
        "ignore_zone": {"lower": np.array([35, 40, 20]), "upper": np.array([85, 255, 150])},
        "total_rot_threshold": 50.0,
        "edge_density_threshold": 0.10
    },
    "Tomato": {
        "rot": {"lower": np.array([0, 0, 0]), "upper": np.array([30, 255, 80])},        
        "mold": {"lower": np.array([0, 0, 80]), "upper": np.array([179, 60, 255])},     
        "ignore_zone": {"lower": np.array([35, 50, 20]), "upper": np.array([85, 255, 120])},
        "total_rot_threshold": 60.0,
        "specular_saturation_limit": 30,
        "specular_value_limit": 230,
        "edge_density_threshold": 0.08
    }
}
