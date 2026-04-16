from .llm_client import LLMClient
from .prompts import CONCIERGE_SYSTEM_PROMPT

class ChatbotLogic:
    """
    Orchestrates the conversation logic for the Food Network Local Concierge.
    """
    def __init__(self):
        self.client = LLMClient()
        self.system_prompt = CONCIERGE_SYSTEM_PROMPT

    def get_response(self, user_message):
        """
        Processes a user message through the LLM and applies humanizing formatting.
        """
        # Call the raw LLM client
        result = self.client.generate_response(self.system_prompt, user_message)
        
        if result["success"]:
            # Apply any post-processing / "humanizing" logic here
            # Like adding natural transitions if the LLM output is too robotic
            processed_response = self._humanize_response(result["response"])
            return {
                "response": processed_response,
                "model": result["model"]
            }
        
        return result

    def _humanize_response(self, text):
        """
        Ensures the response has a warm opening if missing and clean formatting.
        """
        # Basic cleaning
        text = text.strip()
        
        # We can add more advanced pattern matching here later 
        # (e.g., ensuring a 'hospitable' tone as per the Hotel project)
        
        return text

# Singleton instance for easy access
chatbot_logic = ChatbotLogic()
