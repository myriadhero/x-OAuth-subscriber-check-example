import json

from django.core.management.base import BaseCommand, CommandError

from creator_subscriptions.services import (
    XSubscriptionError,
    fetch_x_subscription,
    parse_subscription_type,
)


class Command(BaseCommand):
    help = 'Force an X subscription lookup by X user ID, bypassing profile cache.'

    def add_arguments(self, parser):
        parser.add_argument('x_user_id', help='The X user ID to look up.')

    def handle(self, *args, **options):
        x_user_id = options['x_user_id']

        try:
            payload = fetch_x_subscription(x_user_id)
        except XSubscriptionError as exc:
            raise CommandError(str(exc)) from exc

        subscription_type = parse_subscription_type(payload) or 'None'
        self.stdout.write(self.style.SUCCESS(f'Lookup complete for X user {x_user_id}.'))
        self.stdout.write(f'Subscription type: {subscription_type}')
        self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
