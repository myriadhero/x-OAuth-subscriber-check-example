from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import BlogPost


User = get_user_model()


@override_settings(X_SUBSCRIPTION_MOCK=True, X_SUBSCRIPTION_CACHE_SECONDS=0)
class BlogAccessTests(TestCase):
    def test_post_list_splits_posts_for_anonymous_visitor(self):
        self.create_tier_posts()

        response = self.client.get(reverse('blog:post_list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [post.access_tier for post in response.context['accessible_posts']],
            [BlogPost.AccessTier.PUBLIC],
        )
        self.assertCountEqual(
            [post.access_tier for post in response.context['locked_posts']],
            [
                BlogPost.AccessTier.BASIC,
                BlogPost.AccessTier.PREMIUM,
                BlogPost.AccessTier.PREMIUM_PLUS,
            ],
        )

    def test_post_list_splits_posts_for_basic_subscriber(self):
        self.create_tier_posts()
        user = User.objects.create_user(
            username='basic-reader',
            email='basic@example.com',
            password='secret12345',
        )
        user.profile.x_user_id = 'mock-basic'
        user.profile.save()
        self.client.login(username='basic-reader', password='secret12345')

        response = self.client.get(reverse('blog:post_list'))

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            [post.access_tier for post in response.context['accessible_posts']],
            [BlogPost.AccessTier.BASIC, BlogPost.AccessTier.PUBLIC],
        )
        self.assertCountEqual(
            [post.access_tier for post in response.context['locked_posts']],
            [BlogPost.AccessTier.PREMIUM, BlogPost.AccessTier.PREMIUM_PLUS],
        )

    def test_public_post_is_visible_without_login(self):
        post = BlogPost.objects.create(
            title='Public update',
            slug='public-update',
            body='Available to everyone.',
            access_tier=BlogPost.AccessTier.PUBLIC,
        )

        response = self.client.get(reverse('blog:post_detail', args=[post.slug]))

        self.assertEqual(response.status_code, 200)

    def create_tier_posts(self):
        return [
            BlogPost.objects.create(
                title='Public update',
                slug='public-update',
                body='Public content.',
                access_tier=BlogPost.AccessTier.PUBLIC,
            ),
            BlogPost.objects.create(
                title='Basic update',
                slug='basic-update',
                body='Basic content.',
                access_tier=BlogPost.AccessTier.BASIC,
            ),
            BlogPost.objects.create(
                title='Premium update',
                slug='premium-update',
                body='Premium content.',
                access_tier=BlogPost.AccessTier.PREMIUM,
            ),
            BlogPost.objects.create(
                title='Premium Plus update',
                slug='premium-plus-update',
                body='Premium Plus content.',
                access_tier=BlogPost.AccessTier.PREMIUM_PLUS,
            ),
        ]


@override_settings(X_SUBSCRIPTION_MOCK=True, X_SUBSCRIPTION_CACHE_SECONDS=0)
class SeedBlogPostsCommandTests(TestCase):
    def test_seed_blog_posts_creates_one_post_per_tier(self):
        call_command('seed_blog_posts')

        self.assertEqual(BlogPost.objects.count(), 4)
        self.assertEqual(
            set(BlogPost.objects.values_list('access_tier', flat=True)),
            {
                BlogPost.AccessTier.PUBLIC,
                BlogPost.AccessTier.BASIC,
                BlogPost.AccessTier.PREMIUM,
                BlogPost.AccessTier.PREMIUM_PLUS,
            },
        )

    def test_seed_blog_posts_refuses_to_run_when_posts_exist(self):
        BlogPost.objects.create(
            title='Existing post',
            slug='existing-post',
            body='Already here.',
        )

        with self.assertRaises(CommandError):
            call_command('seed_blog_posts')

    def test_premium_post_denies_basic_subscriber(self):
        post = BlogPost.objects.create(
            title='Premium update',
            slug='premium-update',
            body='Premium content.',
            access_tier=BlogPost.AccessTier.PREMIUM,
        )
        user = User.objects.create_user(
            username='basic-reader',
            email='basic@example.com',
            password='secret12345',
        )
        user.profile.x_user_id = 'mock-basic'
        user.profile.save()
        self.client.login(username='basic-reader', password='secret12345')

        response = self.client.get(reverse('blog:post_detail', args=[post.slug]))

        self.assertEqual(response.status_code, 403)

    def test_premium_post_allows_premium_subscriber(self):
        post = BlogPost.objects.create(
            title='Premium update',
            slug='premium-update',
            body='Premium content.',
            access_tier=BlogPost.AccessTier.PREMIUM,
        )
        user = User.objects.create_user(
            username='premium-reader',
            email='premium@example.com',
            password='secret12345',
        )
        user.profile.x_user_id = 'mock-premium'
        user.profile.save()
        self.client.login(username='premium-reader', password='secret12345')

        response = self.client.get(reverse('blog:post_detail', args=[post.slug]))

        self.assertEqual(response.status_code, 200)
