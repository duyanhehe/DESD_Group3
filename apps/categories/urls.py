from django.urls import path
from .views import CategoryListView

urlpatterns = [
    path("api/v1/", CategoryListView.as_view(), name="category_list"),
]
