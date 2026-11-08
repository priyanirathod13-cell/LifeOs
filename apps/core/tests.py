from django.test import TestCase, Client
from django.urls import reverse


class CoreAndDesignSystemTests(TestCase):
    """
    Test suite for LifeOS core endpoints, navigation routes, and Design System templates.
    """

    def setUp(self):
        self.client = Client()

    def test_health_check_status_code(self):
        """GET /health/ must return HTTP 200 OK (Step 01 preservation)."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)

    def test_health_check_response_payload(self):
        """GET /health/ must return the exact expected JSON structure."""
        response = self.client.get('/health/')
        self.assertEqual(response.json(), {
            "status": "ok",
            "application": "LifeOS"
        })

    def test_dashboard_view(self):
        """GET / must render the dashboard template and app layout."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/dashboard.html')
        self.assertTemplateUsed(response, 'layouts/app_layout.html')
        self.assertTemplateUsed(response, 'components/sidebar.html')
        self.assertTemplateUsed(response, 'components/header.html')
        self.assertContains(response, 'Behavioral Dashboard')
        self.assertContains(response, 'Daily Focus Index')

    def test_ui_system_showcase_view(self):
        """GET /ui-system/ must render the design system demonstration page."""
        response = self.client.get('/ui-system/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/ui_system.html')
        self.assertTemplateUsed(response, 'layouts/app_layout.html')
        self.assertContains(response, 'LifeOS Design System')
        self.assertContains(response, 'Primary Action')
        self.assertContains(response, 'sampleModal')

    def test_sidebar_navigation_routes_exist_and_succeed(self):
        """Verify that every single sidebar navigation link returns HTTP 200 (no 404s)."""
        nav_routes = [
            'core:dashboard',
            'core:ui_system',
            'core:timetable',
            'core:routines',
            'core:tasks',
            'core:habits',
            'core:activities',
            'core:checkin',
            'core:study',
            'core:goals',
            'core:projects',
            'core:journal',
            'core:decisions',
            'core:mistakes',
            'core:productivity_analytics',
            'core:study_analytics',
            'core:behavioral_insights',
            'core:financial_analytics',
            'core:recommendations',
            'core:settings',
        ]

        for route_name in nav_routes:
            url = reverse(route_name)
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 200,
                f"Expected route '{route_name}' ({url}) to return 200 OK, got {response.status_code}"
            )
