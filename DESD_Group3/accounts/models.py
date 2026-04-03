from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    is_customer = models.BooleanField(default=True)
    is_producer = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    delivery_address = models.TextField(blank=True, null=True)

class ProducerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='producer_profile')
    business_name = models.CharField(max_length=255)
    business_address = models.TextField()
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    farm_origin = models.CharField(max_length=255, blank=True, null=True)