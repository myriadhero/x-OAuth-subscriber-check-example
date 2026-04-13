import logging

from allauth.socialaccount.signals import social_account_added, social_account_updated
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile
from .services import link_x_account, refresh_profile_subscription


logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(user_logged_in)
def refresh_subscription_on_login(sender, user, **kwargs):
    profile, _ = Profile.objects.get_or_create(user=user)
    if profile.x_user_id:
        refresh_profile_subscription(profile)


@receiver(social_account_added)
@receiver(social_account_updated)
def sync_x_social_account(sender, sociallogin, **kwargs):
    account = sociallogin.account
    if account.provider != 'twitter_oauth2':
        return

    try:
        profile = link_x_account(sociallogin.user, account.uid)
    except ValidationError:
        logger.warning('X social account was already linked elsewhere.', exc_info=True)
        return

    refresh_profile_subscription(profile, force=True)
