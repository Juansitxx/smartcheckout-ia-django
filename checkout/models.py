from decimal import Decimal

from django.db import models
from django.urls import reverse


class Product(models.Model):
    class_id = models.PositiveIntegerField(unique=True)
    class_name = models.CharField(max_length=120, unique=True, db_index=True)
    name = models.CharField(max_length=160)
    sku = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=12, default="COP")
    stock = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["class_id"]

    def __str__(self):
        return f"{self.name} ({self.class_name})"


class DetectionRun(models.Model):
    STATUS_PENDING = "pending"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendiente"),
        (STATUS_DONE, "Procesado"),
        (STATUS_ERROR, "Error"),
    ]

    image_original = models.ImageField(upload_to="uploads/")
    image_processed = models.ImageField(upload_to="processed/", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    detections_json = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    inference_time_ms = models.FloatField(default=0)
    total_detected = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def get_absolute_url(self):
        return reverse("checkout:result", args=[self.pk])


class Cart(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Borrador"),
        (STATUS_CONFIRMED, "Confirmado"),
        (STATUS_CANCELLED, "Cancelado"),
    ]

    detection_run = models.OneToOneField(
        DetectionRun,
        related_name="cart",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def recalculate(self):
        subtotal = sum((item.line_total for item in self.items.all()), Decimal("0.00"))
        self.subtotal = subtotal
        self.tax = Decimal("0.00")
        self.total = self.subtotal + self.tax
        self.save(update_fields=["subtotal", "tax", "total", "updated_at"])

    def __str__(self):
        return f"Cart #{self.pk} - {self.status}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="cart_items", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    confidence = models.FloatField(default=0)
    bbox = models.JSONField(default=dict, blank=True)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("cart", "product")
        ordering = ["product__name"]

    def save(self, *args, **kwargs):
        self.line_total = Decimal(self.quantity) * self.unit_price
        super().save(*args, **kwargs)


class Sale(models.Model):
    PAYMENT_CASH = "cash"
    PAYMENT_CARD = "card"
    PAYMENT_TRANSFER = "transfer"
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, "Efectivo"),
        (PAYMENT_CARD, "Tarjeta"),
        (PAYMENT_TRANSFER, "Transferencia"),
    ]

    cart = models.OneToOneField(Cart, related_name="sale", on_delete=models.PROTECT)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_CASH)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sale #{self.pk} - {self.total}"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="sale_items", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["product__name"]
