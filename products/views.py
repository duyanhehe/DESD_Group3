from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.db.models import Q
from django.db import transaction

from .models import Product
from .serializers import ProductSerializer


class CreateProductView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_producer:
            return Response({"error": "Only producers can create products"}, status=403)

        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(producer=request.user)
            return Response(
                {"message": "Product created successfully", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        today = now().date()

        products = Product.objects.filter(
            is_available=True, stock_quantity__gt=0
        ).filter(
            Q(available_from__isnull=True) | Q(available_from__lte=today),
            Q(available_to__isnull=True) | Q(available_to__gte=today),
        )

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id):
        today = now().date()

        product = get_object_or_404(
            Product.objects.filter(is_available=True, stock_quantity__gt=0).filter(
                Q(available_from__isnull=True) | Q(available_from__lte=today),
                Q(available_to__isnull=True) | Q(available_to__gte=today),
            ),
            id=id,
        )

        serializer = ProductSerializer(product)
        return Response(serializer.data)


class EditProductView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        product = get_object_or_404(Product, id=id)

        if not request.user.is_producer or product.producer != request.user:
            return Response({"error": "Unauthorized"}, status=403)

        serializer = ProductSerializer(product, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Product updated successfully", "data": serializer.data}
            )

        return Response(serializer.errors, status=400)


class DeleteProductView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        product = get_object_or_404(Product, id=id)

        if not request.user.is_producer or product.producer != request.user:
            return Response({"error": "Unauthorized"}, status=403)

        product.delete()
        return Response({"message": "Product deleted successfully"}, status=204)
