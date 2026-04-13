import json

from django.core.management.base import BaseCommand, CommandError

from creator_subscriptions.services import (
    XSubscriptionError,
    fetch_x_subscription,
    parse_subscription_state,
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

        state = parse_subscription_state(payload)
        access_tier = state['access_tier'] or 'None'
        self.stdout.write(self.style.SUCCESS(f'Lookup complete for X user {x_user_id}.'))
        self.stdout.write(f'Subscribes to you: {state["subscribes_to_you"]}')
        self.stdout.write(f'Subscription type: {state["subscription_type"] or "None"}')
        self.stdout.write(f'Access tier: {access_tier}')
        self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
