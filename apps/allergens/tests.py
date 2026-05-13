"""
Test suite for the Allergens app.

Tests cover:
- Allergen creation
- Slug auto-generation
- Allergen CRUD operations
"""

import pytest
from apps.allergens.models import Allergen

pytestmark = pytest.mark.django_db


# ============================================================================
# UNIT TESTS: Allergen Creation
# ============================================================================


class TestAllergenCreation:
    """Unit tests for allergen model."""

    def test_create_allergen(self):
        """
        Test: Creating an allergen.
        """
        allergen = Allergen.objects.create(name="Peanuts")

        assert allergen.name == "Peanuts"
        assert allergen.id is not None

    def test_allergen_slug_auto_generation(self):
        """
        Test: Slug is auto-generated from name.
        """
        allergen = Allergen.objects.create(name="Tree Nuts")

        assert allergen.slug == "tree-nuts"

    def test_allergen_slug_auto_generated_on_save(self):
        """
        Test: Slug generated only if blank on save.
        """
        allergen = Allergen(name="Milk")
        assert allergen.slug == ""

        allergen.save()

        assert allergen.slug == "milk"

    def test_allergen_slug_preserves_custom_slug(self):
        """
        Test: If slug is provided, it's not overwritten.
        """
        allergen = Allergen(name="Fish", slug="finfish")
        allergen.save()

        assert allergen.slug == "finfish"

    def test_allergen_name_unique(self):
        """
        Test: Allergen name field is unique.
        """
        Allergen.objects.create(name="Shellfish")

        with pytest.raises(Exception):  # IntegrityError
            Allergen.objects.create(name="Shellfish")

    def test_allergen_slug_unique(self):
        """
        Test: Slug field is unique.
        """
        Allergen.objects.create(name="Soy")

        with pytest.raises(Exception):  # IntegrityError
            Allergen.objects.create(name="Soy")  # Same name = same slug

    def test_allergen_string_representation(self):
        """
        Test: __str__ returns allergen name.
        """
        allergen = Allergen.objects.create(name="Gluten")

        assert str(allergen) == "Gluten"


# ============================================================================
# UNIT TESTS: Allergen CRUD
# ============================================================================


class TestAllergenCRUD:
    """Unit tests for CRUD operations."""

    def test_update_allergen_name(self):
        """
        Test: Updating allergen name (may not be expected in practice).
        """
        allergen = Allergen.objects.create(name="Original")
        original_slug = allergen.slug

        allergen.name = "Updated"
        allergen.save()

        # Slug should not change if it's already set
        assert allergen.slug == original_slug

    def test_delete_allergen(self):
        """
        Test: Deleting an allergen.
        """
        allergen = Allergen.objects.create(name="Temporary")
        allergen_id = allergen.id

        allergen.delete()

        assert Allergen.objects.filter(id=allergen_id).count() == 0

    def test_allergen_list(self):
        """
        Test: Listing all allergens.
        """
        Allergen.objects.create(name="Peanuts")
        Allergen.objects.create(name="Milk")
        Allergen.objects.create(name="Eggs")
        Allergen.objects.create(name="Fish")
        Allergen.objects.create(name="Shellfish")

        allergens = Allergen.objects.all()

        assert allergens.count() >= 5


# ============================================================================
# UNIT TESTS: Common Allergens
# ============================================================================


class TestCommonAllergens:
    """Tests for common allergens in Bristol Food Network."""

    def test_common_allergens_exist(self):
        """
        Test: Create common UK allergens.
        """
        common = [
            "Peanuts",
            "Tree Nuts",
            "Milk",
            "Eggs",
            "Fish",
            "Shellfish",
            "Soy",
            "Gluten",
            "Sesame",
            "Celery",
            "Mustard",
        ]

        for name in common:
            Allergen.objects.create(name=name)

        assert Allergen.objects.count() >= len(common)


if __name__ == "__main__":
    pytest.main([__file__])
