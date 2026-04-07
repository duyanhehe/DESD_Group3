from django.urls import path
from .views import (
    RegistrationView,
    LoginView,
    LogoutView,
    logout_view,
    UserProfileView,
    login_page,
    register_page,
)

urlpatterns = [
    # Template Views
    path("login/", login_page, name="login_page"),
    path("register/", register_page, name="register_page"),
    # API Views
    path("api/v1/register/", RegistrationView.as_view(), name="api_register"),
    path("api/v1/login/", LoginView.as_view(), name="api_login"),
    path("api/v1/logout/", LogoutView.as_view(), name="api_logout"),
    path("logout/", logout_view, name="logout"),
    path("api/v1/profile/", UserProfileView.as_view(), name="api_profile"),
]
