from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from .forms import EmailRegistrationForm, MockXConnectForm, MockXSignInForm
from .models import Profile
from .services import link_x_account, refresh_profile_subscription


User = get_user_model()
AUTH_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def home(request):
    return render(request, 'creator_subscriptions/home.html')


@require_http_methods(['GET', 'POST'])
def register(request):
    if request.user.is_authenticated:
        return redirect('creator_subscriptions:profile')

    form = EmailRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        _mark_primary_email(user, verified=True)
        login(request, user, backend=AUTH_BACKEND)
        messages.success(request, 'Account created.')
        return redirect('creator_subscriptions:profile')

    return render(request, 'creator_subscriptions/register.html', {'form': form})


@login_required
def profile(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    if profile_obj.x_user_id:
        refresh_profile_subscription(profile_obj)
    return render(
        request,
        'creator_subscriptions/profile.html',
        {'profile': profile_obj},
    )


@login_required
@require_http_methods(['GET', 'POST'])
def connect_x_mock(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    form = MockXConnectForm(request.POST or None, initial={'x_user_id': profile_obj.x_user_id})

    if request.method == 'POST' and form.is_valid():
        try:
            link_x_account(request.user, form.cleaned_data['x_user_id'])
        except ValidationError as exc:
            form.add_error('x_user_id', exc)
        else:
            refresh_profile_subscription(request.user.profile, force=True)
            messages.success(request, 'X account connected.')
            return redirect('creator_subscriptions:profile')

    return render(
        request,
        'creator_subscriptions/connect_x_mock.html',
        {'form': form, 'profile': profile_obj},
    )


@require_http_methods(['GET', 'POST'])
def mock_x_sign_in(request):
    if request.user.is_authenticated:
        return redirect('creator_subscriptions:profile')

    form = MockXSignInForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = _user_for_mock_x_login(
            form.cleaned_data['x_user_id'],
            form.cleaned_data.get('confirmed_email', ''),
        )
        login(request, user, backend=AUTH_BACKEND)
        refresh_profile_subscription(user.profile, force=True)
        messages.success(request, 'Signed in with the mock X account.')
        return redirect('creator_subscriptions:profile')

    return render(request, 'creator_subscriptions/mock_x_sign_in.html', {'form': form})


@login_required
def members_only(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    refresh_profile_subscription(profile_obj)

    if not profile_obj.is_x_subscriber:
        return render(
            request,
            'creator_subscriptions/members_denied.html',
            {'profile': profile_obj},
            status=403,
        )

    return render(
        request,
        'creator_subscriptions/members_only.html',
        {'profile': profile_obj},
    )


def _user_for_mock_x_login(x_user_id, confirmed_email):
    existing_profile = Profile.objects.select_related('user').filter(x_user_id=x_user_id).first()
    if existing_profile:
        return existing_profile.user

    user = None
    if confirmed_email:
        user = User.objects.filter(email__iexact=confirmed_email).first()

    if user is None:
        user = User(username=_unique_username_for_x_id(x_user_id), email=confirmed_email)
        user.set_unusable_password()
        user.save()
        _mark_primary_email(user, verified=True)

    link_x_account(user, x_user_id)
    return user


def _unique_username_for_x_id(x_user_id):
    base = slugify(f'x-{x_user_id}')[:130] or 'x-user'
    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f'{base[:145]}-{suffix}'
    return username


def _mark_primary_email(user, verified):
    if not user.email:
        return None

    email_address, _ = EmailAddress.objects.get_or_create(
        user=user,
        email=user.email.lower(),
        defaults={'primary': True, 'verified': verified},
    )
    if not email_address.primary or email_address.verified != verified:
        email_address.primary = True
        email_address.verified = verified
        email_address.save(update_fields=['primary', 'verified'])
    return email_address
