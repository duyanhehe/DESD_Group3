from .model import get_model
from .inference import recommend
from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from django.db.models import Count


def get_recommendations(user_items):
    """
    Get recommendations based on a list of items.
    Returns product names that are frequently bought together.
    """
    if not user_items:
        return {"recommendations": [], "explanation": "No items provided."}

    model = get_model()
    recs = recommend(model, set(user_items))

    return {
        "recommendations": recs,
        "explanation": f"Based on {len(user_items)} items in your selection.",
    }


def get_product_recommendations(product_name):
    """
    Get 'Frequently Bought Together' recommendations for a single product.
    Used on product detail pages.
    """
    return get_recommendations([product_name])


def get_cart_recommendations(cart_items):
    """
    Get recommendations based on cart items.
    cart_items: list of product names
    """
    return get_recommendations(cart_items)


def get_order_recommendations(order_id):
    """
    Get recommendations based on a completed order.
    Used post-checkout.
    """
    try:
        order = Order.objects.get(id=order_id, status="delivered")
        items = [item.product.name for item in order.items.all()]
        return get_recommendations(items)
    except Order.DoesNotExist:
        return {"recommendations": [], "explanation": "Order not found or not delivered."}


def get_trending_products(limit=10):
    """
    Get most frequently purchased products across all delivered orders.
    Used for homepage "Trending Now" section.
    Falls back to newest available products if no delivered orders exist.
    """
    trending = (
        OrderItem.objects.filter(order__status="delivered")
        .values("product__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    product_names = [item["product__name"] for item in trending]

    # Fallback: return newest available products if no delivered orders
    if not product_names:
        product_names = list(
            Product.objects.active()
            .order_by("-created_at")
            .values_list("name", flat=True)[:limit]
        )

    return product_names


def get_user_recommendations(user_id, limit=10):
    """
    Get personalized recommendations for a user based on their order history.
    Used for homepage "Recommended For You" section.
    """
    # Get user's past delivered orders
    orders = Order.objects.filter(customer_id=user_id, status="delivered")

    if not orders.exists():
        # New user - return trending items
        return {
            "recommendations": get_trending_products(limit),
            "explanation": "Popular items right now.",
        }

    # Get all items from user's orders
    all_items = []
    for order in orders:
        items = [item.product.name for item in order.items.all()]
        all_items.extend(items)

    # Get recommendations based on user's purchase history
    if all_items:
        result = get_recommendations(list(set(all_items)))
        return result

    return {"recommendations": [], "explanation": "No purchase history found."}


def resolve_product_names_to_objects(product_names):
    """
    Convert product names to Product objects for frontend display.
    """
    products = Product.objects.filter(name__in=product_names, is_available=True)
    return products
