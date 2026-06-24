import logging
import sys
from unittest import TestCase, mock

from goodrain_web.log_formatter import IPFormatter


class LoggingConfigTests(TestCase):
    # capability_id: console.logging.default-no-debug-noise
    def test_ip_formatter_uses_record_level_name(self):
        record = logging.LogRecord(
            name="default",
            level=logging.WARNING,
            pathname=__file__,
            lineno=10,
            msg="important warning",
            args=(),
            exc_info=None,
        )
        record.module = "logging_config_test"

        with mock.patch("goodrain_web.log_formatter.socket.gethostname", return_value="host"), \
                mock.patch("goodrain_web.log_formatter.socket.gethostbyname", return_value="127.0.0.1"), \
                mock.patch("goodrain_web.log_formatter.time.strftime", return_value="2026/06/23 23:30:00"):
            message = IPFormatter().format(record)

        self.assertTrue(message.startswith("WARNING[2026/06/23 23:30:00]"))
        self.assertIn("module=logging_config_test important warning", message)

    # capability_id: console.logging.default-no-debug-noise
    def test_default_logger_level_defaults_to_info(self):
        sys.modules.pop("goodrain_web.settings", None)

        with mock.patch.dict("os.environ", {"SECRET_KEY": "test-secret"}, clear=False):
            from goodrain_web import settings

        self.assertEqual("INFO", settings.DEFAULT_LOG_LEVEL)
        self.assertEqual("INFO", settings.LOGGING["handlers"]["file_handler"]["level"])
        self.assertEqual("INFO", settings.LOGGING["handlers"]["console"]["level"])
        self.assertEqual("INFO", settings.LOGGING["loggers"]["default"]["level"])
