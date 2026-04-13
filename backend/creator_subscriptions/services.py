import json
import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import CreatorXCredential, Profile


logger = logging.getLogger(__name__)

ACTIVE_SUBSCRIPTION_TYPES = {'Basic', 'Premium', 'PremiumPlus'}
SUBSCRIPTION_CHECK_FAILED_MESSAGE = (
    'Subscription status could not be verified. Please try again later or contact an admin.'
)
MOCK_SUBSCRIPTION_TYPES = {
    'mock-basic': 'Basic',
    'mock-premium': 'Premium',
    'mock-plus': 'PremiumPlus',
    'mock-unsubscribed': None,
}


class XSubscriptionError(Exception):
    pass


def link_x_account(user, x_user_id):
    if Profile.objects.filter(x_user_id=x_user_id).exclude(user=user).exists():
        raise ValidationError('That X account is already connected to another user.')

    profile, _ = Profile.objects.get_or_create(user=user)
    profile.x_user_id = x_user_id
    profile.save(update_fields=['x_user_id'])
    return profile


def refresh_profile_subscription(profile, force=False):
    if not profile.x_user_id:
        profile.is_x_subscriber = False
        profile.x_subscription_status = {}
        profile.x_subscription_last_checked = timezone.now()
        profile.x_subscription_check_failed = False
        profile.x_subscription_last_error = ''
        profile.save(
            update_fields=[
                'is_x_subscriber',
                'x_subscription_status',
                'x_subscription_last_checked',
                'x_subscription_check_failed',
                'x_subscription_last_error',
            ]
        )
        return profile

    if not force and _cache_is_fresh(profile):
        return profile

    try:
        payload = fetch_x_subscription(profile.x_user_id)
    except XSubscriptionError:
        logger.warning('X subscription lookup failed; using cached status.')
        profile.x_subscription_check_failed = True
        profile.x_subscription_last_error = SUBSCRIPTION_CHECK_FAILED_MESSAGE
        profile.save(
            update_fields=[
                'x_subscription_check_failed',
                'x_subscription_last_error',
            ]
        )
        return profile

    subscription_state = parse_subscription_state(payload)
    profile.is_x_subscriber = subscription_state['is_subscriber']
    profile.x_subscription_status = {
        'subscribes_to_you': subscription_state['subscribes_to_you'],
        'subscription_type': subscription_state['subscription_type'],
        'access_tier': subscription_state['access_tier'],
        'raw': payload,
    }
    profile.x_subscription_last_checked = timezone.now()
    profile.x_subscription_check_failed = False
    profile.x_subscription_last_error = ''
    profile.save(
        update_fields=[
            'is_x_subscriber',
            'x_subscription_status',
            'x_subscription_last_checked',
            'x_subscription_check_failed',
            'x_subscription_last_error',
        ]
    )
    return profile


def fetch_x_subscription(x_user_id):
    if settings.X_SUBSCRIPTION_MOCK:
        payload = _fetch_mock_x_subscription(x_user_id)
    else:
        payload = _fetch_real_x_subscription(x_user_id)
    _log_subscription_lookup_sample(x_user_id, payload)
    return payload


def parse_subscription_type(payload):
    return parse_subscription_state(payload)['subscription_type']


def parse_subscription_state(payload):
    data = payload.get('data', payload)
    subscription = data.get('subscription') if isinstance(data, dict) else None
    subscribes_to_you = None
    subscription_type = None

    if isinstance(subscription, dict):
        subscribes_to_you = subscription.get('subscribes_to_you')
        subscription_type = subscription.get('subscription_type')
    elif isinstance(subscription, str):
        subscription_type = subscription

    if subscribes_to_you is not None:
        is_subscriber = bool(subscribes_to_you)
        access_tier = (
            _access_tier_for_subscription(subscription_type, is_subscriber)
            if is_subscriber
            else None
        )
    else:
        access_tier = _access_tier_for_subscription(subscription_type, False)
        is_subscriber = access_tier in ACTIVE_SUBSCRIPTION_TYPES

    return {
        'is_subscriber': is_subscriber,
        'subscribes_to_you': subscribes_to_you,
        'subscription_type': subscription_type,
        'access_tier': access_tier,
    }


def _access_tier_for_subscription(subscription_type, is_creator_subscriber):
    if subscription_type in ACTIVE_SUBSCRIPTION_TYPES:
        return subscription_type
    if is_creator_subscriber:
        return 'Basic'
    return None


def _fetch_mock_x_subscription(x_user_id):
    # Mock API calls are active for testing.
    subscription_type = MOCK_SUBSCRIPTION_TYPES.get(
        x_user_id,
        settings.X_SUBSCRIPTION_MOCK_TYPE,
    )
    subscription = (
        {'subscription_type': subscription_type}
        if subscription_type
        else None
    )
    return {
        'data': {
            'id': x_user_id,
            'subscription': subscription,
        }
    }


def _fetch_real_x_subscription(x_user_id):
    token = get_active_creator_bearer_token()
    if not token:
        raise XSubscriptionError('No active creator X credential is configured in admin.')

    url = f'https://api.x.com/2/users/{x_user_id}'

    try:
        response = requests.get(
            url,
            params={'user.fields': 'subscription'},
            headers={'Authorization': f'Bearer {token}'},
            timeout=settings.X_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise XSubscriptionError('X subscription lookup failed.') from exc


def get_active_creator_bearer_token():
    credential = CreatorXCredential.objects.filter(is_active=True).order_by('-updated_at').first()
    if not credential:
        return ''
    return credential.bearer_token.strip()


def _log_subscription_lookup_sample(x_user_id, payload):
    if not settings.DEBUG or not settings.X_SUBSCRIPTION_LOG_SAMPLE_RESPONSE:
        return

    logger.info(
        'X subscription lookup sample: x_user_id=%s response=%s',
        x_user_id,
        json.dumps(payload, sort_keys=True, default=str),
    )


def _cache_is_fresh(profile):
    if profile.x_subscription_check_failed:
        return False

    if not profile.x_subscription_last_checked:
        return False

    ttl = timedelta(seconds=settings.X_SUBSCRIPTION_CACHE_SECONDS)
    return timezone.now() - profile.x_subscription_last_checked < ttl
