from django.db import models
from django.utils import timezone
import pytz

class OAuthToken(models.Model):
    token = models.TextField()
    refresh_token = models.TextField(blank=True)
    token_uri = models.URLField()
    client_id = models.TextField()
    client_secret = models.TextField()
    scopes = models.TextField()
    universe_domain = models.TextField(blank=True, null=True)
    account = models.TextField(blank=True, null=True)
    expiry = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if self.expiry and self.expiry.tzinfo is None:
            self.expiry = pytz.UTC.localize(self.expiry)
        super().save(*args, **kwargs)

    def get_expiry(self):
        """Return timezone-aware expiry time"""
        if self.expiry and self.expiry.tzinfo is None:
            return pytz.UTC.localize(self.expiry)
        return self.expiry.astimezone(pytz.UTC)