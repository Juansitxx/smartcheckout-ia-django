from io import BytesIO
from decimal import Decimal

from django.test import TestCase, override_settings
from PIL import Image

from .ai import SmartCheckoutDetector
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


class DetectorImageDecodingTests(TestCase):
    def test_predict_jpeg_bytes_without_opencv(self):
        detector = SmartCheckoutDetector()
        detector.model = FakeYOLOModel()

        image = Image.new("RGB", (12, 8), color="white")
        buffer = BytesIO()
        image.save(buffer, format="JPEG")

        result = detector.predict_jpeg_bytes(buffer.getvalue())

        self.assertEqual(result["frame_width"], 12)
        self.assertEqual(result["frame_height"], 8)
        self.assertEqual(len(result["detections"]), 1)
        self.assertEqual(result["detections"][0]["class_name"], "soda")


class FakeYOLOModel:
    def predict(self, frame, **kwargs):
        return [FakeYOLOResult()]


class FakeYOLOResult:
    names = {0: "soda"}
    boxes = []

    def __init__(self):
        self.boxes = [FakeYOLOBox()]


class FakeYOLOBox:
    cls = [0]
    conf = [0.91]
    xyxy = []
    xywhn = []

    def __init__(self):
        self.xyxy = [FakeTensor([1.0, 1.0, 10.0, 6.0])]
        self.xywhn = [FakeTensor([0.45, 0.5, 0.75, 0.625])]


class FakeTensor:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return self._values
