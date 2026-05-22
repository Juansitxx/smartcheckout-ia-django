import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(BASE_DIR / ".env")


def get_csv_env(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def is_windows_absolute_path(value: str) -> bool:
    return len(value) >= 3 and value[0].isalpha() and value[1] == ":" and value[2] in ("\\", "/")


def resolve_path_value(value: str | None, default: Path, base_dir: Path, platform_name: str | None = None) -> Path:
    platform_name = platform_name or os.name
    if not value:
        return default.resolve()
    if platform_name != "nt" and is_windows_absolute_path(value):
        return default.resolve()

    path = Path(value)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def get_path_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    path = resolve_path_value(value, default, BASE_DIR)
    return path

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-smart-checkout-local-dev")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = get_csv_env("DJANGO_ALLOWED_HOSTS", ["127.0.0.1", "localhost", ".app.github.dev", ".github.dev"])

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

BUNDLED_MODEL_DIR = BASE_DIR / "model_assets"
BUNDLED_MODEL_PATH = BUNDLED_MODEL_DIR / "models" / "YOLO" / "smart_checkout_model_small_v1.pt"
BUNDLED_PRODUCTS_PATH = BUNDLED_MODEL_DIR / "config" / "service" / "products.yaml"

SMART_MODEL_DIR = get_path_env("SMART_MODEL_DIR", BUNDLED_MODEL_DIR)
SMART_MODEL_PATH = get_path_env(
    "SMART_MODEL_PATH", BUNDLED_MODEL_PATH
)
SMART_PRODUCTS_PATH = get_path_env(
    "SMART_PRODUCTS_PATH", BUNDLED_PRODUCTS_PATH
)
SMART_DEVICE = os.getenv("SMART_DEVICE", "cpu")
SMART_IMAGE_SIZE = int(os.getenv("SMART_IMAGE_SIZE", "640"))
SMART_CONFIDENCE = float(os.getenv("SMART_CONFIDENCE", "0.35"))
SMART_IOU = float(os.getenv("SMART_IOU", "0.45"))
SMART_MAX_DETECTIONS = int(os.getenv("SMART_MAX_DETECTIONS", "50"))
SMART_CLASS_AUTO_ADD_MIN_CONFIDENCE = {
    "gorra": float(os.getenv("SMART_GORRA_AUTO_ADD_CONFIDENCE", "1.01")),
}
