import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-smart-checkout-local-dev")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "checkout",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SMART_MODEL_DIR = Path(os.getenv("SMART_MODEL_DIR", r"C:\Users\Juan\Desktop\ModeloDL"))
SMART_MODEL_PATH = Path(
    os.getenv("SMART_MODEL_PATH", str(SMART_MODEL_DIR / "models" / "YOLO" / "smart_checkout_model_small_v1.pt"))
)
SMART_PRODUCTS_PATH = Path(
    os.getenv("SMART_PRODUCTS_PATH", str(SMART_MODEL_DIR / "config" / "service" / "products.yaml"))
)
SMART_DEVICE = os.getenv("SMART_DEVICE", "cpu")
SMART_IMAGE_SIZE = int(os.getenv("SMART_IMAGE_SIZE", "640"))
SMART_CONFIDENCE = float(os.getenv("SMART_CONFIDENCE", "0.35"))
SMART_IOU = float(os.getenv("SMART_IOU", "0.45"))
SMART_MAX_DETECTIONS = int(os.getenv("SMART_MAX_DETECTIONS", "50"))
SMART_CLASS_AUTO_ADD_MIN_CONFIDENCE = {
    "gorra": float(os.getenv("SMART_GORRA_AUTO_ADD_CONFIDENCE", "1.01")),
}
