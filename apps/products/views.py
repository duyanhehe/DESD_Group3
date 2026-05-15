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

from .models import Product, Recipe, FarmStory, Review
from apps.orders.models import OrderItem
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
        products = Product.objects.active()

        # TC-014: Organic filter
        is_organic = request.GET.get("is_organic")
        if is_organic == "true":
            products = products.filter(is_organic=True)
        elif is_organic == "false":
            products = products.filter(is_organic=False)

        # TC-019: Surplus filter
        is_surplus = request.GET.get("is_surplus")
        if is_surplus == "true":
            products = products.filter(is_surplus=True)

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
    low_stock_alerts = [p for p in products if p.stock_quantity <= p.low_stock_threshold]
    
    return render(request, "products/producer_dashboard.html", {
        "products": products,
        "low_stock_alerts": low_stock_alerts
    })

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
        products = Product.objects.active()
        
        # Build search filters
        search_filter = (
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(producer__producer_profile__business_name__icontains=query) |
            Q(category__name__icontains=query)
        )
        
        # If the search includes "organic", also match products marked as organic
        if 'organic' in query.lower():
            search_filter |= Q(is_organic=True)
            
        products = products.filter(search_filter)

        # TC-014: Add filters to search as well
        is_organic = request.GET.get("is_organic")
        if is_organic == "true":
            products = products.filter(is_organic=True)
            
        is_surplus = request.GET.get("is_surplus")
        if is_surplus == "true":
            products = products.filter(is_surplus=True)

        serializer = ProductSerializer(products, many=True, context={"request": request})

        # Handle no results
        if not products.exists():
            return Response(
                {"message": "No products found.", "results": []}, status=200
            )

        return Response(
            {"count": products.count(), "results": serializer.data}, status=200
        )

@login_required
def education_list_page(request):
    """TC-020: Education & Story listing page."""
    from .models import Recipe, FarmStory
    recipes = Recipe.objects.all().order_by("-created_at")
    stories = FarmStory.objects.all().order_by("-created_at")
    return render(request, "products/education.html", {
        "recipes": recipes,
        "stories": stories
    })

@login_required
def add_recipe(request):
    if not request.user.is_producer:
        messages.error(request, "Only producers can add recipes.")
        return redirect("/")

    from .forms import RecipeForm
    if request.method == "POST":
        form = RecipeForm(request.POST, request.FILES, producer=request.user)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.producer = request.user
            recipe.save()
            form.save_m2m()
            messages.success(request, f"Recipe '{recipe.title}' added successfully!")
            return redirect("education_page")
    else:
        form = RecipeForm(producer=request.user)

    return render(request, "products/add_content.html", {"form": form, "title": "Add Recipe"})

@login_required
def add_story(request):
    if not request.user.is_producer:
        messages.error(request, "Only producers can add farm stories.")
        return redirect("/")

    from .forms import FarmStoryForm
    if request.method == "POST":
        form = FarmStoryForm(request.POST, request.FILES, producer=request.user)
        if form.is_valid():
            story = form.save(commit=False)
            story.producer = request.user
            story.save()
            form.save_m2m()
            messages.success(request, f"Farm Story '{story.title}' added successfully!")
            return redirect("education_page")
    else:
        form = FarmStoryForm(producer=request.user)

    return render(request, "products/add_content.html", {"form": form, "title": "Add Farm Story"})

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_review(request, product_id):
    """TC-024: Add review logic."""
    from .models import Product, Review
    from apps.orders.models import Order
    
    product = get_object_or_404(Product, id=product_id)
    rating = request.data.get("rating")
    comment = request.data.get("comment")
    
    if not rating or not comment:
        return Response({"error": "Rating and comment are required."}, status=400)
    
    # Check if user has bought this item (allow any non-cancelled/refunded order for testing/reviewing)
    from apps.orders.models import OrderItem, Order
    has_bought = OrderItem.objects.filter(
        order__customer=request.user,
        product=product
    ).exclude(
        order__status__in=[Order.CANCELLED, Order.REFUNDED, Order.REFUND_REQUESTED]
    ).exists()
    
    if not has_bought:
        return Response({"error": "You can only review items you have successfully purchased."}, status=403)
        
    # Check if they already reviewed
    if Review.objects.filter(product=product, customer=request.user).exists():
        return Response({"error": "You have already reviewed this product."}, status=400)
        
    Review.objects.create(
        product=product,
        customer=request.user,
        rating=rating,
        comment=comment
    )
    return Response({"message": "Review submitted successfully!"}, status=201)
