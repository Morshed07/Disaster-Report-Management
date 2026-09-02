import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ContactMessageSerializer
from .tasks import send_contact_message_email

logger = logging.getLogger(__name__)


class ContactMessageCreateView(APIView):
    """
    API endpoint for submitting the 'Send us a message' contact form.
    """

    def post(self, request, *args, **kwargs):
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()

            # Trigger background Celery confirmation & notification task (non-blocking if Celery/Redis is down)
            try:
                send_contact_message_email.delay(instance.id)
            except Exception:
                logger.exception(
                    "Celery task dispatch failed for ContactMessage %s — continuing.",
                    instance.id,
                )

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

