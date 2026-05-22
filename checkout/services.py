from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .ai import get_detector
from .models import Cart, CartItem, DetectionRun, Product, Sale, SaleItem


DEFAULT_CLASS_IDS = {
    "caja cereal": 0,
    "cepillo dental": 1,
    "gafas": 2,
    "gorra": 3,
    "manzana roja": 4,
    "papel higienico": 5,
    "papel higienico.": 5,
    "soda": 6,
    "zanahoria": 7,
}

COP_PRODUCT_DEFAULTS = {
    "caja cereal": {"name": "Caja de cereal", "price": Decimal("14500"), "currency": "COP"},
    "cepillo dental": {"name": "Cepillo dental", "price": Decimal("5500"), "currency": "COP"},
    "gafas": {"name": "Gafas", "price": Decimal("25000"), "currency": "COP"},
    "gorra": {"name": "Gorra", "price": Decimal("30000"), "currency": "COP"},
    "manzana roja": {"name": "Manzana roja", "price": Decimal("1800"), "currency": "COP"},
    "papel higienico": {"name": "Papel higienico", "price": Decimal("12000"), "currency": "COP"},
    "soda": {"name": "Soda", "price": Decimal("3500"), "currency": "COP"},
    "zanahoria": {"name": "Zanahoria", "price": Decimal("1200"), "currency": "COP"},
}


def normalize_name(value):
    return str(value or "").lower().strip()


def analyze_detection_run(run: DetectionRun) -> Cart:
    original_path = Path(run.image_original.path)
    processed_name = f"processed_{run.pk}_{original_path.stem}.jpg"
    processed_path = Path(settings.MEDIA_ROOT) / "processed" / processed_name

    try:
        result = get_detector().predict_image(original_path, processed_path)
    except Exception as exc:
        run.status = DetectionRun.STATUS_ERROR
        run.error_message = str(exc)
        run.save(update_fields=["status", "error_message"])
        raise

    detections = result["detections"]
    run.image_processed.name = f"processed/{processed_name}"
    run.status = DetectionRun.STATUS_DONE
    run.detections_json = detections
    run.inference_time_ms = result["inference_time_ms"]
    run.total_detected = len(detections)
    run.save(
        update_fields=[
            "image_processed",
            "status",
            "detections_json",
            "inference_time_ms",
            "total_detected",
        ]
    )
    return create_cart_from_detections(run, detections)


@transaction.atomic
def create_cart_from_detections(run: DetectionRun, detections: list[dict]) -> Cart:
    cart = Cart.objects.create(detection_run=run)
    grouped = {}

    for detection in detections:
        product = find_product_for_detection(detection)
        if product is None:
            continue
        key = product.pk
        if key not in grouped:
            grouped[key] = {
                "product": product,
                "quantity": 0,
                "confidence": 0,
                "bbox": detection.get("bbox_xyxy") or detection.get("bbox_norm") or [],
            }
        grouped[key]["quantity"] += 1
        grouped[key]["confidence"] = max(grouped[key]["confidence"], float(detection.get("confidence", 0)))

    for item in grouped.values():
        CartItem.objects.create(
            cart=cart,
            product=item["product"],
            quantity=item["quantity"],
            unit_price=item["product"].price,
            confidence=item["confidence"],
            bbox={"box": item["bbox"]},
        )

    cart.recalculate()
    return cart


def find_product_for_detection(detection: dict) -> Product | None:
    class_id = detection.get("class_id")
    class_name = normalize_name(detection.get("class_name"))

    product = None
    if class_id is not None:
        product = Product.objects.filter(class_id=class_id, active=True).first()
    if product is None and class_name:
        product = Product.objects.filter(class_name__iexact=class_name, active=True).first()
    return product


