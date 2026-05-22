# Smart Checkout IA Django

Aplicacion Django para usar un modelo YOLO como una caja registradora con IA.

## Flujo principal

1. El usuario sube una imagen de productos.
2. Django guarda la imagen original.
3. El modulo `checkout.ai` carga el modelo YOLO y ejecuta inferencia.
4. Se guarda una imagen procesada con cajas dibujadas.
5. Las detecciones se cruzan con el catalogo de productos.
6. En la vista `Caja Live`, cada producto nuevo detectado por camara se agrega automaticamente al carrito.
7. El usuario confirma la venta.
8. La venta queda en SQLite y se refleja en el dashboard.


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

## Uso en Codespaces o Linux

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Notas:

- El proyecto ya no depende de OpenCV para arrancar en entornos headless.
- Si vas a ejecutar la IA, configura `SMART_MODEL_PATH` y `SMART_PRODUCTS_PATH` con rutas validas dentro del Codespace.
- Si necesitas hosts personalizados, define `DJANGO_ALLOWED_HOSTS` separado por comas.

