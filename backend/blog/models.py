from django.db import models


class BlogPost(models.Model):
    class AccessTier(models.TextChoices):
        PUBLIC = 'public', 'Public'
        BASIC = 'Basic', 'Basic'
        PREMIUM = 'Premium', 'Premium'
        PREMIUM_PLUS = 'PremiumPlus', 'Premium Plus'

    title = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    excerpt = models.TextField(blank=True)
    body = models.TextField()
    access_tier = models.CharField(
        max_length=32,
        choices=AccessTier,
        default=AccessTier.PUBLIC,
    )
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_public(self):
        return self.access_tier == self.AccessTier.PUBLIC
