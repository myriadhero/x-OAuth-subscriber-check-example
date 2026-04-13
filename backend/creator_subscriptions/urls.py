from django.urls import path

from . import views


app_name = 'creator_subscriptions'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('connect-x/mock/', views.connect_x_mock, name='connect_x_mock'),
    path('sign-in-with-x/mock/', views.mock_x_sign_in, name='mock_x_sign_in'),
    path('members-only/', views.members_only, name='members_only'),
]
