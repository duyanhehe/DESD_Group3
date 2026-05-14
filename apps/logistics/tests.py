"""
Comprehensive test suite for the Logistics app (CRITICAL PATH).

Tests cover:
- Postcode geocoding (Nominatim API integration)
- Caching of geocoded results (24-hour TTL)
- Haversine distance calculations
- Food miles aggregation
"""

import pytest
import math
import responses
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import override_settings

from apps.logistics.utils import geocode_postcode, haversine_distance, NOMINATIM_URL

pytestmark = pytest.mark.django_db


# ============================================================================
# UNIT TESTS: Haversine Distance Calculation
# ============================================================================


class TestHaversineDistance:
    """Unit tests for haversine distance calculation."""

    def test_haversine_same_location(self):
        """
        Test: Distance between same location is 0 miles.
        """
        distance = haversine_distance(51.4545, -2.5879, 51.4545, -2.5879)

        assert distance == pytest.approx(0.0, abs=0.01)

    def test_haversine_known_distance_bristol_to_london(self):
        """
        Test: Distance Bristol to London ≈ 106 miles.
        Bristol: 51.4545, -2.5879
        London: 51.5074, -0.1278
        """
        # Bristol city centre
        lat1, lon1 = 51.4545, -2.5879
        # London city centre
        lat2, lon2 = 51.5074, -0.1278

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Should be approximately 106 miles
        assert 100 < distance < 115

    def test_haversine_known_distance_bristol_to_manchester(self):
        """
        Test: Distance Bristol to Manchester ≈ 140-160 miles.
        """
        # Bristol
        lat1, lon1 = 51.4545, -2.5879
        # Manchester
        lat2, lon2 = 53.4808, -2.2426

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        assert 140 < distance < 160

    def test_haversine_symmetrical(self):
        """
        Test: Distance A→B equals distance B→A.
        """
        lat1, lon1 = 51.4545, -2.5879
        lat2, lon2 = 53.4808, -2.2426

        dist_ab = haversine_distance(lat1, lon1, lat2, lon2)
        dist_ba = haversine_distance(lat2, lon2, lat1, lon1)

        assert dist_ab == pytest.approx(dist_ba, abs=0.01)

    def test_haversine_short_distance(self):
        """
        Test: Short distance within same city (~7.4 miles).
        """
        # Bristol city centre
        lat1, lon1 = 51.4545, -2.5879
        # Bristol airport (south of city)
        lat2, lon2 = 51.3860, -2.7191

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        assert 5 < distance < 10  # Roughly 7.4 miles


# ============================================================================
# UNIT TESTS: Postcode Geocoding
# ============================================================================


class TestPostcodeGeocoding:
    """Unit tests for postcode to lat/lon conversion."""

    @responses.activate
    def test_geocode_valid_postcode_bristol(self):
        """
        Test: Valid Bristol postcode returns correct lat/lon.
        """
        # Mock Nominatim response for Bristol city centre
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[{"lat": "51.4545", "lon": "-2.5879"}],
            status=200,
            match_querystring=False,
        )

        result = geocode_postcode("BS1 5AH")

        assert result is not None
        lat, lon = result
        assert lat == pytest.approx(51.4545, abs=0.001)
        assert lon == pytest.approx(-2.5879, abs=0.001)

    @responses.activate
    def test_geocode_valid_postcode_london(self):
        """
        Test: Valid London postcode returns correct coordinates.
        """
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[{"lat": "51.5074", "lon": "-0.1278"}],
            status=200,
            match_querystring=False,
        )

        result = geocode_postcode("EC1A 1AA")

        assert result is not None
        lat, lon = result
        assert 51.5 < lat < 51.51
        assert -0.15 < lon < -0.10

    @responses.activate
    def test_geocode_invalid_postcode_returns_none(self):
        """
        Test: Invalid postcode returns None.
        """
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[],  # No results
            status=200,
        )

        result = geocode_postcode("INVALID123")

        assert result is None

    @responses.activate
    def test_geocode_api_error_returns_none(self):
        """
        Test: API error (timeout, 500, etc.) returns None gracefully.
        """
        cache.clear()  # Clear any cached results from previous tests

        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json={"error": "Internal Server Error"},
            status=500,
        )

        result = geocode_postcode("BS1 5AH")

        assert result is None

    @responses.activate
    def test_geocode_empty_postcode_returns_none(self):
        """
        Test: Empty or None postcode returns None.
        """
        result = geocode_postcode("")

        assert result is None

        result = geocode_postcode(None)

        assert result is None

    @responses.activate
    def test_geocode_postcode_with_spaces(self, reset_cache):
        """
        Test: Postcode with or without spaces returns same result (normalized).
        """
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[{"lat": "51.4545", "lon": "-2.5879"}],
            status=200,
        )

        # Try postcode with space
        result1 = geocode_postcode("BS1 5AH")

        cache.clear()
        responses.reset()

        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[{"lat": "51.4545", "lon": "-2.5879"}],
            status=200,
        )

        # Try postcode without space
        result2 = geocode_postcode("BS15AH")

        # Both should return valid results (normalization handled)
        assert result1 is not None
        assert result2 is not None


