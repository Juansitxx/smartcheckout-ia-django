# Smart Checkout IA Django

Aplicacion Django para usar el modelo de `C:\Users\Juan\Desktop\ModeloDL` como una caja registradora con IA.

## Flujo principal

1. El usuario sube una imagen de productos.
2. Django guarda la imagen original.
3. El modulo `checkout.ai` carga el modelo YOLO de ModeloDL y ejecuta inferencia.
4. Se guarda una imagen procesada con cajas dibujadas.
5. Las detecciones se cruzan con el catalogo de productos.
6. En la vista `Caja Live`, cada producto nuevo detectado por camara se agrega automaticamente al carrito.
7. El usuario confirma la venta.
8. La venta queda en SQLite y se refleja en el dashboard.

## Arquitectura

- `core/`: configuracion Django.
- `checkout/models.py`: productos, ejecuciones IA, carritos y ventas.
- `checkout/ai.py`: adaptador del modelo YOLO.
- `checkout/services.py`: reglas de negocio del checkout.
- `checkout/views.py`: vistas web function-based.
- `checkout/templates/checkout/`: interfaz web.
- `checkout/management/commands/seed_products.py`: carga catalogo desde ModeloDL.

## Modelo usado

Por defecto:

```text
C:\Users\Juan\Desktop\ModeloDL\models\YOLO\smart_checkout_model_small_v1.pt
```

Catalogo:

```text
C:\Users\Juan\Desktop\ModeloDL\config\service\products.yaml
```

Puedes cambiarlo con variables de entorno:

```powershell
$env:SMART_MODEL_PATH="C:\Users\Juan\Desktop\ModeloDL\models\YOLO\smart_checkout_model_small_v1.pt"
$env:SMART_DEVICE="cpu"
```

## Instalacion en Windows

```powershell
cd C:\Users\Juan\Desktop\smart_checkout_ia_django
setup_windows.cmd
runserver_windows.cmd
```

Abrir:

```text
http://127.0.0.1:8000/
```

## Comandos manuales

```powershell
cd C:\Users\Juan\Desktop\smart_checkout_ia_django
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py makemigrations
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_products
.\.venv\Scripts\python.exe manage.py runserver
```

## Pruebas

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

## Notas tecnicas

- La app no copia los pesos del modelo; los referencia desde `ModeloDL`.
- YOLO solo se carga cuando se analiza una imagen.
- Si el modelo no existe o falla una dependencia, la ejecucion queda marcada como error y la app sigue funcionando.
- La vista principal de caja en vivo esta en `/live/`.
- El catalogo usa pesos colombianos (`COP`).
