#!/usr/bin/env python
"""
=============================================================================
  FOOD NETWORK MARKETPLACE — Mock Data Seeder
  Creates 40 products + prerequisite data (users, categories, allergens)

  Run from DESD_Group3 directory:
    python mock_data.py
=============================================================================

Allocation:
  Group 1: Normal Products         (15 records) - is_available=True, stock>0
  Group 2: Seasonal Products       (10 records) - testing is_in_season()
  Group 3: Out of Stock / Rotten   ( 7 records) - stock_quantity=0
  Group 4: Allergy Constrained     ( 8 records) - testing allergens M2M
"""

import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# ── Django Setup ──
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.accounts.models import User, CustomerProfile, ProducerProfile
from apps.categories.models import Category
from apps.allergens.models import Allergen
from apps.products.models import Product


def seed():
    print("=" * 60)
    print("  FOOD NETWORK MARKETPLACE — Mock Data Seeder")
    print("=" * 60)

    today = date.today()

    # ================================================================
    # 1. USERS — 2 Producers + 2 Customers (for future order testing)
    # ================================================================
    print("\n[1/4] Creating User accounts...")

    # ── Producer 1 ──
    farmer1, created = User.objects.get_or_create(
        username="farmer1",
        defaults={
            "email": "farmer1@foodnetwork.com",
            "first_name": "John",
            "last_name": "Farmer",
            "is_customer": False,
            "is_producer": True,
            "phone_number": "07700900001",
        },
    )
    if created:
        farmer1.set_password("password123")
        farmer1.save()
        ProducerProfile.objects.get_or_create(
            user=farmer1,
            defaults={
                "business_name": "Green Valley Farm",
                "business_address": "123 Farm Lane, Bristol BS1 1AA",
                "farm_origin": "Somerset",
                "postcode": "BS1 1AA",
            },
        )
        print("  ✓ farmer1 (John Farmer) — Green Valley Farm")
    else:
        print("  → farmer1 already exists, skipping")

    # ── Producer 2 ──
    farmer2, created = User.objects.get_or_create(
        username="farmer2",
        defaults={
            "email": "farmer2@foodnetwork.com",
            "first_name": "Jane",
            "last_name": "Grower",
            "is_customer": False,
            "is_producer": True,
            "phone_number": "07700900002",
        },
    )
    if created:
        farmer2.set_password("password123")
        farmer2.save()
        ProducerProfile.objects.get_or_create(
            user=farmer2,
            defaults={
                "business_name": "Sunrise Orchards",
                "business_address": "456 Orchard Road, Bath BA1 2QF",
                "farm_origin": "Wiltshire",
                "postcode": "BA1 2QF",
            },
        )
        print("  ✓ farmer2 (Jane Grower) — Sunrise Orchards")
    else:
        print("  → farmer2 already exists, skipping")

    # ── Customer 1 (for future cart/order testing) ──
    customer1, created = User.objects.get_or_create(
        username="customer1",
        defaults={
            "email": "alice@email.com",
            "first_name": "Alice",
            "last_name": "Smith",
            "is_customer": True,
            "is_producer": False,
            "phone_number": "07700900010",
        },
    )
    if created:
        customer1.set_password("password123")
        customer1.save()
        CustomerProfile.objects.get_or_create(
            user=customer1,
            defaults={
                "delivery_address": "789 High Street, Bristol BS2 0JA",
                "postcode": "BS2 0JA",
            },
        )
        print("  ✓ customer1 (Alice Smith)")
    else:
        print("  → customer1 already exists, skipping")

    # ── Customer 2 ──
    customer2, created = User.objects.get_or_create(
        username="customer2",
        defaults={
            "email": "bob@email.com",
            "first_name": "Bob",
            "last_name": "Jones",
            "is_customer": True,
            "is_producer": False,
            "phone_number": "07700900011",
        },
    )
    if created:
        customer2.set_password("password123")
        customer2.save()
        CustomerProfile.objects.get_or_create(
            user=customer2,
            defaults={
                "delivery_address": "12 Park Row, Bath BA1 1LR",
                "postcode": "BA1 1LR",
            },
        )
        print("  ✓ customer2 (Bob Jones)")
    else:
        print("  → customer2 already exists, skipping")

    # ================================================================
    # 2. CATEGORIES
    # ================================================================
    print("\n[2/4] Creating Categories...")

    cat_apple, _ = Category.objects.get_or_create(name="Apple", defaults={"slug": "apple"})
    cat_banana, _ = Category.objects.get_or_create(name="Banana", defaults={"slug": "banana"})
    cat_bellpepper, _ = Category.objects.get_or_create(name="Bellpepper", defaults={"slug": "bellpepper"})
    cat_carrot, _ = Category.objects.get_or_create(name="Carrot", defaults={"slug": "carrot"})
    cat_cucumber, _ = Category.objects.get_or_create(name="Cucumber", defaults={"slug": "cucumber"})
    cat_grape, _ = Category.objects.get_or_create(name="Grape", defaults={"slug": "grape"})
    cat_guava, _ = Category.objects.get_or_create(name="Guava", defaults={"slug": "guava"})
    cat_jujube, _ = Category.objects.get_or_create(name="Jujube", defaults={"slug": "jujube"})
    cat_mango, _ = Category.objects.get_or_create(name="Mango", defaults={"slug": "mango"})
    cat_orange, _ = Category.objects.get_or_create(name="Orange", defaults={"slug": "orange"})
    cat_pomegranate, _ = Category.objects.get_or_create(name="Pomegranate", defaults={"slug": "pomegranate"})
    cat_potato, _ = Category.objects.get_or_create(name="Potato", defaults={"slug": "potato"})
    cat_strawberry, _ = Category.objects.get_or_create(name="Strawberry", defaults={"slug": "strawberry"})
    cat_tomato, _ = Category.objects.get_or_create(name="Tomato", defaults={"slug": "tomato"})
    print(f"  ✓ Categories: Apple, Banana, Bellpepper, Carrot, Cucumber, Grape, Guava, Jujube, Mango, Orange, Pomegranate, Potato, Strawberry, Tomato")

    # ================================================================
    # 3. ALLERGENS — Use existing 14 from fixtures
    # ================================================================
    print("\n[3/4] Loading Allergens...")

    # Ensure all 14 standard UK allergens exist
    standard_allergens = [
        "Celery",
        "Cereals containing gluten",
        "Crustaceans",
        "Eggs",
        "Fish",
        "Lupin",
        "Milk",
        "Molluscs",
        "Mustard",
        "Nuts",
        "Peanuts",
        "Sesame",
        "Soya",
        "Sulphur dioxide",
    ]
    for name in standard_allergens:
        Allergen.objects.get_or_create(name=name)

    # Build lookup dict for easy access
    alg = {a.name: a for a in Allergen.objects.all()}
    print(f"  ✓ {len(alg)} allergens loaded")

    # ================================================================
    # 4. PRODUCTS — 40 records in 4 groups
    # ================================================================
    print("\n[4/4] Creating 40 Products...")

    created_count = 0
    skipped_count = 0

    def create_product(
        name,
        producer,
        category,
        description,
        price,
        unit,
        stock_quantity,
        image=None,
        is_available=True,
        available_from=None,
        available_to=None,
        product_allergens=None,
    ):
        """
        Helper to create a product with get_or_create pattern.
        M2M allergens are set AFTER save (required by Django ORM).

        NOTE: Product.save() calls update_availability() which will
        force is_available=False if the product is out of season.
        """
        nonlocal created_count, skipped_count

        # Default image if not provided
        if image is None:
            image = f"products/{category.slug}/{name.lower().replace(' ', '_')}.jpg"

        product, created = Product.objects.get_or_create(
            name=name,
            defaults={
                "producer": producer,
                "category": category,
                "description": description,
                "price": Decimal(str(price)),
                "unit": unit,
                "stock_quantity": stock_quantity,
                "image": image,
                "is_available": is_available,
                "available_from": available_from,
                "available_to": available_to,
            },
        )
        if created:
            if product_allergens:
                product.allergens.set(product_allergens)
            created_count += 1
            status = product.get_status()
            active = product.is_active()
            print(
                f"  ✓ [{created_count:02d}] {name:<45} "
                f"status={status:<12} is_active={active}"
            )
        else:
            skipped_count += 1
            print(f"  → {name} (already exists)")

        return product

    # ────────────────────────────────────────────────────────────
    # GROUP 1: Normal Products (15 records)
    # Testing: is_available=True, stock>0, no season dates
    # Expected: get_status()="Available", is_active()=True
    # ────────────────────────────────────────────────────────────
    print("\n  ── Group 1: Normal Products (15) ──")
    print("  Expected: status=Available, is_active=True\n")

    create_product(
        name="Fresh Fuji Apple",
        producer=farmer1,
        category=cat_apple,
        description="Crisp and sweet Fuji apples, freshly picked from our orchard. "
        "Perfect for snacking, baking, or salads.",
        price=3.50,
        unit="kg",
        stock_quantity=150,
    )
    create_product(
        name="Cavendish Banana",
        producer=farmer1,
        category=cat_banana,
        description="Ripe yellow Cavendish bananas. Rich in potassium and "
        "naturally sweet. Sold in bunches.",
        price=1.20,
        unit="bunch",
        stock_quantity=200,
    )
    create_product(
        name="Valencia Orange",
        producer=farmer1,
        category=cat_orange,
        description="Juicy Valencia oranges, ideal for fresh juice or eating. "
        "Sourced from our sunny grove.",
        price=2.80,
        unit="kg",
        stock_quantity=120,
    )
    create_product(
        name="Fresh Guava",
        producer=farmer2,
        category=cat_guava,
        description="Large seedless watermelon, perfect for summer gatherings. "
        "Sweet and refreshing.",
        price=5.00,
        unit="piece",
        stock_quantity=60,
    )
    create_product(
        name="Green Grapes",
        producer=farmer2,
        category=cat_grape,
        description="Plump green seedless grapes. Great for snacking, "
        "cheese boards, or freezing as treats.",
        price=4.20,
        unit="kg",
        stock_quantity=80,
    )
    create_product(
        name="Fresh Jujube",
        producer=farmer1,
        category=cat_jujube,
        description="Hand-picked blueberries, bursting with antioxidants. "
        "Perfect for smoothies, cereals, or baking.",
        price=6.50,
        unit="box",
        stock_quantity=90,
    )
    create_product(
        name="Ripe Mango",
        producer=farmer2,
        category=cat_mango,
        description="Sweet and fragrant ripe mangoes. Ready to eat. "
        "Excellent for desserts and tropical dishes.",
        price=2.50,
        unit="piece",
        stock_quantity=70,
    )
    create_product(
        name="Fresh Tomato",
        producer=farmer1,
        category=cat_tomato,
        description="Vine-ripened tomatoes with rich, full flavour. "
        "Ideal for salads, sauces, and sandwiches.",
        price=2.00,
        unit="kg",
        stock_quantity=180,
    )
    create_product(
        name="Organic Carrot",
        producer=farmer2,
        category=cat_carrot,
        description="Freshly harvested organic carrots. Naturally sweet, "
        "great for roasting, juicing, or raw snacking.",
        price=1.80,
        unit="kg",
        stock_quantity=160,
    )
    create_product(
        name="Fresh Bell Pepper",
        producer=farmer1,
        category=cat_bellpepper,
        description="Mixed red, yellow, and green bell peppers. "
        "Crunchy and versatile for stir-fries and salads.",
        price=3.00,
        unit="kg",
        stock_quantity=100,
    )
    create_product(
        name="Cherry Tomato",
        producer=farmer2,
        category=cat_tomato,
        description="Sweet cherry tomatoes, perfect for salads and pasta. "
        "Grown in our greenhouse for year-round supply.",
        price=3.50,
        unit="box",
        stock_quantity=110,
    )
    create_product(
        name="Fresh Potato",
        producer=farmer1,
        category=cat_potato,
        description="Tender baby spinach leaves. Pre-washed and ready to eat. "
        "Rich in iron and vitamins.",
        price=2.50,
        unit="bag",
        stock_quantity=130,
    )
    create_product(
        name="Fresh Pomegranate",
        producer=farmer2,
        category=cat_pomegranate,
        description="Fresh corn on the cob, super sweet variety. "
        "Perfect for grilling, boiling, or barbecues.",
        price=1.50,
        unit="piece",
        stock_quantity=90,
    )
    create_product(
        name="Fresh Cucumber",
        producer=farmer1,
        category=cat_cucumber,
        description="Crisp and cool cucumbers. Grown hydroponically for "
        "consistent quality and taste.",
        price=0.90,
        unit="piece",
        stock_quantity=140,
    )
    create_product(
        name="Fresh Strawberry",
        producer=farmer2,
        category=cat_strawberry,
        description="Fresh broccoli florets, pre-cut and ready to cook. "
        "Packed with vitamins C and K.",
        price=2.20,
        unit="bag",
        stock_quantity=85,
    )

    # ────────────────────────────────────────────────────────────
    # GROUP 2: Seasonal Products (10 records)
    # Testing: is_in_season() method
    #
    # Case 2.1 (5 — currently IN season):
    #   available_from=past, available_to=future, is_available=False
    #   Expected: get_status()="In Season", is_active()=False
    #   (is_active=False because is_available=False; this tests
    #    that get_status checks seasonality independently)
    #
    # Case 2.2 (5 — OUT of season):
    #   available_from=2023-01-01, available_to=2023-12-31
    #   Expected: get_status()="Unavailable", is_active()=False
    # ────────────────────────────────────────────────────────────
    print("\n  ── Group 2: Seasonal Products (10) ──")
    print("  Case 2.1 — In season: status=In Season, is_active=False")
    print("  Case 2.2 — Out of season: status=Unavailable, is_active=False\n")

    # Case 2.1: Currently IN season (available_from=past, available_to=future)
    in_season_from = today - timedelta(days=30)
    in_season_to = today + timedelta(days=180)

    create_product(
        name="Winter Strawberry",
        producer=farmer1,
        category=cat_strawberry,
        description="Sweet winter strawberries grown in our heated greenhouse. "
        "Available during colder months only.",
        price=5.50,
        unit="box",
        stock_quantity=100,
        is_available=False,
        available_from=in_season_from,
        available_to=in_season_to,
    )
    create_product(
        name="Summer Mango",
        producer=farmer2,
        category=cat_mango,
        description="Tropical Alphonso mangoes imported for the summer season. "
        "Limited seasonal availability.",
        price=3.80,
        unit="piece",
        stock_quantity=100,
        is_available=False,
        available_from=in_season_from,
        available_to=in_season_to,
    )
    create_product(
        name="Autumn Bellpepper",
        producer=farmer1,
        category=cat_bellpepper,
        description="Large orange pumpkins, perfect for soups, pies, and "
        "Halloween decorations. Seasonal harvest.",
        price=4.00,
        unit="piece",
        stock_quantity=100,
        is_available=False,
        available_from=in_season_from,
        available_to=in_season_to,
    )
    create_product(
        name="Spring Cucumber",
        producer=farmer2,
        category=cat_cucumber,
        description="Fresh garden peas harvested in spring. Sweet and tender, "
        "best eaten fresh or lightly steamed.",
        price=3.20,
        unit="kg",
        stock_quantity=100,
        is_available=False,
        available_from=in_season_from,
        available_to=in_season_to,
    )
    create_product(
        name="Seasonal Guava",
        producer=farmer1,
        category=cat_guava,
        description="Golden pineapples at peak ripeness. Only available during "
        "the tropical import season.",
        price=3.50,
        unit="piece",
        stock_quantity=100,
        is_available=False,
        available_from=in_season_from,
        available_to=in_season_to,
    )

    # Case 2.2: OUT of season (dates in 2023, already passed)
    out_of_season_from = date(2023, 1, 1)
    out_of_season_to = date(2023, 12, 31)

    create_product(
        name="Christmas Strawberry",
        producer=farmer2,
        category=cat_strawberry,
        description="Special Christmas cherries, only harvested in December. "
        "This batch was from the 2023 season.",
        price=8.00,
        unit="box",
        stock_quantity=100,
        is_available=True,  # save() will force to False via update_availability
        available_from=out_of_season_from,
        available_to=out_of_season_to,
    )
    create_product(
        name="Summer Jujube",
        producer=farmer1,
        category=cat_jujube,
        description="Wild summer raspberries. Last season's listing — no longer "
        "available until next summer.",
        price=7.00,
        unit="box",
        stock_quantity=100,
        is_available=True,  # save() will force to False
        available_from=out_of_season_from,
        available_to=out_of_season_to,
    )
    create_product(
        name="Spring Carrot",
        producer=farmer2,
        category=cat_carrot,
        description="English asparagus, a spring delicacy. This listing "
        "has expired and will return next April.",
        price=6.00,
        unit="bunch",
        stock_quantity=100,
        is_available=True,  # save() will force to False
        available_from=out_of_season_from,
        available_to=out_of_season_to,
    )
    create_product(
        name="Autumn Grape",
        producer=farmer1,
        category=cat_grape,
        description="Fresh Turkish figs from the autumn harvest. "
        "Sweet and delicate. Season ended.",
        price=5.50,
        unit="box",
        stock_quantity=100,
        is_available=True,  # save() will force to False
        available_from=out_of_season_from,
        available_to=out_of_season_to,
    )
    create_product(
        name="Winter Potato",
        producer=farmer2,
        category=cat_potato,
        description="Frost-sweetened parsnips from our winter crop. "
        "Perfect for roasting. Season has passed.",
        price=2.50,
        unit="kg",
        stock_quantity=100,
        is_available=True,  # save() will force to False
        available_from=out_of_season_from,
        available_to=out_of_season_to,
    )

    # ────────────────────────────────────────────────────────────
    # GROUP 3: Out of Stock / Rotten Products (7 records)
    # Testing: is_active()=False when stock_quantity=0
    # Category: "Compost & Grade 2"
    #
    # NOTE: Current get_status() does NOT return "Out of Stock",
    # it returns "Available" if is_available=True. This is a known
    # gap — the model may need updating to check stock_quantity.
    # ────────────────────────────────────────────────────────────
    print("\n  ── Group 3: Rotten / Out of Stock (7) ──")
    print("  Expected: is_active=False (stock=0)\n")

    create_product(
        name="Rotten Tomato (For Compost)",
        producer=farmer1,
        category=cat_tomato,
        description="Batch of overripe tomatoes unsuitable for consumption. "
        "Ideal for composting or agricultural fertiliser.",
        price=0.50,
        unit="kg",
        stock_quantity=0,
        is_available=False,
    )
    create_product(
        name="Spoiled Carrot Batch",
        producer=farmer2,
        category=cat_carrot,
        description="Carrots with surface damage and early rot. "
        "Suitable for animal feed or compost only.",
        price=0.30,
        unit="kg",
        stock_quantity=0,
        is_available=False,
    )
    create_product(
        name="Damaged Apple Lot",
        producer=farmer1,
        category=cat_apple,
        description="Bruised and damaged apples from harvest sorting. "
        "Grade 2 — for juice production or compost.",
        price=0.80,
        unit="kg",
        stock_quantity=0,
        is_available=True,
    )
    create_product(
        name="Overripe Banana Batch",
        producer=farmer2,
        category=cat_banana,
        description="Heavily spotted bananas past retail quality. "
        "Can be used for banana bread or compost.",
        price=0.40,
        unit="bunch",
        stock_quantity=0,
        is_available=True,
    )
    create_product(
        name="Moldy Grape Cluster",
        producer=farmer1,
        category=cat_grape,
        description="Grape clusters showing visible mold growth. "
        "Not safe for consumption. For composting only.",
        price=0.20,
        unit="kg",
        stock_quantity=0,
        is_available=False,
    )
    create_product(
        name="Bruised Strawberry Batch",
        producer=farmer2,
        category=cat_strawberry,
        description="Peaches with impact damage from transport. "
        "Grade 2 quality — suitable for jam production.",
        price=1.00,
        unit="kg",
        stock_quantity=0,
        is_available=False,
    )
    create_product(
        name="Wilted Cucumber For Composting",
        producer=farmer1,
        category=cat_cucumber,
        description="Wilted iceberg lettuce past its shelf life. "
        "Intended for composting or green waste recycling.",
        price=0.10,
        unit="bag",
        stock_quantity=0,
        is_available=True,
    )

    # ────────────────────────────────────────────────────────────
    # GROUP 4: Allergy Constrained Products (8 records)
    # Testing: ManyToMany allergens field
    # Expected: allergen_names returns list of strings in API
    #
    # Uses the 14 standard UK allergens already in the database:
    # Celery, Cereals containing gluten, Crustaceans, Eggs, Fish,
    # Lupin, Milk, Molluscs, Mustard, Nuts, Peanuts, Sesame,
    # Soya, Sulphur dioxide
    # ────────────────────────────────────────────────────────────
    print("\n  ── Group 4: Allergy Constrained (8) ──")
    print("  Expected: allergen_names populated in API response\n")

    create_product(
        name="Strawberry Milk Smoothie",
        producer=farmer1,
        category=cat_strawberry,
        description="Fresh strawberry smoothie made with whole milk. "
        "Creamy, sweet, and ready to drink.",
        price=4.50,
        unit="unit",
        stock_quantity=50,
        product_allergens=[alg["Milk"]],
    )
    create_product(
        name="Walnut Banana Bread Mix",
        producer=farmer2,
        category=cat_banana,
        description="Pre-mixed banana bread kit with crushed walnuts and "
        "wheat flour. Just add eggs and bake.",
        price=5.00,
        unit="box",
        stock_quantity=50,
        product_allergens=[alg["Nuts"], alg["Cereals containing gluten"]],
    )
    create_product(
        name="Cucumber Salad with Tuna Dressing",
        producer=farmer1,
        category=cat_cucumber,
        description="Fresh cucumber salad kit with a tuna-based vinaigrette. "
        "Ready to assemble in 5 minutes.",
        price=6.00,
        unit="box",
        stock_quantity=50,
        product_allergens=[alg["Fish"]],
    )
    create_product(
        name="Sesame Carrot Sticks",
        producer=farmer2,
        category=cat_carrot,
        description="Crunchy carrot sticks coated in toasted sesame seeds. "
        "A healthy snack with an Asian twist.",
        price=3.50,
        unit="bag",
        stock_quantity=50,
        product_allergens=[alg["Sesame"]],
    )
    create_product(
        name="Soy Glazed Edamame",
        producer=farmer1,
        category=cat_potato,
        description="Steamed edamame pods with a sweet soy glaze. "
        "High in plant protein. Vegan-friendly.",
        price=4.00,
        unit="bag",
        stock_quantity=50,
        product_allergens=[alg["Soya"]],
    )
    create_product(
        name="Peanut Butter Apple Slices",
        producer=farmer2,
        category=cat_apple,
        description="Pre-sliced apples paired with creamy peanut butter dip. "
        "A classic protein-packed snack.",
        price=3.80,
        unit="box",
        stock_quantity=50,
        product_allergens=[alg["Peanuts"], alg["Milk"]],
    )
    create_product(
        name="Egg Fried Vegetable Rice Mix",
        producer=farmer1,
        category=cat_bellpepper,
        description="Stir-fry kit with mixed vegetables, egg strips, and soy sauce. "
        "Contains celery and soya.",
        price=5.50,
        unit="box",
        stock_quantity=50,
        product_allergens=[alg["Eggs"], alg["Soya"], alg["Celery"]],
    )
    create_product(
        name="Celery and Mustard Soup Starter",
        producer=farmer2,
        category=cat_pomegranate,
        description="Soup base with fresh celery, wholegrain mustard, and herbs. "
        "Just add water and simmer.",
        price=3.00,
        unit="box",
        stock_quantity=50,
        product_allergens=[alg["Celery"], alg["Mustard"]],
    )

    # ================================================================
    # SUMMARY
    # ================================================================
    total_products = Product.objects.count()
    active_count = sum(1 for p in Product.objects.all() if p.is_active())
    inactive_count = total_products - active_count

    print("\n" + "=" * 60)
    print(f"  ✅ DONE!")
    print(f"  New records created  : {created_count}")
    print(f"  Skipped (existing)   : {skipped_count}")
    print(f"  Total products in DB : {total_products}")
    print(f"  Active (visible)     : {active_count}")
    print(f"  Inactive (hidden)    : {inactive_count}")
    print(f"  Users in DB          : {User.objects.count()}")
    print(f"  Categories in DB     : {Category.objects.count()}")
    print(f"  Allergens in DB      : {Allergen.objects.count()}")
    print("=" * 60)

    # Verify allergen groups
    print("\n  Allergen verification (Group 4):")
    group4_names = [
        "Strawberry Milk Smoothie",
        "Walnut Banana Bread Mix",
        "Cucumber Salad with Tuna Dressing",
        "Sesame Carrot Sticks",
        "Soy Glazed Edamame",
        "Peanut Butter Apple Slices",
        "Egg Fried Vegetable Rice Mix",
        "Celery and Mustard Soup Starter",
    ]
    for name in group4_names:
        try:
            p = Product.objects.get(name=name)
            allergen_list = [a.name for a in p.allergens.all()]
            print(f"  {p.name}: {allergen_list}")
        except Product.DoesNotExist:
            print(f"  ⚠ {name}: NOT FOUND")

    print()


if __name__ == "__main__":
    seed()
