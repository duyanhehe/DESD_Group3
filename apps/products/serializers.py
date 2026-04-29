from rest_framework import serializers
from django.utils.timezone import now
from .models import Product, Allergen


# Serializer for Product model
class ProductSerializer(serializers.ModelSerializer):
    producer_name = serializers.CharField(source="producer.username", read_only=True)
    status = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    allergen_names = serializers.SerializerMethodField()
    
    # Use image field directly but also provide image_url for frontend compatibility
    image_url = serializers.SerializerMethodField()

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
            "unit",
            "created_at",
        )
        read_only_fields = ("producer", "created_at")

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
