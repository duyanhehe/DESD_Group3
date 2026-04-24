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
        Processes a user message with live database context.
        """
        from apps.products.models import Product
        
        # Fetch active products to provide real context
        active_products = Product.objects.active()[:15] # Top 15 current items
        inventory_list = "\n".join([
            f"- {p.name} ({p.category.name if p.category else 'General'}): ${p.price}/{p.unit} from {(p.producer.producer_profile.business_name if hasattr(p.producer, 'producer_profile') else p.producer.username) if p.producer else 'Local Farm'}"
            for p in active_products
        ])
        
        dynamic_prompt = self.system_prompt + f"\n\nCURRENT INVENTORY (ONLY RECOMMEND THESE):\n{inventory_list}"

        # Call the raw LLM client with dynamic context
        result = self.client.generate_response(dynamic_prompt, user_message)
        
        if result["success"]:
            # Apply any post-processing / "humanizing" logic here
            # Like adding natural transitions if the LLM output is too robotic
            processed_response = self._humanize_response(result["response"])
            return {
                "success": True,
                "reply": processed_response,
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
