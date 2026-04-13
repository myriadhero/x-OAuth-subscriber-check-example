from django.shortcuts import get_object_or_404, render

from creator_subscriptions.models import Profile
from creator_subscriptions.services import refresh_profile_subscription

from .models import BlogPost


TIER_RANK = {
    BlogPost.AccessTier.PUBLIC: 0,
    BlogPost.AccessTier.BASIC: 1,
    BlogPost.AccessTier.PREMIUM: 2,
    BlogPost.AccessTier.PREMIUM_PLUS: 3,
}


def post_list(request):
    posts = BlogPost.objects.filter(is_published=True)
    profile = get_refreshed_profile(request.user)
    accessible_posts = []
    locked_posts = []

    for post in posts:
        if user_can_access_post(request.user, post, profile):
            accessible_posts.append(post)
        else:
            locked_posts.append(post)

    return render(
        request,
        'blog/post_list.html',
        {
            'accessible_posts': accessible_posts,
            'locked_posts': locked_posts,
            'posts': posts,
            'profile': profile,
        },
    )


def post_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    profile = get_refreshed_profile(request.user)

    if not user_can_access_post(request.user, post, profile):
        return render(
            request,
            'blog/post_access_denied.html',
            {'post': post, 'profile': profile},
            status=403,
        )

    return render(request, 'blog/post_detail.html', {'post': post, 'profile': profile})


def get_refreshed_profile(user):
    if not user.is_authenticated:
        return None

    profile, _ = Profile.objects.get_or_create(user=user)
    refresh_profile_subscription(profile)
    return profile


def user_can_access_post(user, post, profile=None):
    if post.is_public:
        return True

    if not user.is_authenticated or not profile or not profile.is_x_subscriber:
        return False

    access_tier = profile.x_subscription_status.get('access_tier')
    return TIER_RANK.get(access_tier, 0) >= TIER_RANK[post.access_tier]
