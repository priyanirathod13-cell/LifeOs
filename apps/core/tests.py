from django.test import TestCase, Client
from django.urls import reverse


class HealthCheckTests(TestCase):
    """
    Test suite for the LifeOS core health-check endpoint.
    """

    def setUp(self):
        self.client = Client()

    def test_health_check_status_code(self):
        """GET /health/ should return HTTP 200 OK."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)

    def test_health_check_response_payload(self):
        """GET /health/ should return the expected JSON structure."""
        response = self.client.get('/health/')
        self.assertEqual(response.json(), {
            "status": "ok",
            "application": "LifeOS"
        })

    def test_health_check_reverse_url(self):
        """Reversing 'core:health_check' resolves to '/health/'."""
        url = reverse('core:health_check')
        self.assertEqual(url, '/health/')
