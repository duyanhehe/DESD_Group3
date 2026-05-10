from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, OrderStatusLog, RefundRequest


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
    food_miles = serializers.FloatField(read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id", "product", "product_name",
            "producer_id", "producer_name",
            "unit_price", "unit", "quantity", "subtotal", "food_miles",
        ]
        read_only_fields = ["id"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    total_food_miles = serializers.FloatField(read_only=True)
    # group items by producer for multi-vendor awareness (DESD-58)
    grouped_by_producer = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total", "total_food_miles", "grouped_by_producer", "updated_at"]

    def get_total(self, obj):
        return sum(item.subtotal for item in obj.items.all())

    def to_representation(self, instance):
        """
        Optimize representation by grouping items that are already serialized.
        This avoids double serialization and redundant property calls.
        """
        data = super().to_representation(instance)
        
        # Group items by producer
        groups = {}
        for item_data in data.get('items', []):
            p_id = str(item_data.get('producer_id'))
            p_name = item_data.get('producer_name')
            
            if p_id not in groups:
                groups[p_id] = {
                    "producer_id": int(p_id),
                    "producer_name": p_name,
                    "items": [],
                    "subtotal": 0,
                    "food_miles": 0,
                }
            
            groups[p_id]["items"].append(item_data)
            groups[p_id]["subtotal"] += float(item_data.get('subtotal', 0))
            
            miles = item_data.get('food_miles')
            if miles is not None:
                groups[p_id]["food_miles"] += miles

        # Round food_miles in each group
        for group in groups.values():
            group["food_miles"] = round(group["food_miles"], 1)
            
        data['grouped_by_producer'] = list(groups.values())
        return data

    def get_grouped_by_producer(self, obj):
        # Placeholder because the field is required by SerializerMethodField
        # The actual work is done in to_representation for efficiency.
        return []


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
    items = serializers.SerializerMethodField()
    status_logs = OrderStatusLogSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()
    sub_orders = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "customer", "customer_name",
            "status", "total_price",
            "items", "sub_orders", "status_logs",
            "created_at", "updated_at",
        ]
        read_only_fields = ["customer", "total_price", "created_at", "updated_at"]

    def get_items(self, obj):
        # If it's a Master Order, fetch items from its sub_orders
        if obj.parent_order is None and obj.sub_orders.exists():
            items = OrderItem.objects.filter(order__parent_order=obj)
            return OrderItemSerializer(items, many=True).data
        return OrderItemSerializer(obj.items.all(), many=True).data

    def get_sub_orders(self, obj):
        if obj.parent_order is None:
            # Avoid recursion by only returning basic info
            return [{"id": so.id, "producer": so.producer.username if so.producer else None, "total_price": float(so.total_price), "status": so.status} for so in obj.sub_orders.all()]
        return None

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


# ─── Refund Requests ──────────────────────────────────────────

class RefundRequestSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source="order.id", read_only=True)
    customer_name = serializers.CharField(source="customer.username", read_only=True)
    item_name = serializers.CharField(source="order_item.product.name", read_only=True, default="Entire Order")

    class Meta:
        model = RefundRequest
        fields = [
            "id", "order_id", "order_item", "customer_name", "item_name",
            "reason_category", "reason_text", "evidence_image",
            "requested_amount", "status", "admin_note",
            "created_at", "resolved_at"
        ]
        read_only_fields = ["id", "order_id", "customer_name", "item_name", "requested_amount", "status", "admin_note", "resolved_at", "created_at"]

