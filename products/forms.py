from django import forms
from .models import Product
from categories.models import Category
from allergens.models import Allergen

class ProductForm(forms.ModelForm):
    UNIT_CHOICES = [
        ('kg', 'Kilogram (kg)'),
        ('g', 'Gram (g)'),
        ('bunch', 'Bunch'),
        ('piece', 'Piece/Each'),
        ('box', 'Box'),
        ('bag', 'Bag'),
        ('liter', 'Liter (L)'),
    ]

    unit = forms.ChoiceField(choices=UNIT_CHOICES, initial='kg', widget=forms.Select(attrs={'class': 'form-control'}))
    
    available_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    available_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price', 'unit', 
            'available_from', 'available_to', 'stock_quantity', 'allergens'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Fresh Carrots'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe your product...'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'allergens': forms.CheckboxSelectMultiple(attrs={'class': 'allergen-checkbox-group'}),
        }
        labels = {
            'available_from': 'Available From (Optional)',
            'available_to': 'Available To (Optional)',
            'stock_quantity': 'Stock Quantity',
        }
