from rest_framework import serializers


class SingleGoogleReviewSerializer(serializers.Serializer):
    author_name = serializers.CharField(max_length=255)
    author_url = serializers.URLField(required=False, allow_blank=True)
    profile_photo_url = serializers.URLField(required=False, allow_blank=True)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    relative_time_description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    text = serializers.CharField(required=False, allow_blank=True)
    time = serializers.IntegerField(required=False)


class GoogleReviewsResponseSerializer(serializers.Serializer):
    place_id = serializers.CharField(max_length=255)
    fid = serializers.CharField(max_length=255, required=False, allow_blank=True)
    cid = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name = serializers.CharField(max_length=255)
    rating = serializers.FloatField()
    user_ratings_total = serializers.IntegerField()
    write_review_url = serializers.URLField()
    google_maps_url = serializers.URLField()
    cached = serializers.BooleanField(default=False)
    source = serializers.CharField(max_length=50)
    reviews = SingleGoogleReviewSerializer(many=True)


class WriteReviewUrlSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    write_review_url = serializers.URLField()
    google_maps_url = serializers.URLField()
    place_id = serializers.CharField(max_length=255)
    cid = serializers.CharField(max_length=255)
