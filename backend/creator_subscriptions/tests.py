from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from allauth.socialaccount.models import SocialApp
from io import StringIO
from unittest.mock import patch

from .models import CreatorXCredential, Profile
from .services import (
    XSubscriptionError,
    _cache_is_fresh,
    _fetch_real_x_subscription,
    get_active_creator_bearer_token,
    refresh_profile_subscription,
)


User = get_user_model()


@override_settings(X_SUBSCRIPTION_MOCK=True, X_SUBSCRIPTION_CACHE_SECONDS=0)
class SubscriptionAccessTests(TestCase):
    def test_profile_is_created_for_email_user(self):
        user = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )

        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_members_only_denies_unlinked_user(self):
        User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )
        self.client.login(username='reader', password='secret12345')

        response = self.client.get(reverse('creator_subscriptions:members_only'))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'X connected:', status_code=403)
        self.assertContains(response, 'No', status_code=403)
        self.assertContains(response, 'Tier:', status_code=403)

    def test_allauth_login_uses_project_shell(self):
        response = self.client.get(reverse('account_login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Creator Subscriptions')
        self.assertContains(response, 'Mock sign in with X')

    def test_allauth_logout_uses_project_shell(self):
        User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )
        self.client.login(username='reader', password='secret12345')

        response = self.client.get(reverse('account_logout'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Creator Subscriptions')
        self.assertContains(response, 'Stay signed in')

    def test_allauth_connections_uses_project_shell(self):
        User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )
        self.client.login(username='reader', password='secret12345')

        response = self.client.get(reverse('socialaccount_connections'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Creator Subscriptions')
        self.assertContains(response, 'Third-party accounts')
        self.assertContains(response, 'Back to profile')

    def test_x_oauth_connect_handoff_uses_project_shell(self):
        user = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )
        app = SocialApp.objects.create(
            provider='twitter_oauth2',
            name='X local',
            client_id='client-id',
            secret='client-secret',
        )
        app.sites.add(Site.objects.get_current())
        self.client.force_login(user)

        response = self.client.get(reverse('twitter_oauth2_login'), {'process': 'connect'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Creator Subscriptions')
        self.assertContains(response, 'Connect X')
        self.assertContains(response, 'Back to third-party accounts')

    def test_allauth_third_party_error_uses_project_shell(self):
        response = self.client.get(reverse('socialaccount_login_error'))

        self.assertEqual(response.status_code, 401)
        self.assertContains(response, 'Creator Subscriptions', status_code=401)
        self.assertContains(response, 'Third-party login failed', status_code=401)

    def test_register_page_links_to_x_and_login(self):
        response = self.client.get(reverse('creator_subscriptions:register'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mock sign in with X')
        self.assertContains(response, 'Back to login')

    def test_mock_x_sign_in_page_links_to_email_register_and_login(self):
        response = self.client.get(reverse('creator_subscriptions:mock_x_sign_in'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Register with email')
        self.assertContains(response, 'Back to login')

    def test_registered_email_user_can_log_in_with_email(self):
        self.client.post(
            reverse('creator_subscriptions:register'),
            {
                'username': 'reader',
                'email': 'reader@example.com',
                'password1': 'secret12345',
                'password2': 'secret12345',
            },
        )
        self.client.logout()

        response = self.client.post(
            reverse('account_login'),
            {'login': 'reader@example.com', 'password': 'secret12345'},
        )

        self.assertEqual(response.status_code, 302)

    def test_members_only_allows_mock_subscriber(self):
        user = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )
        user.profile.x_user_id = 'mock-premium'
        user.profile.save()
        self.client.login(username='reader', password='secret12345')

        response = self.client.get(reverse('creator_subscriptions:members_only'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'X connected:')
        self.assertContains(response, 'X subscriber:')
        self.assertContains(response, 'Premium')
        user.profile.refresh_from_db()
        self.assertTrue(user.profile.is_x_subscriber)

    def test_members_only_revokes_mock_unsubscriber(self):
        user = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )
        user.profile.x_user_id = 'mock-unsubscribed'
        user.profile.is_x_subscriber = True
        user.profile.save()
        self.client.login(username='reader', password='secret12345')

        response = self.client.get(reverse('creator_subscriptions:members_only'))

        self.assertEqual(response.status_code, 403)
        user.profile.refresh_from_db()
        self.assertFalse(user.profile.is_x_subscriber)

    def test_mock_x_sign_in_links_existing_email_user(self):
        user = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )

        response = self.client.post(
            reverse('creator_subscriptions:mock_x_sign_in'),
            {'x_user_id': 'mock-plus', 'confirmed_email': 'reader@example.com'},
        )

        self.assertRedirects(response, reverse('creator_subscriptions:profile'))
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.x_user_id, 'mock-plus')
        self.assertTrue(user.profile.is_x_subscriber)

    @override_settings(DEBUG=True, X_SUBSCRIPTION_LOG_SAMPLE_RESPONSE=True)
    def test_subscription_sample_logging_can_be_enabled_in_debug(self):
        user = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )
        user.profile.x_user_id = 'mock-premium'
        user.profile.save()

        with patch('creator_subscriptions.services.logger.info') as log_info:
            refresh_profile_subscription(user.profile, force=True)

        log_info.assert_called_once()
        self.assertIn('X subscription lookup sample', log_info.call_args.args[0])
        self.assertEqual(log_info.call_args.args[1], 'mock-premium')

    @override_settings(DEBUG=False, X_SUBSCRIPTION_LOG_SAMPLE_RESPONSE=True)
    def test_subscription_sample_logging_requires_debug(self):
        user = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )
        user.profile.x_user_id = 'mock-premium'
        user.profile.save()

        with patch('creator_subscriptions.services.logger.info') as log_info:
            refresh_profile_subscription(user.profile, force=True)

        log_info.assert_not_called()

    @override_settings(DEBUG=True, X_SUBSCRIPTION_LOG_SAMPLE_RESPONSE=True)
    def test_force_subscription_lookup_command_triggers_sample_logging(self):
        out = StringIO()

        with patch('creator_subscriptions.services.logger.info') as log_info:
            call_command('force_x_subscription_lookup', 'mock-premium', stdout=out)

        log_info.assert_called_once()
        self.assertEqual(log_info.call_args.args[1], 'mock-premium')
        self.assertIn('Subscription type: Premium', out.getvalue())

    @override_settings(X_SUBSCRIPTION_MOCK=False)
    def test_force_subscription_lookup_command_reports_lookup_errors(self):
        with self.assertRaises(CommandError):
            call_command('force_x_subscription_lookup', '123', stdout=StringIO())


class CreatorXCredentialTests(TestCase):
    def test_active_creator_bearer_token_comes_from_database(self):
        CreatorXCredential.objects.create(
            name='Creator account',
            bearer_token=' token-from-admin ',
            is_active=True,
        )

        self.assertEqual(get_active_creator_bearer_token(), 'token-from-admin')

    @override_settings(X_SUBSCRIPTION_MOCK=False)
    def test_real_subscription_lookup_requires_admin_credential(self):
        with self.assertRaisesMessage(
            XSubscriptionError,
            'No active creator X credential is configured in admin.',
        ):
            _fetch_real_x_subscription('123')

    @override_settings(X_SUBSCRIPTION_MOCK=False)
    def test_subscription_error_marks_profile_dirty_and_keeps_cached_status(self):
        user = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )
        profile = user.profile
        profile.x_user_id = '123'
        profile.is_x_subscriber = True
        profile.x_subscription_status = {'subscription_type': 'Premium'}
        profile.x_subscription_last_checked = timezone.now()
        profile.save()

        refresh_profile_subscription(profile, force=True)

        profile.refresh_from_db()
        self.assertTrue(profile.x_subscription_check_failed)
        self.assertFalse(_cache_is_fresh(profile))
        self.assertTrue(profile.is_x_subscriber)
        self.assertEqual(profile.x_subscription_status['subscription_type'], 'Premium')

    def test_dirty_subscription_state_retries_next_refresh_and_clears_on_success(self):
        user = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )
        profile = user.profile
        profile.x_user_id = '123'
        profile.x_subscription_check_failed = True
        profile.x_subscription_last_error = 'Subscription status could not be verified.'
        profile.x_subscription_last_checked = timezone.now()
        profile.save()

        with patch(
            'creator_subscriptions.services.fetch_x_subscription',
            return_value={'data': {'subscription': {'subscription_type': 'Basic'}}},
        ) as fetch_subscription:
            refresh_profile_subscription(profile)

        profile.refresh_from_db()
        fetch_subscription.assert_called_once_with('123')
        self.assertFalse(profile.x_subscription_check_failed)
        self.assertEqual(profile.x_subscription_last_error, '')
        self.assertTrue(profile.is_x_subscriber)
        self.assertEqual(profile.x_subscription_status['subscription_type'], 'Basic')

    @override_settings(X_SUBSCRIPTION_MOCK=False)
    def test_members_only_shows_subscription_lookup_error_notice(self):
        user = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='secret12345',
        )
        user.profile.x_user_id = '123'
        user.profile.save()
        self.client.login(username='reader', password='secret12345')

        response = self.client.get(reverse('creator_subscriptions:members_only'))

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            'Subscription status could not be verified.',
            status_code=403,
        )
