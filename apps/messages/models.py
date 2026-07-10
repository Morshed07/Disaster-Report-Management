from django.db import models
from apps.reports.models import TimeStampedModel
# Create your models here.


class ContactMessage(TimeStampedModel):
    """
    Maps to the "Send us a message" contact form (Image 1).
    """
 
    name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=30)
    email = models.EmailField()
    message = models.TextField()
    privacy_policy_accepted = models.BooleanField(default=False)

    is_handled = models.BooleanField(default=False)
 
    class Meta:
        ordering = ["-created_at"]
 
    def __str__(self) -> str:
        return f"Message from {self.name} ({self.email})"