from django.apps import AppConfig


class CreatorSubscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'creator_subscriptions'

    def ready(self):
        import creator_subscriptions.signals  # noqa: F401
