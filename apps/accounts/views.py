from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, logout, login as auth_login
from django.shortcuts import render, redirect
from django.db.models import Q
from .models import User
from .serializers import UserRegistrationSerializer


class RegistrationView(generics.CreateAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Log the user in for session-based auth (templates)
        auth_login(request, user)

        # Generate token
        token, created = Token.objects.get_or_create(user=user)

        return Response(
            {
                "message": "User registered successfully",
                "user_id": user.id,
                "token": token.key,
                "role": "customer" if user.is_customer else "producer",
            },
            status=status.HTTP_201_CREATED,
        )


def login_page(request):
    if request.user.is_authenticated:
        return redirect("/")
    return render(request, "accounts/login.html")


def register_page(request):
    if request.user.is_authenticated:
        return redirect("/")
    return render(request, "accounts/register.html")


class LoginView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

    def post(self, request):
        login_input = request.data.get("username")  # This could be username or email
        password = request.data.get("password")

        # Basic server-side validation
        if not login_input or not password:
            return Response(
                {"error": "Please provide both credentials."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Resolve username if email was provided
        user_obj = User.objects.filter(Q(username=login_input) | Q(email=login_input)).first()
        username = user_obj.username if user_obj else login_input

        user = authenticate(request, username=username, password=password)

        if user:
            # Log the user in for session-based auth (templates)
            auth_login(request, user)
            
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "message": "Login successful",
                    "token": token.key,
                    "role": "customer" if user.is_customer else "producer",
                }
            )
        else:
            return Response(
                {"error": "Invalid email/username or password."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )


class LogoutView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if request.user.is_authenticated:
            if hasattr(request.user, "auth_token"):
                request.user.auth_token.delete()
            logout(request)
        return Response({"message": "Logout successful"})


def logout_view(request):
    if request.method == "POST":
        if request.user.is_authenticated:
            # Try to delete token if exists
            try:
                if hasattr(request.user, "auth_token"):
                    request.user.auth_token.delete()
            except:
                pass
            logout(request)
    return redirect("login_page")


class UserProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserRegistrationSerializer

    def get_object(self):
        return self.request.user