def serialize_detection_for_live(detection: dict) -> dict:
    product = find_product_for_detection(detection)
    class_name = normalize_name(detection.get("class_name"))
    confidence = float(detection.get("confidence", 0) or 0)
    auto_add_min_confidence = getattr(settings, "SMART_CLASS_AUTO_ADD_MIN_CONFIDENCE", {}).get(class_name, 0)
    auto_add_allowed = confidence >= auto_add_min_confidence
    payload = {
        "class_id": detection.get("class_id"),
        "class_name": detection.get("class_name"),
        "confidence": confidence,
        "bbox": detection.get("bbox_xyxy") or [],
        "bbox_norm": detection.get("bbox_norm") or [],
        "product": None,
        "auto_add": auto_add_allowed,
        "auto_add_reason": "" if auto_add_allowed else "Requiere confirmacion por posible falso positivo.",
    }
    if product:
        payload["product"] = {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "price": float(product.price),
            "currency": product.currency,
            "stock": product.stock,
        }
    return payload


@transaction.atomic
def confirm_cart(cart: Cart, payment_method: str) -> Sale:
    if cart.status == Cart.STATUS_CONFIRMED:
        return cart.sale
    if not cart.items.exists():
        raise ValueError("El carrito no tiene productos para confirmar.")

    sale = Sale.objects.create(cart=cart, payment_method=payment_method, total=cart.total)
    for item in cart.items.select_related("product"):
        SaleItem.objects.create(
            sale=sale,
            product=item.product,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.line_total,
        )
        item.product.stock = max(0, item.product.stock - item.quantity)
        item.product.save(update_fields=["stock", "updated_at"])

    cart.status = Cart.STATUS_CONFIRMED
    cart.save(update_fields=["status", "updated_at"])
    return sale


@transaction.atomic
def create_live_sale(items: list[dict], payment_method: str) -> Sale:
    if not items:
        raise ValueError("No hay productos para confirmar.")

    cart = Cart.objects.create()
    for raw in items:
        product_id = int(raw.get("product_id"))
        quantity = int(raw.get("quantity", 1))
        if quantity <= 0:
            raise ValueError("La cantidad debe ser mayor a cero.")

        product = Product.objects.select_for_update().filter(pk=product_id, active=True).first()
        if product is None:
            raise ValueError(f"Producto no disponible: {product_id}")

        existing = CartItem.objects.filter(cart=cart, product=product).first()
        if existing:
            existing.quantity += quantity
            existing.save()
        else:
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
                unit_price=product.price,
                confidence=float(raw.get("confidence", 0) or 0),
                bbox={"box": raw.get("bbox") or []},
            )

    cart.recalculate()
    return confirm_cart(cart, normalize_payment_method(payment_method))


def normalize_payment_method(value: str) -> str:
    normalized = normalize_name(value)
    mapping = {
        "efectivo": Sale.PAYMENT_CASH,
        "cash": Sale.PAYMENT_CASH,
        "tarjeta": Sale.PAYMENT_CARD,
        "card": Sale.PAYMENT_CARD,
        "transferencia": Sale.PAYMENT_TRANSFER,
        "transfer": Sale.PAYMENT_TRANSFER,
    }
    return mapping.get(normalized, Sale.PAYMENT_CASH)


def load_products_from_yaml(path: Path | None = None) -> int:
    import yaml

    configured_catalog_path = Path(path or settings.SMART_PRODUCTS_PATH)
    fallback_catalog_path = Path(getattr(settings, "BUNDLED_PRODUCTS_PATH", configured_catalog_path))
    catalog_path = configured_catalog_path
    if path is None and not catalog_path.exists() and fallback_catalog_path.exists():
        catalog_path = fallback_catalog_path

    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalogo no encontrado: {catalog_path}")

    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    currency = "COP"
    products = data.get("products", {}) or {}
    created_or_updated = 0

    for index, (class_name, info) in enumerate(products.items()):
        normalized = normalize_name(class_name)
        class_id = DEFAULT_CLASS_IDS.get(normalized, index)
        cop_defaults = COP_PRODUCT_DEFAULTS.get(normalized, {})
        defaults = {
            "class_name": normalized,
            "name": cop_defaults.get("name") or info.get("name") or class_name.title(),
            "sku": info.get("sku") or f"SKU-{class_id:03d}",
            "description": info.get("description", ""),
            "price": cop_defaults.get("price") or Decimal(str(info.get("price", "0"))),
            "currency": cop_defaults.get("currency") or currency,
            "stock": 50,
            "active": True,
        }
        Product.objects.update_or_create(class_id=class_id, defaults=defaults)
        created_or_updated += 1

    return created_or_updated
