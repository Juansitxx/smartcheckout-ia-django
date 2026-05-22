import base64
import json

from django.contrib import messages
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .forms import ImageUploadForm, ProductForm, SaleConfirmForm
from .models import Cart, DetectionRun, Product, Sale
from .ai import get_detector
from .services import analyze_detection_run, confirm_cart, create_live_sale, serialize_detection_for_live


def home(request):
    form = ImageUploadForm()
    recent_runs = DetectionRun.objects.select_related("cart").all()[:5]
    return render(request, "checkout/home.html", {"form": form, "recent_runs": recent_runs})


def live(request):
    return render(request, "checkout/live.html")


def analyze_image(request):
    if request.method != "POST":
        return redirect("checkout:home")

    form = ImageUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "La imagen enviada no es valida.")
        return render(request, "checkout/home.html", {"form": form})

    run = DetectionRun.objects.create(image_original=form.cleaned_data["image"])
    try:
        cart = analyze_detection_run(run)
    except Exception as exc:
        messages.error(request, f"No se pudo ejecutar la IA: {exc}")
        return redirect(run.get_absolute_url())

    if not cart.items.exists():
        messages.warning(request, "La IA no encontro productos activos del catalogo en la imagen.")
    return redirect(run.get_absolute_url())


def result(request, pk):
    run = get_object_or_404(DetectionRun, pk=pk)
    cart = getattr(run, "cart", None)
    form = SaleConfirmForm()
    return render(request, "checkout/result.html", {"run": run, "cart": cart, "form": form})


def confirm_sale(request, cart_id):
    cart = get_object_or_404(Cart.objects.prefetch_related("items__product"), pk=cart_id)
    if request.method != "POST":
        return redirect("checkout:result", pk=cart.detection_run_id)

    form = SaleConfirmForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Metodo de pago no valido.")
        return redirect("checkout:result", pk=cart.detection_run_id)

    try:
        sale = confirm_cart(cart, form.cleaned_data["payment_method"])
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("checkout:result", pk=cart.detection_run_id)

    messages.success(request, f"Venta #{sale.pk} confirmada correctamente.")
    return redirect("checkout:sale_detail", pk=sale.pk)


def dashboard(request):
    sales_total = Sale.objects.aggregate(total=Sum("total"))["total"] or 0
    context = {
        "products_count": Product.objects.count(),
        "active_products": Product.objects.filter(active=True).count(),
        "runs_count": DetectionRun.objects.count(),
        "detections_count": DetectionRun.objects.aggregate(total=Sum("total_detected"))["total"] or 0,
        "sales_count": Sale.objects.count(),
        "sales_total": sales_total,
        "recent_sales": Sale.objects.prefetch_related("items__product")[:5],
        "recent_runs": DetectionRun.objects.all()[:8],
        "top_products": (
            Product.objects.annotate(sold_units=Sum("sale_items__quantity"))
            .filter(sold_units__isnull=False)
            .order_by("-sold_units")[:5]
        ),
        "run_statuses": DetectionRun.objects.values("status").annotate(total=Count("id")).order_by("status"),
    }
    return render(request, "checkout/dashboard.html", context)


def products(request):
    items = Product.objects.all()
    return render(request, "checkout/products.html", {"products": items})


def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto actualizado.")
            return redirect("checkout:products")
    else:
        form = ProductForm(instance=product)
    return render(request, "checkout/product_form.html", {"form": form, "product": product})


def sales(request):
    items = Sale.objects.prefetch_related("items__product").all()
    return render(request, "checkout/sales.html", {"sales": items})


def sale_detail(request, pk):
    sale = get_object_or_404(Sale.objects.prefetch_related("items__product"), pk=pk)
    return render(request, "checkout/sale_detail.html", {"sale": sale})


@csrf_exempt
@require_POST
def detect_frame_api(request):
    try:
        payload = json.loads(request.body or "{}")
        image_data = payload.get("image", "")
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]
        image_bytes = base64.b64decode(image_data)
        result = get_detector().predict_jpeg_bytes(image_bytes)
        detections = [serialize_detection_for_live(item) for item in result["detections"]]
        return JsonResponse(
            {
                "success": True,
                "detections": detections,
                "latency_ms": result["inference_time_ms"],
                "frame_width": result["frame_width"],
                "frame_height": result["frame_height"],
            }
        )
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


@csrf_exempt
@require_POST
def confirm_live_sale_api(request):
    try:
        payload = json.loads(request.body or "{}")
        sale = create_live_sale(payload.get("items", []), payload.get("payment_method", "cash"))
        return JsonResponse(
            {
                "success": True,
                "message": "Venta registrada correctamente",
                "sale": serialize_sale(sale),
            }
        )
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


@require_GET
def sales_history_api(request):
    sales_qs = Sale.objects.prefetch_related("items__product").all()[:20]
    return JsonResponse({"success": True, "sales": [serialize_sale(sale) for sale in sales_qs]})


def serialize_sale(sale: Sale) -> dict:
    first_item = next(iter(sale.items.all()), None)
    currency = first_item.product.currency if first_item else "COP"
    return {
        "id": sale.id,
        "payment_method": sale.get_payment_method_display(),
        "total": float(sale.total),
        "currency": currency,
        "created_at": sale.created_at.isoformat(),
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "line_total": float(item.line_total),
                "currency": item.product.currency,
            }
            for item in sale.items.all()
        ],
    }
