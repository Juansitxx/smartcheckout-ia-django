from django.core.management.base import BaseCommand

from checkout.services import load_products_from_yaml


class Command(BaseCommand):
    help = "Carga o actualiza el catalogo inicial desde ModeloDL/products.yaml."

    def add_arguments(self, parser):
        parser.add_argument("--path", default=None, help="Ruta opcional al products.yaml")

    def handle(self, *args, **options):
        total = load_products_from_yaml(options["path"])
        self.stdout.write(self.style.SUCCESS(f"Catalogo actualizado: {total} productos"))
