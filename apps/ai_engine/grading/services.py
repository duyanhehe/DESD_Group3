from apps.ai_engine.grading.inference import predict


class GradingService:
    @staticmethod
    def analyze(image_path: str):
        return predict(image_path)