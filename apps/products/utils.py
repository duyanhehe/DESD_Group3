from rest_framework.exceptions import ValidationError


def validate_product_for_order(product, quantity):
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than 0.")

    if not product.is_in_season():
        raise ValidationError("Product is out of season.")

    if not product.is_available:
        raise ValidationError("Product is not available.")

    if product.stock_quantity < quantity:
        raise ValidationError("Not enough stock available.")
