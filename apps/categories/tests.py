"""
Test suite for the Categories app.

Tests cover:
- Category creation
- Slug auto-generation
- Category CRUD operations
"""

import pytest
from apps.categories.models import Category

pytestmark = pytest.mark.django_db


# ============================================================================
# UNIT TESTS: Category Creation
# ============================================================================


class TestCategoryCreation:
    """Unit tests for category model."""

    def test_create_category(self):
        """
        Test: Creating a category.
        """
        category = Category.objects.create(name="Vegetables")

        assert category.name == "Vegetables"
        assert category.id is not None

    def test_category_slug_auto_generation(self):
        """
        Test: Slug is auto-generated from name.
        """
        category = Category.objects.create(name="Dairy Products")

        assert category.slug == "dairy-products"

    def test_category_slug_auto_generated_on_save(self):
        """
        Test: Slug generated only if blank on save.
        """
        category = Category(name="Bakery")
        assert category.slug == ""

        category.save()

        assert category.slug == "bakery"

    def test_category_slug_preserves_custom_slug(self):
        """
        Test: If slug is provided, it's not overwritten.
        """
        category = Category(name="Preserved Foods", slug="canned-goods")
        category.save()

        assert category.slug == "canned-goods"

    def test_category_slug_unique(self):
        """
        Test: Slug field is unique.
        """
        Category.objects.create(name="Fruits")

        with pytest.raises(Exception):  # IntegrityError
            Category.objects.create(name="Fruits")  # Same name = same slug

    def test_category_string_representation(self):
        """
        Test: __str__ returns category name.
        """
        category = Category.objects.create(name="Preserves")

        assert str(category) == "Preserves"


# ============================================================================
# UNIT TESTS: Category CRUD
# ============================================================================


class TestCategoryCRUD:
    """Unit tests for CRUD operations."""

    def test_update_category_name(self):
        """
        Test: Updating category name.
        """
        category = Category.objects.create(name="Original")
        original_slug = category.slug

        category.name = "Updated"
        category.save()

        # Slug should not change if it's already set
        assert category.slug == original_slug

    def test_delete_category(self):
        """
        Test: Deleting a category.
        """
        category = Category.objects.create(name="Temporary")
        category_id = category.id

        category.delete()

        assert Category.objects.filter(id=category_id).count() == 0

    def test_category_list(self):
        """
        Test: Listing all categories.
        """
        Category.objects.create(name="Vegetables")
        Category.objects.create(name="Fruits")
        Category.objects.create(name="Dairy")

        categories = Category.objects.all()

        assert categories.count() >= 3


# ============================================================================
# INTEGRATION TESTS: API
# ============================================================================


class TestCategoryAPI:
    """Integration tests for category API endpoints."""

    def test_list_categories_endpoint(self):
        """
        Test: GET /categories/api/v1/ returns all categories.
        """
        from rest_framework.test import APIClient
        from rest_framework import status

        Category.objects.create(name="Vegetables")
        Category.objects.create(name="Fruits")

        client = APIClient()
        response = client.get("/categories/api/v1/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2


if __name__ == "__main__":
    pytest.main([__file__])