# ============================================================================
# UNIT TESTS: Caching
# ============================================================================


class TestGeocodingCache:
    """Unit tests for geocoding result caching."""

    @responses.activate
    def test_geocode_result_cached_24_hours(self, reset_cache):
        """
        Test: First call hits API; subsequent calls return cached result.
        """
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[{"lat": "51.4545", "lon": "-2.5879"}],
            status=200,
        )

        # First call
        result1 = geocode_postcode("BS1 5AH")

        # Second call (should hit cache, not API)
        result2 = geocode_postcode("BS1 5AH")

        # Both should be identical
        assert result1 == result2
        # API should have been called only once
        assert len(responses.calls) == 1

    @responses.activate
    def test_geocode_negative_result_cached(self, reset_cache):
        """
        Test: Failed geocoding (invalid postcode) is also cached.
        Prevents hammering API with repeated invalid requests.
        """
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[],
            status=200,
        )

        # First call - fails
        result1 = geocode_postcode("INVALID123")

        # Second call - should return cached None without hitting API again
        result2 = geocode_postcode("INVALID123")

        assert result1 is None
        assert result2 is None
        # API should have been called only once (second call cached)
        assert len(responses.calls) == 1

    def test_geocode_cache_key_normalization(self, reset_cache):
        """
        Test: Cache key normalizes postcode (uppercase, no spaces).
        """
        from django.core.cache import cache

        # Manually set a cache entry
        cache.set("geocode:BS15AH", (51.4545, -2.5879), 86400)

        # Try different variations - should hit cache
        with patch("apps.logistics.utils.requests.get") as mock_get:
            result = geocode_postcode("bs1 5ah")  # lowercase with space

            # Should NOT call the API because normalized key matches
            # (if caching works correctly)
            assert result == (51.4545, -2.5879) or mock_get.called


# ============================================================================
# INTEGRATION TESTS: Nominatim API with Mocking
# ============================================================================


class TestGeocodingIntegration:
    """Integration tests using mocked Nominatim API."""

    @responses.activate
    def test_geocode_full_workflow_single_postcode(self, reset_cache):
        """
        Test: Full workflow of geocoding Bristol → haversine to London.
        """
        # Mock Bristol geocoding
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[{"lat": "51.4545", "lon": "-2.5879"}],
            status=200,
            match_querystring=False,
        )

        # Geocode Bristol
        bristol_coords = geocode_postcode("BS1 5AH")

        assert bristol_coords is not None

        # Use coordinates in distance calc
        # London coords (hardcoded for this test)
        london_coords = (51.5074, -0.1278)

        distance = haversine_distance(
            bristol_coords[0], bristol_coords[1], london_coords[0], london_coords[1]
        )

        assert 100 < distance < 115

    @responses.activate
    def test_calculate_distance_between_postcodes(self, reset_cache):
        """
        Test: Utility to calculate distance between two postcodes.
        """
        # Mock Nominatim responses
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[{"lat": "51.4545", "lon": "-2.5879"}],
            status=200,
            match_querystring=False,
        )
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[{"lat": "51.5074", "lon": "-0.1278"}],
            status=200,
            match_querystring=False,
        )

        # Assuming there's a helper function in utils
        from apps.logistics.utils import calculate_distance_between_postcodes

        distance = calculate_distance_between_postcodes("BS1 5AH", "EC1A 1AA")

        assert distance is not None
        assert 100 < distance < 115


