from django.core.management.base import BaseCommand, CommandError

from blog.models import BlogPost


class Command(BaseCommand):
    help = 'Seed one test blog post for each access tier.'

    def handle(self, *args, **options):
        if BlogPost.objects.exists():
            raise CommandError('Blog posts already exist. Delete them before seeding test data.')

        posts = [
            {
                'title': 'Public Field Notes',
                'slug': 'public-field-notes',
                'excerpt': 'A public test post available to every visitor.',
                'body': 'This post is public. It should be visible without logging in.',
                'access_tier': BlogPost.AccessTier.PUBLIC,
            },
            {
                'title': 'Basic Subscriber Brief',
                'slug': 'basic-subscriber-brief',
                'excerpt': 'A Basic-tier test post for subscriber access checks.',
                'body': 'This post requires Basic access or higher.',
                'access_tier': BlogPost.AccessTier.BASIC,
            },
            {
                'title': 'Premium Subscriber Brief',
                'slug': 'premium-subscriber-brief',
                'excerpt': 'A Premium-tier test post for subscriber access checks.',
                'body': 'This post requires Premium access or higher.',
                'access_tier': BlogPost.AccessTier.PREMIUM,
            },
            {
                'title': 'Premium Plus Subscriber Brief',
                'slug': 'premium-plus-subscriber-brief',
                'excerpt': 'A Premium Plus-tier test post for subscriber access checks.',
                'body': 'This post requires Premium Plus access.',
                'access_tier': BlogPost.AccessTier.PREMIUM_PLUS,
            },
        ]

        BlogPost.objects.bulk_create(BlogPost(**post) for post in posts)
        self.stdout.write(self.style.SUCCESS('Created 4 blog posts.'))
