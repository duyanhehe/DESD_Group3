from django import forms
from .models import Product
from apps.categories.models import Category
from apps.allergens.models import Allergen


class ProductForm(forms.ModelForm):
    UNIT_CHOICES = [
        ("unit", "Unit"),
        ("kg", "Kilogram (kg)"),
        ("g", "Gram (g)"),
        ("bunch", "Bunch"),
        ("piece", "Piece/Each"),
        ("box", "Box"),
        ("bag", "Bag"),
        ("liter", "Liter (L)"),
    ]

    unit = forms.ChoiceField(
        choices=UNIT_CHOICES,
        initial="unit",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    available_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    available_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    MONTH_CHOICES = [
        (0, "Not Seasonal"),
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December")
    ]

    season_start_month = forms.TypedChoiceField(
        choices=MONTH_CHOICES,
        coerce=int,
        required=False,
        initial=0,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Season Starts"
    )
    season_end_month = forms.TypedChoiceField(
        choices=MONTH_CHOICES,
        coerce=int,
        required=False,
        initial=0,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Season Ends"
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "description",
            "price",
            "unit",
            "image",
            "available_from",
            "available_to",
            "season_start_month",
            "season_end_month",
            "stock_quantity",
            "is_available",
            "is_organic",
            "is_surplus",
            "discount_price",
            "allergens",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Fresh Carrots"}
            ),
            "category": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe your product...",
                }
            ),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "stock_quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "allergens": forms.CheckboxSelectMultiple(
                attrs={"class": "allergen-checkbox-group"}
            ),
            "image": forms.FileInput(attrs={"id": "image-upload", "accept": "image/*"}),
        }
        labels = {
            "available_from": "Available From (Optional)",
            "available_to": "Available To (Optional)",
            "stock_quantity": "Stock Quantity",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['allergens'].required = False


from .models import Recipe, FarmStory

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ["title", "content", "image", "products"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Recipe Title"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Ingredients and instructions..."}),
            "products": forms.SelectMultiple(attrs={"class": "form-control"}),
            "image": forms.FileInput(attrs={"id": "image-upload", "accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        producer = kwargs.pop('producer', None)
        super().__init__(*args, **kwargs)
        if producer:
            self.fields['products'].queryset = Product.objects.filter(producer=producer)
        self.fields['products'].required = False


class FarmStoryForm(forms.ModelForm):
    class Meta:
        model = FarmStory
        fields = ["title", "content", "image", "products"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Story Title"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Share your story..."}),
            "products": forms.SelectMultiple(attrs={"class": "form-control"}),
            "image": forms.FileInput(attrs={"id": "image-upload", "accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        producer = kwargs.pop('producer', None)
        super().__init__(*args, **kwargs)
        if producer:
            self.fields['products'].queryset = Product.objects.filter(producer=producer)
        self.fields['products'].required = False
