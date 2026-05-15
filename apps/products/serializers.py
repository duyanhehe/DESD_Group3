from rest_framework import serializers
from django.utils.timezone import now
from .models import Product, Allergen, Review


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.username", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "customer_name", "rating", "comment", "created_at")


# Serializer for Product model
class ProductSerializer(serializers.ModelSerializer):
    producer_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    allergen_names = serializers.SerializerMethodField()
    
    # Use image field directly but also provide image_url for frontend compatibility
    image_url = serializers.SerializerMethodField()
    food_miles = serializers.SerializerMethodField()
    reviews = ReviewSerializer(many=True, read_only=True)
    can_review = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "description",
            "price",
            "stock_quantity",
            "image",
            "image_url",
            "producer",
            "producer_name",
            "category",
            "category_name",
            "category_slug",
            "allergen_names",
            "status",
            "is_available",
            "available_from",
            "available_to",
            "season_start_month",
            "season_end_month",
            "unit",
            "created_at",
            "is_organic",
            "is_surplus",
            "discount_price",
            "low_stock_threshold",
            "reviews",
            "can_review",
            "food_miles",
        )
        read_only_fields = ("producer", "created_at")

    def get_food_miles(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        
        try:
            from apps.logistics.utils import calculate_distance_between_postcodes
            customer_profile = getattr(request.user, "customer_profile", None)
            producer_profile = getattr(obj.producer, "producer_profile", None)

            if not customer_profile or not producer_profile:
                return None
                
            c_pc = customer_profile.postcode
            p_pc = producer_profile.postcode
            
            if not c_pc or not p_pc:
                return None
                
            return calculate_distance_between_postcodes(p_pc, c_pc)
        except ImportError:
            return None

    def get_can_review(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
            
        from apps.orders.models import OrderItem, Order
        has_bought = OrderItem.objects.filter(
            order__customer=request.user,
            product=obj
        ).exclude(
            order__status__in=[Order.CANCELLED, Order.REFUNDED, Order.REFUND_REQUESTED]
        ).exists()
        
        has_reviewed = obj.reviews.filter(customer=request.user).exists()
        
        return has_bought and not has_reviewed

    def get_status(self, obj):
        return obj.get_status()

    def get_allergen_names(self, obj):
        return [a.name for a in obj.allergens.all()]

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_producer_name(self, obj):
        if hasattr(obj.producer, "producer_profile") and obj.producer.producer_profile.business_name:
            return obj.producer.producer_profile.business_name
        return obj.producer.username

    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock cannot be negative.")
        return value

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError("Product image is required.")
        return value

    def validate(self, data):
        available_from = data.get("available_from", getattr(self.instance, "available_from", None))
        available_to = data.get("available_to", getattr(self.instance, "available_to", None))
        is_available = data.get("is_available", getattr(self.instance, "is_available", True))

        if available_from and available_to and available_from > available_to:
            raise serializers.ValidationError("available_from cannot be later than available_to.")
        
        today = now().date()
        if is_available:
            if available_from and today < available_from:
                raise serializers.ValidationError("Product is not yet in season.")
            if available_to and today > available_to:
                raise serializers.ValidationError("Product is out of season.")

        return data


class ProductDetailSerializer(ProductSerializer):
    recipes = serializers.SerializerMethodField()
    farm_stories = serializers.SerializerMethodField()

    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields + (
            "recipes",
            "farm_stories",
        )

    def get_recipes(self, obj):
        return [{"id": r.id, "title": r.title, "image": r.image.url if r.image else None} for r in obj.recipes.all()]

    def get_farm_stories(self, obj):
        return [{"id": s.id, "title": s.title, "image": s.image.url if s.image else None} for s in obj.farm_stories.all()]
