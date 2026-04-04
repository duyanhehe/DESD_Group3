from django import forms
from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ["producer", "created_at"]

    def clean(self):
        cleaned_data = super().clean()

        stock = cleaned_data.get("stock_quantity")
        price = cleaned_data.get("price")

        if stock is not None and stock < 0:
            raise forms.ValidationError("Stock cannot be negative.")

        if price is not None and price <= 0:
            raise forms.ValidationError("Price must be greater than 0.")

        return cleaned_data
