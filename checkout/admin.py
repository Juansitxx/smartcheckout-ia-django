from django.contrib import admin

from .models import Cart, CartItem, DetectionRun, Product, Sale, SaleItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("class_id", "class_name", "name", "sku", "price", "stock", "active")
    list_filter = ("active", "currency")
    search_fields = ("class_name", "name", "sku")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "subtotal", "total", "created_at")
    list_filter = ("status",)
    inlines = [CartItemInline]


@admin.register(DetectionRun)
class DetectionRunAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "total_detected", "inference_time_ms", "created_at")
    list_filter = ("status",)
    readonly_fields = ("detections_json",)


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "payment_method", "total", "created_at")
    list_filter = ("payment_method",)
    inlines = [SaleItemInline]
