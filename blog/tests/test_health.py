from unittest import mock

from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse


class HealthTests(TestCase):
    def test_live_returns_ok(self):
        resp = self.client.get(reverse("livez"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

    def test_live_does_not_access_database(self):
        with mock.patch("core.health.connection.cursor") as mock_cursor:
            resp = self.client.get(reverse("livez"))
        self.assertEqual(resp.status_code, 200)
        mock_cursor.assert_not_called()

    def test_ready_returns_ready_when_db_up(self):
        resp = self.client.get(reverse("readyz"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ready")

    def test_ready_returns_503_when_db_down(self):
        with mock.patch("core.health.connection.cursor", side_effect=OperationalError("db down")):
            resp = self.client.get(reverse("readyz"))
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["status"], "unavailable")
