from unittest import mock

from django.test import TestCase


class HealthTests(TestCase):
    def test_live_returns_ok(self):
        resp = self.client.get("/health/live")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

    def test_ready_returns_ready_when_db_up(self):
        resp = self.client.get("/health/ready")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ready")

    def test_ready_returns_503_when_db_down(self):
        with mock.patch("core.health.connection.cursor", side_effect=Exception("db down")):
            resp = self.client.get("/health/ready")
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["status"], "unavailable")
