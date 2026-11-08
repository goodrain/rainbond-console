"""Small delivery job runner using existing region MQ executors and persistent task state."""
import logging
import threading
from django.db import close_old_connections

logger = logging.getLogger("default")
_guard = threading.Lock()
_started = False


def start_delivery_worker():
    global _started
    with _guard:
        if _started:
            return
        _started = True
        threading.Thread(target=run_delivery_worker, name="delivery-jobs", daemon=True).start()


def run_delivery_worker():
    from console.services.delivery_templates import DeliveryService
    service = DeliveryService()
    pause = threading.Event()
    while True:
        close_old_connections()
        try:
            ids = list(
                service.m.DeliveryTask.objects.filter(status__in=["queued", "running"]).order_by("created_at").values_list(
                    "id", flat=True)[:50])
            for task_id in ids:
                service.advance(task_id)
        except Exception:
            # Migrations may not have been applied when the process starts. No task payloads in logs.
            logger.warning("delivery job runner waiting for database or region availability")
        close_old_connections()
        pause.wait(2)
