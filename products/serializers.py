from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    producer_name = serializers.CharField(source="producer.username", read_only=True)
    status = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "stock_quantity",
            "producer",
            "producer_name",
            "category",
            "category_name",
            "category_slug",
            "status",
            "is_available",
            "available_from",
            "available_to",
            "created_at",
        ]
        read_only_fields = ["producer", "created_at"]

    def get_status(self, obj):
        return obj.get_status()
