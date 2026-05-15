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
    education_list_page,
    add_recipe,
    add_story,
    add_review,
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
    path("education/", education_list_page, name="education_page"),
    path("education/add_recipe/", add_recipe, name="add_recipe"),
    path("education/add_story/", add_story, name="add_story"),
    
    # API endpoints
    path("api/v1/", ProductListView.as_view(), name="product_list"),
    path("api/v1/create/", CreateProductView.as_view(), name="product_create"),
    path("api/v1/<int:id>/", ProductDetailView.as_view(), name="product_detail"),
    path("api/v1/<int:id>/edit/", EditProductView.as_view(), name="product_edit"),
    path("api/v1/<int:product_id>/add_review/", add_review, name="add_review"),
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
