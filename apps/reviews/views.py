from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import GoogleReviewsResponseSerializer, WriteReviewUrlSerializer
from .services.google_reviews import GoogleReviewsService


class GoogleReviewsAPIView(APIView):
    """
    GET /api/v1/reviews/google/

    Retrieves Google Reviews, overall rating statistics, and direct write-review link.
    Supports caching (24h) and optional parameters:
    - ?limit=5 (1-20)
    - ?refresh=true (bypasses cache)
    """

    def get(self, request, *args, **kwargs):
        # Parse query params
        raw_limit = request.query_params.get("limit", "5")
        try:
            limit = int(raw_limit)
            limit = max(1, min(limit, 20))
        except (ValueError, TypeError):
            limit = 5

        raw_refresh = request.query_params.get("refresh", "false").lower()
        force_refresh = raw_refresh in ("true", "1", "yes")

        service = GoogleReviewsService()
        data = service.get_reviews(limit=limit, force_refresh=force_refresh)

        serializer = GoogleReviewsResponseSerializer(data)
        return Response(
            {
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class GoogleReviewWriteUrlAPIView(APIView):
    """
    GET /api/v1/reviews/google/write-url/

    Returns the direct Google URL for customers to post a review for Bevingshulp Noord.
    """

    def get(self, request, *args, **kwargs):
        service = GoogleReviewsService()
        payload = {
            "status": "success",
            "write_review_url": service.write_review_url,
            "google_maps_url": service.google_maps_url,
            "place_id": service.place_id,
            "cid": service.cid,
        }
        serializer = WriteReviewUrlSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)
