"""Small delivery job runner using existing region MQ executors and persistent task state."""
import logging
import threading
from django.db import close_old_connections

logger = logging.getLogger("default")
_guard = threading.Lock()
_started = False
_vm_started = False


def start_delivery_worker():
    global _started
    with _guard:
        if _started:
            return
        _started = True
        threading.Thread(target=run_delivery_worker, name="delivery-jobs", daemon=True).start()


def run_delivery_worker():
    global _vm_started
    with _guard:
        if not _vm_started:
            _vm_started = True
            threading.Thread(target=run_vm_delivery_worker, name='vm-delivery-jobs', daemon=True).start()
    from console.services.delivery_templates import DeliveryService
    service = DeliveryService()
    pause = threading.Event()
    while True:
        close_old_connections()
        try:
            ids = list(
                service.m.DeliveryTask.objects.filter(status__in=["queued", "running"]).exclude(
                    kind='vm_prepare').order_by("created_at").values_list("id", flat=True)[:50])
            for task_id in ids:
                service.advance(task_id)
        except Exception:
            # Migrations may not have been applied when the process starts. No task payloads in logs.
            logger.warning("delivery job runner waiting for database or region availability")
        close_old_connections()
        pause.wait(2)


def run_vm_delivery_worker():
    """VM control polling cannot delay ordinary delivery or publication jobs."""
    from console.services.delivery_templates import DeliveryService
    service = DeliveryService()
    pause = threading.Event()
    while True:
        close_old_connections()
        try:
            task = service.m.DeliveryTask.objects.filter(kind='vm_prepare',
                                                         status__in=['queued', 'running']).order_by('updated_at').first()
            if task:
                service.advance(task.id)
        except Exception:
            logger.warning('VM delivery runner waiting for database or region availability')
        close_old_connections()
        pause.wait(2)
