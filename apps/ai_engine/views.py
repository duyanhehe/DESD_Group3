from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
import requests
import json

# Recommendation services
from .recommendation.services import (
    get_recommendations,
    get_product_recommendations,
    get_cart_recommendations,
    get_order_recommendations,
    get_trending_products,
    get_user_recommendations,
    resolve_product_names_to_objects,
)
from apps.products.models import Product
from apps.products.serializers import ProductSerializer
from .chatbot import chatbot_logic


class RecommendationView(APIView):
    """
    POST /ai/recommend/
    General purpose recommendation endpoint.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        items = request.data.get("items", [])

        if not items:
            return Response(
                {"error": "Items list is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = get_recommendations(items)
            # Resolve product names to full product objects
            if result["recommendations"]:
                products = resolve_product_names_to_objects(result["recommendations"])
                result["products"] = ProductSerializer(products, many=True).data
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HomepageRecommendationsView(APIView):
    """
    GET /ai/recommendations/homepage/
    Returns trending products and personalized recommendations for logged-in users.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            # Always get trending products
            trending_names = get_trending_products(limit=10)
            trending_products = resolve_product_names_to_objects(trending_names)

            response_data = {
                "trending": ProductSerializer(trending_products, many=True).data,
            }

            # If user is authenticated, add personalized recommendations
            if request.user.is_authenticated:
                personal = get_user_recommendations(request.user.id, limit=10)
                if personal["recommendations"]:
                    personal_products = resolve_product_names_to_objects(
                        personal["recommendations"]
                    )
                    response_data["personalized"] = ProductSerializer(
                        personal_products, many=True
                    ).data
                    response_data["personalized_explanation"] = personal["explanation"]

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductRecommendationsView(APIView):
    """
    GET /ai/recommendations/product/<product_id>/
    Returns 'Frequently Bought Together' for a specific product.
    """
    permission_classes = [AllowAny]

    def get(self, request, product_id):
        try:
            product = get_object_or_404(Product, id=product_id)
            result = get_product_recommendations(product.name)

            if result["recommendations"]:
                products = resolve_product_names_to_objects(result["recommendations"])
                result["products"] = ProductSerializer(products, many=True).data

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CartRecommendationsView(APIView):
    """
    POST /ai/recommendations/cart/
    Returns recommendations based on current cart items.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        cart_items = request.data.get("items", [])

        if not cart_items:
            return Response(
                {"error": "Cart items are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = get_cart_recommendations(cart_items)

            if result["recommendations"]:
                products = resolve_product_names_to_objects(result["recommendations"])
                result["products"] = ProductSerializer(products, many=True).data

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrderRecommendationsView(APIView):
    """
    GET /ai/recommendations/order/<order_id>/
    Returns recommendations based on a completed order (post-checkout).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            result = get_order_recommendations(order_id)

            if result["recommendations"]:
                products = resolve_product_names_to_objects(result["recommendations"])
                result["products"] = ProductSerializer(products, many=True).data

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatbotView(APIView):
    """
    POST /ai/chatbot/
    Provides an AI chat interface powered by local Ollama (qwen2.5:7b).
    """
    permission_classes = [AllowAny] # Use IsAuthenticated in production

    def post(self, request):
        user_message = request.data.get("message")
        if not user_message:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Delegate to modular logic
        result = chatbot_logic.get_response(user_message)
        
        if result.get("success") is False:
            return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(result, status=status.HTTP_200_OK)

