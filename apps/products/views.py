from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Product
from .serializers import ProductSerializer
from .forms import ProductForm

from django.db import transaction


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

        products = Product.objects.active()

        serializer = ProductSerializer(products, many=True, context={"request": request})
        return Response(serializer.data)


class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id):
        today = now().date()

        product = get_object_or_404(Product.objects.active(), id=id)

        serializer = ProductSerializer(product, context={"request": request})
        return Response(serializer.data)


class CategoryProductsView(APIView):
    def get(self, request, slug):
        today = now().date()

        products = Product.objects.active().filter(category__slug=slug)
        serializer = ProductSerializer(products, many=True, context={"request": request})
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


def product_list_page(request):
    return render(request, "products/list.html")


def product_detail_page(request, id):
    return render(request, "products/detail.html", {"product_id": id})


def search_results_page(request):
    return render(request, "products/search_results.html")


@login_required
def producer_dashboard(request):
    if not request.user.is_producer:
        messages.error(request, "Only producers can access the dashboard.")
        return redirect("/")

    products = Product.objects.filter(producer=request.user)
    return render(request, "products/producer_dashboard.html", {"products": products})

@login_required
def add_product(request):
    if not request.user.is_producer:
        messages.error(request, "Only producers can add products.")
        return redirect("/")

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.producer = request.user
            product.save()
            form.save_m2m()  # Important for allergens
            messages.success(request, f"Product '{product.name}' added successfully!")
            return redirect("producer_dashboard")
    else:
        form = ProductForm()

    return render(request, "products/add_product.html", {"form": form})


@login_required
def edit_product(request, id):
    product = get_object_or_404(Product, id=id)

    # Security: Ensure current producer owns this product
    if not request.user.is_producer or product.producer != request.user:
        messages.error(request, "Permission denied.")
        return redirect("producer_dashboard")

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect("producer_dashboard")
    else:
        form = ProductForm(instance=product)

    return render(
        request, "products/edit_product.html", {"form": form, "product": product}
    )


@login_required
def delete_product(request, id):
    product = get_object_or_404(Product, id=id)

    # Security: Ensure current producer owns this product
    if not request.user.is_producer or product.producer != request.user:
        messages.error(request, "Permission denied.")
        return redirect("producer_dashboard")

    if request.method == "POST":
        product_name = product.name
        product.delete()
        messages.success(request, f"Product '{product_name}' deleted successfully.")
        return redirect("producer_dashboard")

    return render(request, "products/delete_product_confirm.html", {"product": product})


class ProductSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.GET.get("q", "").strip()

        # Handle empty query
        if not query:
            return Response(
                {"message": "Please provide a search query.", "results": []}, status=200
            )

        # Search logic (partial and case insensitive)
        products = Product.objects.active().filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

        serializer = ProductSerializer(products, many=True, context={"request": request})

        # Handle no results
        if not products.exists():
            return Response(
                {"message": "No products found.", "results": []}, status=200
            )

        return Response(
            {"count": products.count(), "results": serializer.data}, status=200
        )
