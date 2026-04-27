import pickle
from apps.ai_engine.config import RECOMMENDATION_MODEL_PATH

_model = None


def get_model():
    global _model

    if _model is None:
        try:
            with open(RECOMMENDATION_MODEL_PATH, "rb") as f:
                _model = pickle.load(f)
        except FileNotFoundError:
            print(f"WARNING: Recommendation model not found at {RECOMMENDATION_MODEL_PATH}")
            return None

    return _model
