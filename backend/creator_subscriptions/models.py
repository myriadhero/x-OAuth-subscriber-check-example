from django.db import models
from django.conf import settings


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    x_user_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    x_subscription_status = models.JSONField(default=dict, blank=True)
    x_subscription_last_checked = models.DateTimeField(null=True, blank=True)
    is_x_subscriber = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user} X subscription profile'


class CreatorXCredential(models.Model):
    name = models.CharField(max_length=80, default='Default creator credential')
    bearer_token = models.TextField(help_text='Creator account bearer token for X API lookups.')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Creator X credential'
        verbose_name_plural = 'Creator X credentials'

    def __str__(self):
        status = 'active' if self.is_active else 'inactive'
        return f'{self.name} ({status})'
