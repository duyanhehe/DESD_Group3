from django.urls import path
from .views import (
    RecommendationView,
    HomepageRecommendationsView,
    ProductRecommendationsView,
    CartRecommendationsView,
    OrderRecommendationsView,
    ChatbotView,
)

urlpatterns = [
    # General recommendation endpoint
    path("recommend/", RecommendationView.as_view(), name="recommend"),

    # Homepage recommendations (trending + personalized)
    path("recommendations/homepage/", HomepageRecommendationsView.as_view(), name="homepage_recommendations"),

    # Product page recommendations (frequently bought together)
    path("recommendations/product/<int:product_id>/", ProductRecommendationsView.as_view(), name="product_recommendations"),

    # Cart recommendations
    path("recommendations/cart/", CartRecommendationsView.as_view(), name="cart_recommendations"),

    # Post-checkout recommendations
    path("recommendations/order/<int:order_id>/", OrderRecommendationsView.as_view(), name="order_recommendations"),

    # Fruit/Vegetable grading
    path("grading/", GradingView.as_view(), name="grading"),
    # AI Chatbot endpoint
    path("chatbot/", ChatbotView.as_view(), name="chatbot"),
]