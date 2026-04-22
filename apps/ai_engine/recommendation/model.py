import pickle
from apps.ai_engine.config import RECOMMENDATION_MODEL_PATH

_model = None


def get_model():
    global _model

    if _model is None:
        with open(RECOMMENDATION_MODEL_PATH, "rb") as f:
            _model = pickle.load(f)

    return _model
