import signal
from types import SimpleNamespace
from unittest import TestCase, mock

from console.services.app_config.extend_service import AppExtendService


class AppExtendServiceTests(TestCase):
    def test_get_app_extend_method_builds_node_list_with_positive_step(self):
        service = SimpleNamespace(extend_method="stateless_multiple")
        extend_method = SimpleNamespace(
            min_node=2,
            max_node=9,
            step_node=3,
            max_memory=256,
        )

        with mock.patch("console.services.app_config.extend_service.extend_repo.get_extend_method_by_service",
                        return_value=extend_method):
            node_list, memory_list = AppExtendService().get_app_extend_method(service)

        self.assertEqual([2, 5, 8], node_list)
        self.assertEqual(["32", "64", "128", "256"], memory_list)

    def test_get_app_extend_method_handles_zero_node_step(self):
        service = SimpleNamespace(extend_method="daemonset")
        extend_method = SimpleNamespace(
            min_node=0,
            max_node=0,
            step_node=0,
            max_memory=65536,
        )

        def fail_on_timeout(signum, frame):
            raise TimeoutError("node list generation did not terminate")

        previous_handler = signal.signal(signal.SIGALRM, fail_on_timeout)
        signal.setitimer(signal.ITIMER_REAL, 1)
        try:
            with mock.patch("console.services.app_config.extend_service.extend_repo.get_extend_method_by_service",
                            return_value=extend_method):
                node_list, _ = AppExtendService().get_app_extend_method(service)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)

        self.assertEqual([0], node_list)
