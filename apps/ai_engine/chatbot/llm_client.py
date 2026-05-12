import requests
import json
from django.conf import settings

class LLMClient:
    """
    Standardized client for interacting with the local Ollama LLM.
    """
    def __init__(self):
        self.url = getattr(settings, "OLLAMA_API_URL", "http://localhost:11434/api/generate")

    def generate_response(self, system_prompt, user_message):
        """
        Sends a message to the Ollama API and retrieves the generated response.
        """
        # Protection: Prevent massive input abuse
        user_message = user_message[:500] 

        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\nUser: {user_message}\nAssistant:",
            "stream": False,
            "options": {
                "num_predict": 300,  # Limits response length to ~225 words
                "temperature": 0.7,
                "top_p": 0.9
            }
        }

        try:
            response = requests.post(self.url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            return {
                "success": True,
                "response": data.get("response", ""),
                "model": self.model
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": "AI service offline",
                "details": str(e),
                "response": "I'm currently resting after a long day at the farm. (Local AI Service Offline)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Internal Error",
                "details": str(e),
                "response": "I'm having trouble connecting to my farm records right now."
            }
