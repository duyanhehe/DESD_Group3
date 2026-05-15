import pytest

from apps.allergens.models import Allergen

pytestmark = pytest.mark.django_db


def test_tc015_product_displays_clear_allergen_warnings(product):
    egg = Allergen.objects.create(name="Eggs")
    milk = Allergen.objects.create(name="Milk")

    product.allergens.add(egg, milk)

    warnings = set(product.allergens.values_list("name", flat=True))
    assert {"Eggs", "Milk"}.issubset(warnings)
    assert product.allergens.count() >= 2
