from django.urls import path
from .views import (
    # template views
    cart_page,
    order_success_page,
    producer_orders_page,
    order_history_page,
    # cart
    CartDetailView,
    AddToCartView,
    UpdateCartItemView,
    RemoveCartItemView,
    ClearCartView,
    # orders (customer)
    CreateOrderView,
    CustomerOrderListView,
    CustomerOrderDetailView,
    UpdateOrderStatusView,
    OrderStatusHistoryView,
    ReorderView,
    # orders (producer)
    ProducerOrderListView,
    ProducerOrderDetailView,
    # refunds
    CustomerRefundRequestView,
    AdminRefundReviewView,
    AdminRefundListView,
    AdminRefundReviewPageView,
)

app_name = "orders"

urlpatterns = [
    # -- Template Views --
    path("cart/", cart_page, name="cart_page"),
    path("success/", order_success_page, name="order_success_page"),
    path("history/", order_history_page, name="order_history_page"),
    path("producer/", producer_orders_page, name="producer_orders_page"),
    path("admin/refunds/", AdminRefundReviewPageView.as_view(), name="admin_refunds_page"),

    # -- Cart --
    path("api/v1/cart/", CartDetailView.as_view(), name="cart_detail"),
    path("api/v1/cart/add/", AddToCartView.as_view(), name="cart_add"),
    path("api/v1/cart/item/<int:item_id>/", UpdateCartItemView.as_view(), name="cart_update_item"),
    path("api/v1/cart/item/<int:item_id>/remove/", RemoveCartItemView.as_view(), name="cart_remove_item"),
    path("api/v1/cart/clear/", ClearCartView.as_view(), name="cart_clear"),

    # -- Orders (customer) --
    path("api/v1/", CustomerOrderListView.as_view(), name="order_list"),
    path("api/v1/create/", CreateOrderView.as_view(), name="order_create"),
    path("api/v1/<int:order_id>/", CustomerOrderDetailView.as_view(), name="order_detail"),
    path("api/v1/<int:order_id>/status/", UpdateOrderStatusView.as_view(), name="order_update_status"),
    path("api/v1/<int:order_id>/history/", OrderStatusHistoryView.as_view(), name="order_status_history"),
    path("api/v1/<int:order_id>/reorder/", ReorderView.as_view(), name="order_reorder"),

    # -- Orders (producer) --
    path("api/v1/producer/", ProducerOrderListView.as_view(), name="producer_order_list"),
    path("api/v1/producer/<int:order_id>/", ProducerOrderDetailView.as_view(), name="producer_order_detail"),

    # -- Refunds --
    path("api/v1/refund/request/", CustomerRefundRequestView.as_view(), name="refund_request"),
    path("api/v1/refund/review/list/", AdminRefundListView.as_view(), name="refund_review_list"),
    path("api/v1/refund/review/<int:refund_id>/", AdminRefundReviewView.as_view(), name="refund_review"),
]
