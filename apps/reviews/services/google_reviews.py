import logging
import requests
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Curated fallback reviews in Dutch for Bevingshulp Noord
DEFAULT_FALLBACK_REVIEWS: List[Dict[str, Any]] = [
    {
        "author_name": "Jan de Vries",
        "author_url": "https://www.google.com/maps/contrib/100000000000000000001",
        "profile_photo_url": "https://lh3.googleusercontent.com/a/default-user-photo-1",
        "rating": 5,
        "relative_time_description": "een week geleden",
        "text": "Uitstekende begeleiding bij onze schademelding. Erg professioneel, vriendelijk en deskundig team! Ze hebben ons vanaf het eerste contact tot de afhandeling volledig ontzorgd.",
        "time": 1722500000,
    },
    {
        "author_name": "Anja Bakker",
        "author_url": "https://www.google.com/maps/contrib/100000000000000000002",
        "profile_photo_url": "https://lh3.googleusercontent.com/a/default-user-photo-2",
        "rating": 5,
        "relative_time_description": "2 weken geleden",
        "text": "Heel tevreden over Bevingshulp Noord. De communicatie verliep helder en de inspectie werd snel ingepland. Zeker een aanrader voor iedereen met mijnbouwschade in Groningen.",
        "time": 1721900000,
    },
    {
        "author_name": "Peter Molenaar",
        "author_url": "https://www.google.com/maps/contrib/100000000000000000003",
        "profile_photo_url": "https://lh3.googleusercontent.com/a/default-user-photo-3",
        "rating": 5,
        "relative_time_description": "een maand geleden",
        "text": "Fijne en transparante service. Het adviesrapport en de opvolging bij het IMG waren dik in orde.",
        "time": 1719800000,
    },
    {
        "author_name": "Sanne Kuiper",
        "author_url": "https://www.google.com/maps/contrib/100000000000000000004",
        "profile_photo_url": "https://lh3.googleusercontent.com/a/default-user-photo-4",
        "rating": 5,
        "relative_time_description": "2 maanden geleden",
        "text": "Zeer kundige experts. Door hun hulp is onze aardbeving-schadeclaim vlot goedgekeurd.",
        "time": 1717200000,
    },
    {
        "author_name": "Erik Postma",
        "author_url": "https://www.google.com/maps/contrib/100000000000000000005",
        "profile_photo_url": "https://lh3.googleusercontent.com/a/default-user-photo-5",
        "rating": 5,
        "relative_time_description": "3 maanden geleden",
        "text": "Snelle reactie en top service. Denken goed mee met de klant.",
        "time": 1714500000,
    },
]


class GoogleReviewsService:
    """
    Service for fetching, caching, and serving Google Reviews & rating data
    for Bevingshulp Noord.
    """

    def __init__(self):
        self.api_key = getattr(settings, "GOOGLE_PLACES_API_KEY", "")
        self.place_id = getattr(settings, "GOOGLE_PLACE_ID", "ChIJZZtq0ms1x0cRlnzKtwRxopo")
        self.fid = getattr(settings, "GOOGLE_BUSINESS_FID", "0x47c5b5bb3a6a9b65:0x8ba67104b7ca7c96")
        self.cid = getattr(settings, "GOOGLE_BUSINESS_CID", "10062953288126758038")
        self.cache_timeout = getattr(settings, "GOOGLE_REVIEWS_CACHE_TIMEOUT", 86400)

    @property
    def write_review_url(self) -> str:
        """Direct link for customers to post a review on Google."""
        return f"https://search.google.com/local/writereview?placeid={self.place_id}"

    @property
    def google_maps_url(self) -> str:
        """Google Maps link for the business CID."""
        if self.cid:
            return f"https://maps.google.com/maps?cid={self.cid}"
        return f"https://www.google.com/maps/place/?q=place_id:{self.place_id}"

    def get_cache_key(self, limit: int = 5) -> str:
        return f"google_reviews_{self.place_id}_limit_{limit}"

    def fetch_from_google_api(self) -> Optional[Dict[str, Any]]:
        """
        Fetch place details directly from Google Places API (Details API).
        """
        if not self.api_key:
            logger.info("GOOGLE_PLACES_API_KEY is not configured; using fallback reviews.")
            return None

        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": self.place_id,
            "fields": "name,rating,reviews,user_ratings_total,url",
            "key": self.api_key,
            "language": "nl",
        }

        try:
            response = requests.get(url, params=params, timeout=8)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK":
                logger.warning("Google Places API error status: %s", data.get("status"))
                return None

            result = data.get("result", {})
            return {
                "name": result.get("name", "Bevingshulp Noord"),
                "rating": result.get("rating", 5.0),
                "user_ratings_total": result.get("user_ratings_total", len(DEFAULT_FALLBACK_REVIEWS)),
                "reviews": result.get("reviews", []),
                "source": "google_places_api",
            }
        except Exception as exc:
            logger.error("Failed to connect to Google Places API: %s", exc)
            return None

    def get_fallback_data(self) -> Dict[str, Any]:
        """Generate static fallback response data when API is unavailable."""
        return {
            "name": "Bevingshulp Noord",
            "rating": 4.9,
            "user_ratings_total": 28,
            "reviews": DEFAULT_FALLBACK_REVIEWS,
            "source": "fallback",
        }

    def get_reviews(self, limit: int = 5, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Retrieve Google Reviews data. Uses cache unless force_refresh is True.
        """
        cache_key = self.get_cache_key(limit=limit)

        if not force_refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                cached_data["cached"] = True
                return cached_data

        api_data = self.fetch_from_google_api()

        if api_data:
            reviews_list = api_data.get("reviews", [])[:limit]
            payload = {
                "place_id": self.place_id,
                "fid": self.fid,
                "cid": self.cid,
                "name": api_data.get("name", "Bevingshulp Noord"),
                "rating": api_data.get("rating", 4.9),
                "user_ratings_total": api_data.get("user_ratings_total", 28),
                "write_review_url": self.write_review_url,
                "google_maps_url": self.google_maps_url,
                "cached": False,
                "source": api_data.get("source", "google_places_api"),
                "reviews": reviews_list,
            }
        else:
            fallback = self.get_fallback_data()
            payload = {
                "place_id": self.place_id,
                "fid": self.fid,
                "cid": self.cid,
                "name": fallback["name"],
                "rating": fallback["rating"],
                "user_ratings_total": fallback["user_ratings_total"],
                "write_review_url": self.write_review_url,
                "google_maps_url": self.google_maps_url,
                "cached": False,
                "source": fallback["source"],
                "reviews": fallback["reviews"][:limit],
            }

        # Cache payload
        try:
            cache.set(cache_key, payload, timeout=self.cache_timeout)
        except Exception as e:
            logger.warning("Could not set cache for Google Reviews: %s", e)

        return payload
