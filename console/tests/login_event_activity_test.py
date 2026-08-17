# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import django
from django.test import SimpleTestCase

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")
django.setup()

from console.login.login_event import LoginEvent  # noqa: E402
from console.repositories.login_event import LoginEventRepo  # noqa: E402


class LoginEventActivityTests(SimpleTestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 10, 12, 0, 0)
        self.user = SimpleNamespace(username="demo", enterprise_id="enterprise-id")
        self.event = SimpleNamespace(
            pk=7,
            login_time=self.now - timedelta(hours=1),
            last_active_time=self.now - timedelta(seconds=10),
            logout_time=None,
        )
        self.repo = Mock()
        self.repo.get_last_one.return_value = self.event

    @patch("console.login.login_event.datetime")
    @patch("console.login.login_event.LoginEventModel.objects")
    def test_active_skips_database_write_inside_throttle_window(self, objects, mocked_datetime):
        mocked_datetime.now.return_value = self.now

        LoginEvent(self.user, self.repo).active()

        objects.filter.assert_not_called()

    @patch("console.login.login_event.LoginEventModel.objects")
    def test_active_without_login_event_does_not_write(self, objects):
        self.repo.get_last_one.return_value = None

        LoginEvent(self.user, self.repo).active()

        objects.filter.assert_not_called()

    @patch("console.login.login_event.logger")
    def test_logout_without_login_event_is_ignored(self, logger):
        self.repo.get_last_one.return_value = None

        LoginEvent(self.user, self.repo).logout()

        logger.warning.assert_called_once_with("no login event. username: demo")

    @patch("console.login.login_event.datetime")
    @patch("console.login.login_event.LoginEventModel.objects")
    def test_active_conditionally_updates_only_activity_fields_after_throttle_window(self, objects, mocked_datetime):
        mocked_datetime.now.return_value = self.now
        self.event.last_active_time = self.now - timedelta(seconds=61)
        candidates = Mock()
        stale_candidates = Mock()
        objects.filter.return_value = candidates
        candidates.filter.return_value = stale_candidates
        stale_candidates.update.return_value = 1

        LoginEvent(self.user, self.repo).active()

        objects.filter.assert_called_once_with(pk=self.event.pk)
        candidates.filter.assert_called_once()
        stale_candidates.update.assert_called_once_with(last_active_time=self.now, duration=3600)

    @patch("console.login.login_event.datetime")
    @patch("console.login.login_event.LoginEventModel.objects")
    def test_logout_forces_activity_and_logout_time_update(self, objects, mocked_datetime):
        mocked_datetime.now.return_value = self.now
        candidates = Mock()
        objects.filter.return_value = candidates
        candidates.update.return_value = 1

        LoginEvent(self.user, self.repo).logout()

        objects.filter.assert_called_once_with(pk=self.event.pk)
        candidates.filter.assert_not_called()
        candidates.update.assert_called_once_with(
            last_active_time=self.now,
            duration=3600,
            logout_time=self.now,
        )

    @patch("console.login.login_event.datetime")
    @patch("console.login.login_event.make_uuid", return_value="event-id")
    def test_login_creates_new_activity_event(self, make_uuid, mocked_datetime):
        mocked_datetime.now.return_value = self.now

        LoginEvent(self.user, self.repo).login()

        make_uuid.assert_called_once_with()
        self.repo.create.assert_called_once()
        created = self.repo.create.call_args.kwargs
        self.assertEqual(created["event_id"], "event-id")
        self.assertEqual(created["last_active_time"], "2026-08-10 12:00:00")


class LoginEventRepoTests(SimpleTestCase):
    @patch("console.repositories.login_event.LoginEvent.objects")
    def test_get_last_one_fetches_only_first_matching_event(self, objects):
        event = object()
        events = Mock()
        ordered_events = Mock()
        objects.filter.return_value = events
        events.order_by.return_value = ordered_events
        ordered_events.first.return_value = event

        result = LoginEventRepo.get_last_one("enterprise-id", "demo")

        self.assertIs(result, event)
        objects.filter.assert_called_once_with(enterprise_id="enterprise-id", username="demo")
        events.order_by.assert_called_once_with("-ID")
        ordered_events.first.assert_called_once_with()
