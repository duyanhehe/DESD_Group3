from rest_framework import serializers
from django.utils.timezone import now
from .models import Product, Allergen


class ProductSerializer(serializers.ModelSerializer):
    producer_name = serializers.CharField(source="producer.username", read_only=True)
    status = serializers.SerializerMethodField()

    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)

    # accept allergen IDs
    allergens = serializers.PrimaryKeyRelatedField(
        queryset=Allergen.objects.all(), many=True, required=True
    )

    # show allergen names
    allergen_names = serializers.SerializerMethodField()

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
            "allergens",
            "allergen_names",
            "status",
            "is_available",
            "available_from",
            "available_to",
            "unit",
            "created_at",
        ]
        read_only_fields = ["producer", "created_at"]

    def get_status(self, obj):
        return obj.get_status()

    def get_allergen_names(self, obj):
        return [a.name for a in obj.allergens.all()]

    # enforce requirement
    def validate_allergens(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError("You must specify at least one allergen.")
        return value

    def create(self, validated_data):
        allergens = validated_data.pop("allergens")
        product = Product.objects.create(**validated_data)
        product.allergens.set(allergens)
        return product

    def update(self, instance, validated_data):
        allergens = validated_data.pop("allergens", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if allergens is not None:
            instance.allergens.set(allergens)

        instance.save()
        return instance

    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock cannot be negative.")
        return value

    def validate(self, data):
        available_from = data.get(
            "available_from", getattr(self.instance, "available_from", None)
        )
        available_to = data.get(
            "available_to", getattr(self.instance, "available_to", None)
        )
        is_available = data.get(
            "is_available", getattr(self.instance, "is_available", True)
        )

        # date consistency
        if available_from and available_to and available_from > available_to:
            raise serializers.ValidationError(
                "available_from cannot be later than available_to."
            )
        today = now().date()

        # enforce season
        if is_available:
            if available_from and today < available_from:
                raise serializers.ValidationError("Product is not yet in season.")
            if available_to and today > available_to:
                raise serializers.ValidationError("Product is out of season.")

        return data
