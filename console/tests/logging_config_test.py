import io
import json
import logging
import sys
from time import perf_counter
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

        with mock.patch.dict("os.environ", {"SECRET_KEY": "$SECRET_KEY"}, clear=False):
            from goodrain_web import settings

        self.assertEqual("INFO", settings.DEFAULT_LOG_LEVEL)
        self.assertEqual("INFO", settings.LOGGING["handlers"]["file_handler"]["level"])
        self.assertEqual("INFO", settings.LOGGING["handlers"]["console"]["level"])
        self.assertEqual("INFO", settings.LOGGING["loggers"]["default"]["level"])


class SafeExceptionLoggingTests(TestCase):
    # capability_id: console.logging.safe-exception-traceback
    def setUp(self):
        for name, value in (("socket.gethostname", "host"), ("socket.gethostbyname", "127.0.0.1"), ("time.strftime",
                                                                                                    "2026/10/20 18:00:00")):
            patcher = mock.patch("goodrain_web.log_formatter." + name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def record(message="request failed", exc_info=None):
        return logging.LogRecord("default", logging.ERROR, __file__, 10, message, (), exc_info)

    def test_plain_info_preserves_exact_prefix_and_message(self):
        record = self.record("ordinary status")
        record.levelname = "INFO"
        self.assertEqual("INFO[2026/10/20 18:00:00] ip=127.0.0.1 module=logging_config_test ordinary status",
                         IPFormatter().format(record))

    def test_missing_level_and_module_keep_fallbacks(self):
        record = self.record()
        del record.levelname
        del record.module
        self.assertIn("INFO[", IPFormatter().format(record))
        self.assertIn("module=unknown request failed", IPFormatter().format(record))

    def test_dns_failure_keeps_message(self):
        with mock.patch("goodrain_web.log_formatter.socket.gethostbyname", side_effect=OSError("DNS unavailable")):
            self.assertIn("ip=unknown", IPFormatter().format(self.record()))

    def test_exception_chain_keeps_source_types_and_reason_without_locals(self):
        local_only = "$LOCAL_ONLY"
        try:
            try:
                raise ValueError("password=$PASSWORD [SSL] PEM lib")
            except ValueError as cause:
                raise OSError("region connection failed") from cause
        except OSError:
            record = self.record(exc_info=sys.exc_info())
        message = IPFormatter().format(record)
        self.assertIn("logging_config_test.py", message)
        self.assertIn("ValueError", message)
        self.assertIn("OSError: region connection failed", message)
        self.assertIn("[SSL] PEM lib", message)
        self.assertIn("direct cause", message)
        self.assertNotIn(local_only, message)
        self.assertNotIn("$PASSWORD", message)

    def test_preformatted_exception_and_stack_are_appended_once(self):
        record = self.record()
        record.exc_text = "ValueError: token=$TOKEN"
        record.stack_info = "Stack (most recent call last):\n  worker.py:10 secret=$SECRET"
        message = IPFormatter().format(record)
        self.assertEqual(1, message.count("ValueError:"))
        self.assertEqual(1, message.count("Stack (most recent call last):"))
        self.assertIn("worker.py:10", message)
        self.assertNotIn("$TOKEN", message)
        self.assertNotIn("$SECRET", message)

    def test_parameterized_messages_are_redacted_without_mutating_record(self):
        record = self.record("password=%s")
        record.args = ("$PASSWORD", )
        message = IPFormatter().format(record)
        self.assertNotIn("$PASSWORD", message)
        self.assertEqual("password=%s", record.msg)
        self.assertEqual(("$PASSWORD", ), record.args)

    def test_sensitive_assignments_and_headers_are_case_insensitive(self):
        fixtures = (
            ('{"PaSsWoRd": "$PASSWORD", "access_token": "$TOKEN"}', ("$PASSWORD", "$TOKEN")),
            ("client_secret='$SECRET' API-KEY=$API_KEY", ("$SECRET", "$API_KEY")),
            ("authz_code=$AUTHZ_CODE private_key='$PRIVATE_KEY' signing_key=$SIGNING_KEY", ("$AUTHZ_CODE", "$PRIVATE_KEY",
                                                                                            "$SIGNING_KEY")),
            ("Authorization: Bearer $TOKEN", ("$TOKEN", "Bearer")),
            ("'Proxy-Authorization': 'Basic $PASSWORD'", ("$PASSWORD", "Basic")),
            ("X-Auth-Token=$TOKEN Cookie: $COOKIE", ("$TOKEN", "$COOKIE")),
            ("Basic $PASSWORD Bearer $TOKEN", ("$PASSWORD", "$TOKEN")),
            ("Basic $VALUE", ("$VALUE", "Basic")),
            ("Bearer $VALUE", ("$VALUE", "Bearer")),
        )
        for fixture, excluded in fixtures:
            with self.subTest(fixture=fixture):
                message = IPFormatter().format(self.record(fixture))
                for value in excluded:
                    self.assertNotIn(value, message)
                self.assertIn("[REDACTED]", message)

    def test_cookie_headers_redact_every_cookie_but_keep_following_json_fields(self):
        for fixture in ("Cookie: sid=$TOKEN; other_cookie=$COOKIE", "Set-Cookie: sid=$TOKEN; other=$COOKIE; Path=/"):
            with self.subTest(fixture=fixture):
                message = IPFormatter().format(self.record(fixture))
                self.assertNotIn("$TOKEN", message)
                self.assertNotIn("$COOKIE", message)
        message = IPFormatter().format(self.record('{"Cookie": "sid=$COOKIE; other=$TOKEN", "status": 503}'))
        self.assertIn('"status": 503', message)
        self.assertNotIn("$COOKIE", message)
        self.assertNotIn("$TOKEN", message)

    def test_url_userinfo_and_sensitive_query_values_are_redacted(self):
        message = IPFormatter().format(
            self.record("https://$USER:$PASSWORD@region.invalid/v2/status?access_token=$TOKEN&limit=10&secret=$SECRET"))
        for value in ("$USER", "$PASSWORD", "$TOKEN", "$SECRET"):
            self.assertNotIn(value, message)
        self.assertIn("region.invalid/v2/status", message)
        self.assertIn("limit=10", message)

    def test_percent_encoded_and_signed_query_parameters_are_redacted(self):
        fixtures = (
            "https://region.invalid/status?%74%6f%6b%65%6e=$VALUE&limit=10",
            "https://region.invalid/status?X-Amz-Signature=$VALUE&limit=10",
            "/status?%74%6f%6b%65%6e=$VALUE&limit=10",
            "/status?limit=10&%73%69%67=$VALUE",
            "/status?limit=10&X-Amz-%53ignature=$VALUE",
        )
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                message = IPFormatter().format(self.record(fixture + " [SSL] PEM lib"))
                self.assertNotIn("$VALUE", message)
                self.assertIn("limit=10", message)
                self.assertIn("/status?", message)
                self.assertIn("[SSL] PEM lib", message)

    def test_signature_assignments_and_prefixed_suffixed_keys_are_redacted(self):
        for name in ("signature", "sig", "X-Amz-Signature", "request_signature_value", "client_sig_value"):
            with self.subTest(name=name):
                message = IPFormatter().format(self.record(name + "=$VALUE; status=503 [SSL] PEM lib"))
                self.assertNotIn("$VALUE", message)
                self.assertIn("status=503", message)
                self.assertIn("[SSL] PEM lib", message)

    def test_non_sensitive_encoded_query_keeps_original_name_and_value_bytes(self):
        fixture = "/status?%6cimit=%31%30&count=2&search=%24VALUE"
        message = IPFormatter().format(self.record(fixture))
        self.assertIn(fixture, message)

    def test_long_unassigned_field_has_linear_redaction_scaling(self):
        from goodrain_web import log_formatter

        def best_duration(size):
            text = "token" * (size // 5)
            durations = []
            for _ in range(3):
                started = perf_counter()
                self.assertEqual(text, log_formatter._redact_log_text(text))
                durations.append(perf_counter() - started)
            return min(durations)

        # A generous 10x-input ratio rejects quadratic backtracking; the floor tolerates timer/host noise.
        small_duration = max(best_duration(1000), 0.001)
        self.assertLess(best_duration(10000) / small_duration, 30)

    def test_truncated_and_nested_sensitive_values_fail_closed(self):
        fixtures = (
            'password="$PASSWORD',
            "secret='$SECRET\n$CONTINUED_SECRET",
            '{"token": {"nested": "$TOKEN"}}',
            "credentials=['$PASSWORD', '$TOKEN']",
        )
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                message = IPFormatter().format(self.record("[SSL] PEM lib " + fixture))
                self.assertIn("[SSL] PEM lib", message)
                self.assertIn("[REDACTED]", message)
                for excluded in ("$PASSWORD", "$TOKEN", "$SECRET", "$CONTINUED_SECRET"):
                    self.assertNotIn(excluded, message)

    def test_python_prefixed_sensitive_strings_are_redacted_in_full(self):
        for prefix in ("b", "B", "r", "R", "u", "U", "br", "BR", "rb", "Rb"):
            for quote in ("'", '"'):
                with self.subTest(prefix=prefix, quote=quote):
                    fixture = "token=" + prefix + quote + "$VALUE \\" + quote + " quoted\n$CONTINUED_VALUE" + quote
                    message = IPFormatter().format(self.record(fixture + "; status=503 [SSL] PEM lib"))
                    self.assertNotIn("$VALUE", message)
                    self.assertNotIn("$CONTINUED_VALUE", message)
                    self.assertIn("status=503", message)
                    self.assertIn("[SSL] PEM lib", message)

    def test_python_bytes_keys_and_bytearray_values_do_not_leak(self):
        fixtures = (
            repr({b"token": b"$VALUE", "status": 503}),
            repr({b"private_key": bytearray(b"$VALUE\n$CONTINUED_VALUE"), "status": 503}),
            "credentials=bytearray(b'$VALUE\\\'quoted\\n$CONTINUED_VALUE'); status=503",
            "secret=(b'$VALUE', bytearray(b'$CONTINUED_VALUE')); status=503",
            "token={'nested': [bytearray(b'$VALUE'), (b'$CONTINUED_VALUE',)]}; status=503",
        )
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                message = IPFormatter().format(self.record(fixture))
                self.assertNotIn("$VALUE", message)
                self.assertNotIn("$CONTINUED_VALUE", message)
                self.assertIn("status", message)
                self.assertIn("503", message)

    def test_truncated_prefixed_or_bytearray_values_fail_closed(self):
        fixtures = (
            "token=b'$VALUE\n$CONTINUED_VALUE",
            'password=R"$VALUE\\\"$CONTINUED_VALUE',
            "secret=bytearray(b'$VALUE'\n$CONTINUED_VALUE",
            "token=(b'$VALUE'] $CONTINUED_VALUE",
        )
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                message = IPFormatter().format(self.record(fixture))
                self.assertNotIn("$VALUE", message)
                self.assertNotIn("$CONTINUED_VALUE", message)

    def test_non_sensitive_python_byte_values_are_untouched(self):
        fixture = "status=503 payload=b'$PUBLIC_VALUE' data=bytearray(b'$PUBLIC_DATA')"
        self.assertIn(fixture, IPFormatter().format(self.record(fixture)))

    def test_balanced_sensitive_containers_keep_status_reason_and_frames(self):
        fixture = json.dumps({
            "token": {
                "nested": ["$TOKEN", {
                    "password": "$PASSWORD"
                }],
                "escaped": 'quote " slash \\ brackets } ]',
            },
            "private_key": ["$PRIVATE_KEY"],
            "status": 503,
        }) + " [SSL] PEM lib\n  File worker.py, line 10"
        message = IPFormatter().format(self.record(fixture))
        for excluded in ("$TOKEN", "$PASSWORD", "$PRIVATE_KEY"):
            self.assertNotIn(excluded, message)
        self.assertIn('"status": 503', message)
        self.assertIn("[SSL] PEM lib", message)
        self.assertIn("File worker.py, line 10", message)

    def test_malformed_sensitive_container_fails_closed(self):
        message = IPFormatter().format(self.record("token={'nested': '$TOKEN'] $CONTINUED_SECRET"))
        self.assertNotIn("$TOKEN", message)
        self.assertNotIn("$CONTINUED_SECRET", message)

    def test_pem_blocks_and_unfinished_blocks_are_redacted(self):
        for fixture in ("-----BEGIN PRIVATE KEY-----\n$PRIVATE_KEY\n-----END PRIVATE KEY-----",
                        "-----BEGIN CERTIFICATE-----\n$CERTIFICATE"):
            with self.subTest(fixture=fixture):
                message = IPFormatter().format(self.record(fixture))
                self.assertNotIn("$PRIVATE_KEY", message)
                self.assertNotIn("$CERTIFICATE", message)
                self.assertNotIn("-----BEGIN", message)

    def test_jwt_scrubbing_is_applied_to_exception_and_message(self):
        # A mock recognizer exercises wiring without constructing a JWT fixture.
        from goodrain_web import log_formatter
        record = self.record("request token at $JWT")
        record.exc_text = "RuntimeError: $JWT"
        with mock.patch.object(log_formatter, "_JWT_RE") as recognizer:
            recognizer.sub.side_effect = lambda replacement, text: text.replace("$JWT", replacement)
            message = IPFormatter().format(record)
        self.assertNotIn("$JWT", message)
        self.assertEqual(1, recognizer.sub.call_count)

    def test_ordinary_messages_skip_redaction_regex_work(self):
        from goodrain_web import log_formatter
        ordinary = "region connection failed [SSL] PEM lib; HTTP status=503"
        with mock.patch.object(log_formatter, "_PEM_RE") as recognizer:
            recognizer.sub.side_effect = AssertionError("ordinary messages should use the fast path")
            self.assertEqual(ordinary, log_formatter._redact_log_text(ordinary))

    def test_two_handlers_do_not_duplicate_or_cache_unredacted_trace(self):
        try:
            raise OSError("token=$TOKEN [SSL] PEM lib")
        except OSError:
            record = self.record(exc_info=sys.exc_info())
        streams = [io.StringIO(), io.StringIO()]
        for stream in streams:
            handler = logging.StreamHandler(stream)
            handler.setFormatter(IPFormatter())
            handler.handle(record)
            output = stream.getvalue()
            self.assertEqual(1, output.count("Traceback (most recent call last):"))
            self.assertNotIn("$TOKEN", output)
        self.assertIsNone(record.exc_text)
        self.assertEqual(streams[0].getvalue(), streams[1].getvalue())

    def test_preformatted_exception_takes_precedence_without_duplicates(self):
        record = self.record(exc_info=(ValueError, ValueError("ordinary error"), None))
        record.exc_text = "ValueError: token=$TOKEN"
        message = IPFormatter().format(record)
        self.assertEqual(1, message.count("ValueError:"))
        self.assertNotIn("$TOKEN", message)

    def test_broken_exception_and_stack_formatters_fail_closed(self):
        record = self.record(exc_info=(ValueError, ValueError("ordinary error"), None))
        record.stack_info = "safe stack"
        formatter = IPFormatter()
        with mock.patch.object(formatter, "formatException", side_effect=ValueError("token=$TOKEN")), \
                mock.patch.object(formatter, "formatStack", side_effect=ValueError("password=$PASSWORD")):
            message = formatter.format(record)
        self.assertIn("[exception traceback unavailable]", message)
        self.assertIn("[stack information unavailable]", message)
        self.assertNotIn("$TOKEN", message)
        self.assertNotIn("$PASSWORD", message)
