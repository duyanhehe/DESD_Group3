from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
import requests
import json
import uuid

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

# Grading services
from .grading.services import GradingService


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

            # If user is authenticated, add personalized recommendations.
            if request.user.is_authenticated:
                personal = get_user_recommendations(request.user.id, limit=10)
                if personal["recommendations"]:
                    personal_products = resolve_product_names_to_objects(
                        personal["recommendations"]
                    )
                    response_data["personalized"] = ProductSerializer(
                        personal_products, many=True, context={"request": request}
                    ).data
                    response_data["personalized_explanation"] = personal.get(
                        "explanation",
                        "Based on your order history and local market trends.",
                    )

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


class GradingView(APIView):
    """
    POST /ai/grading/
    Analyzes fruit/vegetable images and returns quality grade with XAI explanation.

    Accepts:
    - Multipart form-data with 'image' field (file upload)
    - JSON with 'image_path' field (server-side file path)

    Returns:
    - Grade (A, B, C, D, or F for rotten)
    - Quality metrics (size, shape, ripeness, defect %)
    - XAI reasons for the grading decision
    - Optional heatmap for defective fruit
    """
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production

    def post(self, request):
        # Handle file upload
        if 'image' in request.FILES:
            uploaded_file = request.FILES['image']

            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
            if uploaded_file.content_type not in allowed_types:
                return Response(
                    {"error": f"Invalid file type. Allowed: {allowed_types}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate file size (max 10MB)
            if uploaded_file.size > 10 * 1024 * 1024:
                return Response(
                    {"error": "File too large. Maximum size: 10MB"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                result = GradingService.analyze_upload(uploaded_file)

                if not result.get('success'):
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)

                # Save heatmap if available
                if result.get('heatmap') is not None:
                    heatmap_filename = f"heatmap_{uuid.uuid4().hex[:8]}.png"
                    heatmap_url = GradingService.save_heatmap(
                        result['heatmap'],
                        heatmap_filename
                    )
                    result['xai']['heatmap_url'] = heatmap_url
                    del result['heatmap']  # Remove numpy array from response

                return Response(result, status=status.HTTP_200_OK)

            except Exception as e:
                return Response(
                    {"error": f"Processing failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Handle image path
        elif 'image_path' in request.data:
            image_path = request.data.get('image_path')

            if not image_path:
                return Response(
                    {"error": "image_path is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                result = GradingService.analyze(image_path)

                if not result.get('success'):
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)

                # Save heatmap if available
                if result.get('heatmap') is not None:
                    heatmap_filename = f"heatmap_{uuid.uuid4().hex[:8]}.png"
                    heatmap_url = GradingService.save_heatmap(
                        result['heatmap'],
                        heatmap_filename
                    )
                    result['xai']['heatmap_url'] = heatmap_url
                    del result['heatmap']  # Remove numpy array from response

                return Response(result, status=status.HTTP_200_OK)

            except Exception as e:
                return Response(
                    {"error": f"Processing failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        else:
            return Response(
                {
                    "error": "No image provided. Upload via 'image' field (multipart) or provide 'image_path' (JSON)"
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class ChatbotView(APIView):
    """
    POST /ai/chatbot/
    Provides an AI chat interface powered by local Ollama (qwen2.5:7b).
    """
    permission_classes = [AllowAny] # Use IsAuthenticated in production

    def post(self, request):
        user_message = request.data.get("message")
        recommendation_data = request.data.get("recommendation_data")
        
        if not user_message:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Delegate to modular logic with optional XAI context and user history
        result = chatbot_logic.get_response(user_message, recommendation_data=recommendation_data, user=request.user)

        if result.get("success") is False:
            return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(result, status=status.HTTP_200_OK)

