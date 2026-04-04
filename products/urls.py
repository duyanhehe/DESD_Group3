from django.urls import path
from .views import (
    CreateProductView,
    ProductListView,
    ProductDetailView,
    EditProductView,
    DeleteProductView,
)

app_name = "products"

urlpatterns = [
    path("", ProductListView.as_view(), name="list"),
    path("create/", CreateProductView.as_view(), name="create"),
    path("<int:id>/", ProductDetailView.as_view(), name="detail"),
    path("<int:id>/edit/", EditProductView.as_view(), name="edit"),
    path("<int:id>/delete/", DeleteProductView.as_view(), name="delete"),
]
