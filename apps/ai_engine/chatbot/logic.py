from .llm_client import LLMClient
from .prompts import CONCIERGE_SYSTEM_PROMPT

class ChatbotLogic:
    """
    Orchestrates the conversation logic for the Food Network Local Concierge.
    """
    def __init__(self):
        self.client = LLMClient()
        self.system_prompt = CONCIERGE_SYSTEM_PROMPT

    def get_response(self, user_message, recommendation_data=None, user=None):
        """
        Processes a user message with live database context, optional AI-driven recommendations (XAI),
        and user-specific history.
        """
        from apps.products.models import Product
        from apps.ai_engine.recommendation.services import get_user_recommendations, get_trending_products
        from apps.orders.models import Order, OrderItem
        
        # Fetch active products to provide real inventory context
        active_products = Product.objects.active()[:15] # Top 15 current items
        inventory_list = "\n".join([
            f"- {p.name} ({p.category.name if p.category else 'General'}): ${p.price}/{p.unit} from {(p.producer.producer_profile.business_name if hasattr(p.producer, 'producer_profile') else p.producer.username) if p.producer else 'Local Farm'}"
            for p in active_products
        ])

        # Prepare User Context (History & Personalized Recommendations)
        user_context = ""
        if user and user.is_authenticated:
            # Get AI-driven personalized recommendations for this user
            user_recs = get_user_recommendations(user.id, limit=5)
            
            # Fetch actual historical purchase items
            orders = Order.objects.filter(customer_id=user.id).exclude(status="cancelled")
            order_ids = list(orders.values_list('id', flat=True))
            sub_order_ids = list(Order.objects.filter(parent_order_id__in=order_ids).values_list('id', flat=True))
            all_order_ids = order_ids + sub_order_ids
            
            history_items = list(OrderItem.objects.filter(order_id__in=all_order_ids).values_list('product__name', flat=True).distinct())
            
            user_context = "\n\nUSER PROFILE & HISTORY:\n"
            user_context += f"- User: {user.username}\n"
            if history_items:
                user_context += f"- Purchase History: {', '.join(history_items)}\n"
            
            if user_recs.get("recommendations"):
                user_context += f"- AI Personalized Suggestions: {', '.join(user_recs['recommendations'])}\n"
                user_context += f"- Why: {user_recs.get('explanation', 'Matches your taste')}\n"

        # Prepare XAI context if recommendation data is provided from the engine (e.g. from current view)
        xai_context = ""
        if recommendation_data:
            xai_context = "\n\nCURRENT INTERACTION INSIGHTS (XAI Context):\n"
            # Ensure recommendation_data is treated as a list for consistent processing
            recs = recommendation_data if isinstance(recommendation_data, list) else [recommendation_data]
            for rec in recs:
                # Extract the recommendation items and the 'because' reasoning
                items = rec.get('recommendation') or rec.get('item')
                if isinstance(items, list):
                    items = ", ".join(items)
                
                reason = rec.get('because')
                if isinstance(reason, list):
                    reason = ", ".join(reason)
                
                confidence = rec.get('confidence', 0)
                
                # Format a clear reasoning string for the LLM to interpret
                xai_context += f"- Suggest: {items} | Why: Based on interest in {reason} | Confidence: {confidence:.2f}\n"
        
        # Construct the final dynamic prompt combining personality, inventory, user history, and XAI data
        dynamic_prompt = (
            f"{self.system_prompt}\n\n"
            f"CURRENT INVENTORY:\n{inventory_list}\n"
            f"{user_context}"
            f"{xai_context}"
        )

        # Send the prompt to the Ollama client
        result = self.client.generate_response(dynamic_prompt, user_message)
        
        if result["success"]:
            # Apply post-processing to ensure a professional tone
            processed_response = self._humanize_response(result["response"])
            return {
                "success": True,
                "reply": processed_response,
                "model": result["model"]
            }
        
        return result

    def _humanize_response(self, text):
        """
        Ensures the response has a consistent and warm professional tone.
        """
        # Clean white spaces
        text = text.strip()
        
        # Optional: Add hooks here to enforce specific branding or safety guardrails
        
        return text

# Singleton instance for easy access
chatbot_logic = ChatbotLogic()
