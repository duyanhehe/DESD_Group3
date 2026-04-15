from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, OrderStatusLog


# ─── Cart ───────────────────────────────────────────────────

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    producer_id = serializers.IntegerField(source="product.producer.id", read_only=True)
    producer_name = serializers.CharField(source="product.producer.username", read_only=True)
    unit_price = serializers.DecimalField(
        source="product.price", max_digits=10, decimal_places=2, read_only=True
    )
    unit = serializers.CharField(source="product.unit", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id", "product", "product_name",
            "producer_id", "producer_name",
            "unit_price", "unit", "quantity", "subtotal",
        ]
        read_only_fields = ["id"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    # group items by producer for multi-vendor awareness (DESD-58)
    grouped_by_producer = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total", "grouped_by_producer", "updated_at"]

    def get_total(self, obj):
        return sum(item.subtotal for item in obj.items.all())

    def get_grouped_by_producer(self, obj):
        """Group cart items by producer so the frontend can show
        which items come from which farm."""
        groups = {}
        for item in obj.items.select_related("product__producer").all():
            producer = item.product.producer
            key = str(producer.id)
            if key not in groups:
                groups[key] = {
                    "producer_id": producer.id,
                    "producer_name": producer.username,
                    "items": [],
                    "subtotal": 0,
                }
            item_data = CartItemSerializer(item).data
            groups[key]["items"].append(item_data)
            groups[key]["subtotal"] += float(item.subtotal)
        return list(groups.values())


# ─── Orders ─────────────────────────────────────────────────

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    producer_name = serializers.CharField(source="producer.username", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id", "product", "product_name",
            "producer", "producer_name",
            "quantity", "unit_price", "subtotal",
        ]


class OrderStatusLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(
        source="changed_by.username", read_only=True, default=None
    )

    class Meta:
        model = OrderStatusLog
        fields = [
            "id", "old_status", "new_status",
            "changed_by", "changed_by_name",
            "note", "timestamp",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_logs = OrderStatusLogSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "customer", "customer_name",
            "status", "total_price",
            "items", "status_logs",
            "created_at", "updated_at",
        ]
        read_only_fields = ["customer", "total_price", "created_at", "updated_at"]

    def get_customer_name(self, obj):
        u = obj.customer
        full = f"{u.first_name} {u.last_name}".strip()
        return full if full else u.username


# ─── Producer view — only shows their own items + customer contact ───

class ProducerOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "quantity", "unit_price", "subtotal"]


class ProducerOrderSerializer(serializers.ModelSerializer):
    """What a producer sees: their items only + customer contact details."""
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    customer_phone = serializers.CharField(
        source="customer.phone_number", read_only=True, default=""
    )
    delivery_address = serializers.SerializerMethodField()
    customer_postcode = serializers.SerializerMethodField()
    # filtered in the view — only this producer's items
    my_items = serializers.SerializerMethodField()
    my_subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "status",
            "customer_name", "customer_email",
            "customer_phone", "delivery_address", "customer_postcode",
            "my_items", "my_subtotal", "total_price",
            "created_at", "updated_at",
        ]

    def get_customer_name(self, obj):
        u = obj.customer
        full = f"{u.first_name} {u.last_name}".strip()
        return full if full else u.username

    def get_delivery_address(self, obj):
        profile = getattr(obj.customer, "customer_profile", None)
        return profile.delivery_address if profile else ""

    def get_customer_postcode(self, obj):
        profile = getattr(obj.customer, "customer_profile", None)
        return profile.postcode if profile else ""

    def get_my_items(self, obj):
        """Only return items belonging to the requesting producer."""
        producer = self.context.get("request").user
        items = obj.items.filter(producer=producer)
        return ProducerOrderItemSerializer(items, many=True).data

    def get_my_subtotal(self, obj):
        producer = self.context.get("request").user
        items = obj.items.filter(producer=producer)
        return sum(item.subtotal for item in items)
