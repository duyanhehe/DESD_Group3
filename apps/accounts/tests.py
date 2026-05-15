import pytest
from django.contrib.auth import authenticate, get_user_model

from apps.accounts.models import CustomerProfile, ProducerProfile

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_tc001_producer_can_create_account_and_authenticate():
    user = User.objects.create_user(
        username="jane.smith@bristolvalleyfarm.com",
        email="jane.smith@bristolvalleyfarm.com",
        password="SecurePass123!",
        first_name="Jane",
        last_name="Smith",
        phone_number="01179 123456",
        is_customer=False,
        is_producer=True,
    )
    ProducerProfile.objects.create(
        user=user,
        business_name="Bristol Valley Farm",
        business_address="Bristol, BS1 4DJ",
        postcode="BS1 4DJ",
        farm_origin="Bristol Valley Farm",
    )

    assert user.check_password("SecurePass123!")
    assert user.password != "SecurePass123!"
    assert user.is_producer is True
    assert user.is_customer is False
    assert user.producer_profile.business_name == "Bristol Valley Farm"
    assert (
        authenticate(
            username="jane.smith@bristolvalleyfarm.com",
            password="SecurePass123!",
        )
        == user
    )


def test_tc002_customer_can_register_with_delivery_details_and_authenticate():
    user = User.objects.create_user(
        username="robert.johnson@email.com",
        email="robert.johnson@email.com",
        password="SecurePass123!",
        first_name="Robert",
        last_name="Johnson",
        phone_number="07700 900123",
        is_customer=True,
        is_producer=False,
    )
    CustomerProfile.objects.create(
        user=user,
        delivery_address="45 Park Street, Bristol",
        postcode="BS1 5JG",
    )

    assert user.is_customer is True
    assert user.is_producer is False
    assert user.customer_profile.delivery_address == "45 Park Street, Bristol"
    assert user.customer_profile.postcode == "BS1 5JG"
    assert (
        authenticate(username="robert.johnson@email.com", password="SecurePass123!")
        == user
    )


def test_tc022_secure_authentication_rejects_bad_credentials_and_roles_are_enforced(
    customer_user, producer_user
):
    assert (
        authenticate(username=customer_user.username, password="wrong-password") is None
    )
    assert (
        authenticate(username="missing@example.com", password="SecurePass123!") is None
    )
    assert customer_user.is_customer is True
    assert customer_user.is_producer is False
    assert producer_user.is_producer is True
    assert producer_user.is_customer is False
