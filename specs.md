# PROJECT SPECIFICATION: Django + X Creator Subscriptions Auto-Access System
## 1. Project Overview
Build a Django web application that automatically grants/revokes access to gated website sections based on a user’s active X Creator Subscription status.

- No manual add/remove of subscribers.
- Support existing email-only users (they can later “Connect X Account”).
- Support testing against mock API (without access to a legitimate creator account with subs).
- Use official X API v2 (as of 2026): user.fields=subscription (returns subscription object with subscription_type: None / Basic / Premium / PremiumPlus). Must authenticate lookups as the creator.

## 2. Core Requirements

- Users sign in with email/password (existing accounts).
- Optional “Sign in with X” (new users) or “Connect X Account” (existing users).
- On login or protected-page access: check linked X user ID → subscription status (cached).
- If subscribed → grant access to gated views/pages.
- If unsubscribed or no link → deny or redirect.
- Handle unsubscribe edge cases gracefully (revoke on next check).
- Secure: never expose X tokens; use backend-only creator auth token.
- Rate-limit aware (cache aggressively).

## 3. Tech Stack (exact versions optional for LLM)

- Python Django
- django-allauth (or allauth-socialaccount) with OAuth 2.0 provider for X (“Sign in with X” + Connect).
- sqlite is fine for this prototype
- caching can be implemented as simple db time field for now - make it modular so it can be swapped for redis later

## 4. Database Models (add to existing User model)
Extend Django’s User or use a Profile model:
- x_user_id (CharField, unique, nullable)
- x_subscription_status (JSONField or CharField for cached result)
- x_subscription_last_checked (DateTimeField)
- is_x_subscriber (BooleanField, computed/cached)

## 5. OAuth & X Integration Flow

- Admin to Create X Developer App (OAuth 2.0, Client ID/Secret).
- Admin to add the creator access token (admin's creator account token — never user tokens for lookups) to backend through Django admin portal.
- “Sign in with X” or “Connect X” → django-allauth captures X user ID only.
- Link X user ID to Django user account.
- Protected views/middleware:
  - If X user ID present → call X API /2/users/:id?user.fields=subscription (authenticated as creator).
  - Parse subscription.subscription_type (or subscription object).
  - Cache result.
  - Grant access if active subscription.
- Ensure timely removal of sub if user no longer subbed


## 6. Development vs Production Mode

- settings.X_SUBSCRIPTION_MOCK=True → return mock {"subscription": {"subscription_type": "Premium"}} for any X ID.
  - otherwise real API call (swap one function).
  - Include clear comment: "Mock API calls are active for testing.”

## 7. Key Views & Features

- Login / Register (email or X).
  - If user registered with email before but didn't link the account, then registered with X in a new session, check X user API `confirmed_email` to link or create a new account
- Profile page: “Connect X Account” button (if their account is email and not linked).
- Gated content views (example: /members-only/) - user must be logged in and belong to subbed group.
- Subscription status indicator on profile (shows “X Subscriber: Yes/No”).

## 8. Security & Best Practices

- Store only X user ID (never tokens in DB for users).
- Creator token in environment variables only.
- Logging for subscription checks (without PII).
- Error handling: X API down → use last cached status + graceful fallback.

## 9. Acceptance Criteria

- Existing email users can connect X later without losing data.
- New users can sign in directly with X.
- Gated pages work with mock in dev.
- Subscription status updates automatically.
- No manual intervention ever required to update sub status.

## 10. Official X Docs References (include these links)

- User data dictionary (subscription field): https://docs.x.com/x-api/fundamentals/data-dictionary#user
- Users lookup: https://docs.x.com/x-api/users/lookup
- OAuth 2.0: https://docs.x.com/fundamentals/authentication/oauth-2-0/overview
- django-allauth: https://docs.allauth.org/en/latest/installation/quickstart.html 

## 11. Use uv

Use uv to manage the project:
```sh
uv run backend/manage.py startapp <newapp> backend/<newapp>
uv run backend/manage.py makemigrations
uv run backend/manage.py migrate
uv run backend/manage.py createsuperuser
uv run backend/manage.py runserver
uv run backend/manage.py test
```

