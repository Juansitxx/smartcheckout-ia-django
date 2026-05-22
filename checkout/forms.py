from django import forms

from .models import Product, Sale


class ImageUploadForm(forms.Form):
    image = forms.ImageField(
        label="Imagen de productos",
        help_text="Sube una foto de los productos sobre la caja.",
    )


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["class_id", "class_name", "name", "sku", "description", "price", "currency", "stock", "active"]


class SaleConfirmForm(forms.Form):
    payment_method = forms.ChoiceField(
        label="Metodo de pago",
        choices=Sale.PAYMENT_CHOICES,
        initial=Sale.PAYMENT_CASH,
    )
