from rest_framework import serializers
from .models import User, CustomerProfile, ProducerProfile


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ["delivery_address"]


class ProducerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProducerProfile
        fields = ["business_name", "business_address", "tax_id", "farm_origin"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    customer_profile = CustomerProfileSerializer(required=False)
    producer_profile = ProducerProfileSerializer(required=False)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "phone_number",
            "is_customer",
            "is_producer",
            "customer_profile",
            "producer_profile",
        ]

    def create(self, validated_data):
        customer_data = validated_data.pop("customer_profile", None)
        producer_data = validated_data.pop("producer_profile", None)
        password = validated_data.pop("password")

        # User
        user = User(**validated_data)
        user.set_password(password)  # hashed password
        user.save()

        # Profiles
        if user.is_customer and customer_data:
            CustomerProfile.objects.create(user=user, **customer_data)

        if user.is_producer and producer_data:
            ProducerProfile.objects.create(user=user, **producer_data)

        return user
