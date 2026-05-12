"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView


def home(request):
    return render(request, "index.html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("products/", include("apps.products.urls")),
    path("orders/", include("apps.orders.urls")),
    path("categories/", include("apps.categories.urls")),
    path("payments/", include("apps.payments.urls")),
    path("ai/", include("apps.ai_engine.urls")),
    
    # Static Info Pages
    path("about/", TemplateView.as_view(template_name="info/about.html"), name="about"),
    path("producer-terms/", TemplateView.as_view(template_name="info/producer_terms.html"), name="producer_terms"),
    path("privacy/", TemplateView.as_view(template_name="info/privacy.html"), name="privacy"),
    path("help/", TemplateView.as_view(template_name="info/help.html"), name="help"),
    path("contact/", TemplateView.as_view(template_name="info/contact.html"), name="contact"),
    path("seasonal-box/", TemplateView.as_view(template_name="info/seasonal_box.html"), name="seasonal_box"),
    path("gift-cards/", TemplateView.as_view(template_name="info/gift_cards.html"), name="gift_cards"),
    path("ethics/", TemplateView.as_view(template_name="info/ethics.html"), name="ethics"),
    
    path("", home, name="home"),
]

# Serve media files in development (heatmaps, uploaded images, etc.)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
