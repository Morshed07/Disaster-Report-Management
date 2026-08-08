from unittest.mock import patch, MagicMock
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.reviews.services.google_reviews import GoogleReviewsService, DEFAULT_FALLBACK_REVIEWS


class GoogleReviewsAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.reviews_url = reverse("google-reviews")
        self.write_url = reverse("google-reviews-write-url")
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_get_write_review_url_endpoint(self):
        """Test GET /api/v1/reviews/google/write-url/"""
        response = self.client.get(self.write_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("placeid=ChIJZZtq0ms1x0cRlnzKtwRxopo", data["write_review_url"])
        self.assertIn("cid=10062953288126758038", data["google_maps_url"])
        self.assertEqual(data["place_id"], "ChIJZZtq0ms1x0cRlnzKtwRxopo")
        self.assertEqual(data["cid"], "10062953288126758038")

    def test_get_google_reviews_fallback(self):
        """Test GET /api/v1/reviews/google/ when no API key is set (fallback mode)."""
        response = self.client.get(self.reviews_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_json = response.json()
        self.assertEqual(res_json["status"], "success")
        
        data = res_json["data"]
        self.assertEqual(data["place_id"], "ChIJZZtq0ms1x0cRlnzKtwRxopo")
        self.assertEqual(data["cid"], "10062953288126758038")
        self.assertEqual(data["name"], "Bevingshulp Noord")
        self.assertEqual(data["source"], "fallback")
        self.assertEqual(len(data["reviews"]), 5)

    def test_get_google_reviews_limit(self):
        """Test limit parameter on /api/v1/reviews/google/?limit=2."""
        response = self.client.get(self.reviews_url, {"limit": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(len(data["reviews"]), 2)

    def test_get_google_reviews_caching(self):
        """Test that subsequent requests use cached data."""
        # Initial request sets cache
        res1 = self.client.get(self.reviews_url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertFalse(res1.json()["data"]["cached"])

        # Second request hits cache
        res2 = self.client.get(self.reviews_url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.json()["data"]["cached"])

    def test_get_google_reviews_force_refresh(self):
        """Test ?refresh=true invalidates cache and fetches fresh data."""
        # Warm cache
        self.client.get(self.reviews_url)

        # Request with refresh=true
        res = self.client.get(self.reviews_url, {"refresh": "true"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.json()["data"]["cached"])

    @override_settings(GOOGLE_PLACES_API_KEY="test_api_key")
    @patch("requests.get")
    def test_google_places_api_integration_success(self, mock_requests_get):
        """Test live API fetch when GOOGLE_PLACES_API_KEY is configured."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "OK",
            "result": {
                "name": "Bevingshulp Noord",
                "rating": 5.0,
                "user_ratings_total": 42,
                "reviews": [
                    {
                        "author_name": "Test Reviewer",
                        "rating": 5,
                        "relative_time_description": "2 days ago",
                        "text": "Great service!",
                        "time": 1723000000,
                    }
                ],
            },
        }
        mock_requests_get.return_value = mock_response

        response = self.client.get(self.reviews_url, {"refresh": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]

        self.assertEqual(data["source"], "google_places_api")
        self.assertEqual(data["rating"], 5.0)
        self.assertEqual(data["user_ratings_total"], 42)
        self.assertEqual(len(data["reviews"]), 1)
        self.assertEqual(data["reviews"][0]["author_name"], "Test Reviewer")

    @override_settings(GOOGLE_PLACES_API_KEY="test_api_key")
    @patch("requests.get")
    def test_google_places_api_failure_fallback(self, mock_requests_get):
        """Test fallback when Google Places API throws exception."""
        mock_requests_get.side_effect = Exception("API connection failed")

        response = self.client.get(self.reviews_url, {"refresh": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]

        self.assertEqual(data["source"], "fallback")
        self.assertEqual(len(data["reviews"]), 5)
