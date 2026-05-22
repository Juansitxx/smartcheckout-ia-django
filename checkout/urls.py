from django.urls import path

from . import views


app_name = "checkout"

urlpatterns = [
    path("", views.home, name="home"),
    path("live/", views.live, name="live"),
    path("analizar/", views.analyze_image, name="analyze"),
    path("resultado/<int:pk>/", views.result, name="result"),
    path("carrito/<int:cart_id>/confirmar/", views.confirm_sale, name="confirm_sale"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("productos/", views.products, name="products"),
    path("productos/<int:pk>/editar/", views.product_edit, name="product_edit"),
    path("ventas/", views.sales, name="sales"),
    path("ventas/<int:pk>/", views.sale_detail, name="sale_detail"),
    path("api/detect-frame/", views.detect_frame_api, name="detect_frame_api"),
    path("api/confirm-live-sale/", views.confirm_live_sale_api, name="confirm_live_sale_api"),
    path("api/sales-history/", views.sales_history_api, name="sales_history_api"),
]
