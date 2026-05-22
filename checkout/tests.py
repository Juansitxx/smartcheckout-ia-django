from decimal import Decimal

from django.test import TestCase, override_settings

from .models import Cart, CartItem, Product
from .services import serialize_detection_for_live


class CartTests(TestCase):
    def test_cart_recalculate(self):
        product = Product.objects.create(
            class_id=1,
            class_name="soda",
            name="Soda",
            sku="DRI-SOD-001",
            price=Decimal("3500"),
            stock=10,
        )
        cart = Cart.objects.create()
        CartItem.objects.create(cart=cart, product=product, quantity=2, unit_price=product.price)

        cart.recalculate()

        self.assertEqual(cart.total, Decimal("7000"))


class LiveDetectionSerializationTests(TestCase):
    def test_gorra_requires_high_confidence_for_auto_add(self):
        Product.objects.create(
            class_id=3,
            class_name="gorra",
            name="Gorra",
            sku="ACC-GOR-001",
            price=Decimal("30000"),
            stock=10,
        )

        with override_settings(SMART_CLASS_AUTO_ADD_MIN_CONFIDENCE={"gorra": 0.90}):
            detection = serialize_detection_for_live(
                {
                    "class_id": 3,
                    "class_name": "gorra",
                    "confidence": 0.72,
                    "bbox_xyxy": [10, 10, 80, 80],
                }
            )

        self.assertFalse(detection["auto_add"])
        self.assertEqual(detection["product"]["name"], "Gorra")
