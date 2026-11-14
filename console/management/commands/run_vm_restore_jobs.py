from django.core.management.base import BaseCommand
from console.services.vm_restore_worker import run_worker


class Command(BaseCommand):
    help = 'Resume durable VM jobs under the Main process supervisor'

    def handle(self, *args, **options):
        run_worker()
