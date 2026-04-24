from rest_framework import serializers
from .models import User, CustomerProfile, ProducerProfile


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ["delivery_address", "postcode"]


class ProducerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProducerProfile
        fields = ["business_name", "business_address", "tax_id", "farm_origin", "postcode"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
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
        password = validated_data.pop("password", None)

        # User
        user = User(**validated_data)
        if password:
            user.set_password(password)  # hashed password
        user.save()

        # Profiles
        if user.is_customer and customer_data:
            CustomerProfile.objects.create(user=user, **customer_data)

        if user.is_producer and producer_data:
            ProducerProfile.objects.create(user=user, **producer_data)

        return user

    def update(self, instance, validated_data):
        customer_data = validated_data.pop("customer_profile", None)
        producer_data = validated_data.pop("producer_profile", None)
        password = validated_data.pop("password", None)

        # Update basic user fields
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.phone_number = validated_data.get("phone_number", instance.phone_number)
        
        if password:
            instance.set_password(password)
        instance.save()

        # Update or create profiles
        if instance.is_customer and customer_data is not None:
            profile, _ = CustomerProfile.objects.get_or_create(user=instance)
            profile.delivery_address = customer_data.get("delivery_address", profile.delivery_address)
            profile.postcode = customer_data.get("postcode", profile.postcode)
            profile.save()

        if instance.is_producer and producer_data is not None:
            profile, _ = ProducerProfile.objects.get_or_create(user=instance)
            profile.business_name = producer_data.get("business_name", profile.business_name)
            profile.business_address = producer_data.get("business_address", profile.business_address)
            profile.tax_id = producer_data.get("tax_id", profile.tax_id)
            profile.farm_origin = producer_data.get("farm_origin", profile.farm_origin)
            profile.postcode = producer_data.get("postcode", profile.postcode)
            profile.save()

        return instance