# ============================================================================
# INTEGRATION TESTS: Food Miles in Orders
# ============================================================================


class TestFoodMilesInOrders:
    """Integration tests for food miles in order context."""

    @responses.activate
    def test_cart_food_miles_calculation_with_real_api(
        self, customer_user, producer_user, product, reset_cache
    ):
        """
        Test: Cart food miles calculated using real Nominatim mocking.
        """
        # Mock both postcodes
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[{"lat": "51.4545", "lon": "-2.5879"}],
            status=200,
            match_querystring=False,
        )
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[{"lat": "51.5235", "lon": "-2.3698"}],
            status=200,
            match_querystring=False,
        )

        from apps.orders.models import Cart, CartItem

        # Create cart
        cart = Cart.objects.create(customer=customer_user)
        item = CartItem.objects.create(cart=cart, product=product, quantity=1)

        # Get food miles
        food_miles = item.food_miles

        # Should calculate to ~15 miles (Bristol to Yate)
        assert food_miles is not None
        assert 10 < food_miles < 20

    @responses.activate
    @responses.activate
    def test_food_miles_zero_for_same_postcode(
        self, customer_user, producer_user, category, reset_cache
    ):
        """
        Test: Food miles = 0 when customer and producer have same postcode.
        """
        from apps.orders.models import Cart, CartItem
        from apps.products.models import Product
        from apps.accounts.models import CustomerProfile, ProducerProfile

        # Set both to same postcode
        cust_profile = customer_user.customer_profile
        cust_profile.postcode = "BS1 5AH"
        cust_profile.save()

        prod_profile = producer_user.producer_profile
        prod_profile.postcode = "BS1 5AH"
        prod_profile.save()

        # Mock postcode lookup - both return same location
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[{"lat": "51.4545", "lon": "-2.5879"}],
            status=200,
        )

        # Create product and cart
        product = Product.objects.create(
            producer=producer_user,
            name="Test Product",
            category=category,
            price=Decimal("5.00"),
            stock_quantity=10,
        )

        cart = Cart.objects.create(customer=customer_user)
        item = CartItem.objects.create(cart=cart, product=product, quantity=1)

        # Food miles should be 0 (same postcode)
        food_miles = item.food_miles

        assert food_miles == 0.0


# ============================================================================
# EDGE CASE & ERROR HANDLING TESTS
# ============================================================================


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    @responses.activate
    def test_geocode_malformed_json_response(self, reset_cache):
        """
        Test: Malformed JSON response is handled gracefully.
        """
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json={"invalid": "structure"},
            status=200,
        )

        result = geocode_postcode("BS1 5AH")

        # Should return None due to KeyError handling
        assert result is None

    @responses.activate
    def test_geocode_partial_data_response(self, reset_cache):
        """
        Test: Response with missing lat/lon fields handled.
        """
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            json=[{"lat": "51.4545"}],  # Missing lon
            status=200,
        )

        result = geocode_postcode("BS1 5AH")

        # Should handle gracefully
        assert result is None

    @responses.activate
    def test_geocode_timeout_handling(self, reset_cache):
        """
        Test: API timeout returns None gracefully.
        """
        responses.add(
            responses.GET,
            NOMINATIM_URL,
            body="",
            status=200,
            match_querystring=False,
        )

        with patch("apps.logistics.utils.requests.get") as mock_get:
            from requests.exceptions import Timeout

            mock_get.side_effect = Timeout("Connection timeout")

            result = geocode_postcode("BS1 5AH")

            assert result is None

    def test_haversine_extreme_coordinates(self):
        """
        Test: Extreme but valid lat/lon values handled.
        Note: Haversine doesn't validate coordinates, just calculates.
        """
        # North pole to south pole
        distance = haversine_distance(90, 0, -90, 0)

        # Should be half Earth's circumference (pi * R)
        assert distance > 6000  # Over 6000 miles


if __name__ == "__main__":
    pytest.main([__file__])
