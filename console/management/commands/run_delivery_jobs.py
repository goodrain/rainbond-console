"""Run persistent delivery jobs independently of web requests."""
from django.core.management.base import BaseCommand
from console.services.delivery_worker import run_delivery_worker


class Command(BaseCommand):
    help = "Resume and process application delivery jobs using the existing region executors"

    def handle(self, *args, **options):
        run_delivery_worker()
