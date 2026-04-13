# X Creator Subscription Access Prototype

A local Django prototype for granting or denying site access based on a linked X user ID and cached subscription status.

## Run locally

```sh
uv run backend/manage.py migrate
uv run backend/manage.py test
uv run backend/manage.py createsuperuser
uv run backend/manage.py seed_blog_posts
uv run backend/manage.py runserver
```

Then open http://127.0.0.1:8000/.

The seed command creates one blog post for each access tier and refuses to run if any blog posts already exist.

Mock X checks are enabled by default with `X_SUBSCRIPTION_MOCK=true`. Use these mock X user IDs:

- `mock-premium` grants access.
- `mock-basic` grants access.
- `mock-plus` grants access.
- `mock-unsubscribed` revokes access on the next check.

For real X lookups, set `X_SUBSCRIPTION_MOCK=false` and add the creator account bearer token in Django admin under `Creator X credentials`. The backend calls `GET https://api.x.com/2/users/:id?user.fields=subscription`; user tokens are not stored.

```sh
X_SUBSCRIPTION_MOCK=false uv run backend/manage.py runserver
```

## Manual testing

1. Apply migrations and create an admin user:

```sh
uv run backend/manage.py migrate
uv run backend/manage.py createsuperuser
```

2. Seed one blog post per access tier:

```sh
uv run backend/manage.py seed_blog_posts
```

Expected result: `Created 4 blog posts.`

If any blog post already exists, the command stops with an error. Delete existing posts in `/admin/` before rerunning it.

3. Start the local server in mock mode:

```sh
uv run backend/manage.py runserver
```

4. Open the admin at http://127.0.0.1:8000/admin/ and sign in with the superuser.

5. Open `Blog posts` in admin. Confirm there are four posts and each has a different access tier:

- `Public`
- `Basic`
- `Premium`
- `Premium Plus`

6. Test unauthenticated access:

- Open http://127.0.0.1:8000/blog/.
- Open the public post. It should load.
- Open a Basic, Premium, or Premium Plus post. It should show an access-needed page.
- Open http://127.0.0.1:8000/members-only/. It should redirect to login because you are not signed in.

7. Test an email user connecting a mock X account:

- Open http://127.0.0.1:8000/register/.
- Create a normal email/password user.
- Open http://127.0.0.1:8000/profile/.
- Click `Connect mock X account`.
- Enter `mock-basic`.
- Open http://127.0.0.1:8000/members-only/. It should load.
- Open the Basic blog post. It should load.
- Open the Premium blog post. It should be denied.

8. Test higher tiers:

- Go back to http://127.0.0.1:8000/connect-x/mock/.
- Change the X user ID to `mock-premium`.
- Open the Premium blog post. It should load.
- Open the Premium Plus post. It should be denied.
- Change the X user ID to `mock-plus`.
- Open the Premium Plus post. It should load.

9. Test revocation:

- Go to http://127.0.0.1:8000/connect-x/mock/.
- Change the X user ID to `mock-unsubscribed`.
- Open http://127.0.0.1:8000/members-only/. It should be denied.
- Open any tiered blog post. It should be denied.
- Open http://127.0.0.1:8000/profile/. `X Subscriber` should be `No`.

10. Test mock X sign-in linking to an existing email user:

- Log out.
- Open http://127.0.0.1:8000/sign-in-with-x/mock/.
- Enter `mock-premium` as the X user ID.
- Enter the email address for the user you created in step 7 as `confirmed_email`.
- Submit the form.
- Open http://127.0.0.1:8000/profile/. The same email account should now show the linked X user ID and subscriber status.

## Real X OAuth setup

Use this only when you have an X Developer App and a creator bearer token that can read subscription data.

1. In the X Developer Portal, configure an OAuth 2.0 app.

Use this local callback URL:

```text
http://127.0.0.1:8000/accounts/twitter_oauth2/login/callback/
```

2. Start the local server:

```sh
uv run backend/manage.py runserver
```

3. Open http://127.0.0.1:8000/admin/ and sign in with the superuser.

4. Add the X OAuth client in admin:

- Open `Social applications`.
- Click `Add social application`.
- Set `Provider` to `X`.
- Set `Name` to `X local`.
- Paste the X app `Client id`.
- Paste the X app `Secret key`.
- Move the current site, usually `example.com`, into `Chosen sites`.
- Save.

5. Add the creator bearer token in admin:

- Open `Creator X credentials`.
- Click `Add creator X credential`.
- Set `Name` to `Creator account`.
- Paste the creator account bearer token into `Bearer token`.
- Leave `Is active` checked.
- Save.

6. Stop the server and restart it with real subscription lookups enabled:

```sh
X_SUBSCRIPTION_MOCK=false uv run backend/manage.py runserver
```

7. Open http://127.0.0.1:8000/profile/ and use `Manage real X OAuth` to connect an X account through allauth.

8. Open http://127.0.0.1:8000/members-only/ and http://127.0.0.1:8000/blog/ to confirm the connected X account grants or denies access based on the creator-authenticated subscription lookup.

## Useful routes

- `/register/` creates an email/password account.
- `/accounts/login/` signs in with email/password through django-allauth.
- `/sign-in-with-x/mock/` simulates X sign-in and can link an existing email account by confirmed email.
- `/profile/` shows linked X status and subscription state.
- `/connect-x/mock/` links a mock X user ID to an existing account.
- `/members-only/` checks the cached subscription and gates access.
- `/blog/` lists published blog posts.
- `/admin/` manages blog posts and marks each one as Public, Basic, Premium, or Premium Plus.

## X and allauth references

- User data dictionary: https://docs.x.com/x-api/fundamentals/data-dictionary#user
- Users lookup: https://docs.x.com/x-api/users/lookup
- OAuth 2.0: https://docs.x.com/fundamentals/authentication/oauth-2-0/overview
- django-allauth: https://docs.allauth.org/en/latest/installation/quickstart.html
