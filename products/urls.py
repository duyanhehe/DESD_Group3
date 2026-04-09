from django.urls import path
from .views import (
    CreateProductView,
    ProductListView,
    ProductDetailView,
    EditProductView,
    DeleteProductView,
    CategoryProductsView,
    product_list_page,
    product_detail_page,
    producer_dashboard,
    add_product,
    edit_product,
    delete_product,
    ProductSearchView,
    search_results_page,
)

urlpatterns = [
    # Template views
    path("", product_list_page, name="product_page"),
    path("search/", search_results_page, name="search_page"),
    path("<int:id>/", product_detail_page, name="product_detail_page"),
    path("producer/dashboard/", producer_dashboard, name="producer_dashboard"),
    path("producer/add/", add_product, name="add_product"),
    path("producer/edit/<int:id>/", edit_product, name="edit_product"),
    path("producer/delete/<int:id>/", delete_product, name="delete_product"),
    # API endpoints
    path("api/v1/", ProductListView.as_view(), name="product_list"),
    path("api/v1/create/", CreateProductView.as_view(), name="product_create"),
    path("api/v1/<int:id>/", ProductDetailView.as_view(), name="product_detail"),
    path("api/v1/<int:id>/edit/", EditProductView.as_view(), name="product_edit"),
    path(
        "api/v1/<int:id>/delete/",
        DeleteProductView.as_view(),
        name="product_delete",
    ),
    path(
        "api/v1/category/<slug:slug>/",
        CategoryProductsView.as_view(),
        name="product_by_category",
    ),
    path(
        "api/v1/search/",
        ProductSearchView.as_view(),
        name="product_search",
    ),
]
