"""
ПРИКЛАД маршрутів. posts/urls.py

Не забудь підключити їх у головному config/urls.py:

    from django.contrib import admin
    from django.urls import include, path

    urlpatterns = [
        path('admin/', admin.site.urls),
        path('', include('django.contrib.auth.urls')),   # /login/, /logout/ готові від Django
        path('', include('posts.urls')),
    ]
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from . import views
from .forms import LoginForm

urlpatterns = [
    path(
        '',
        auth_views.LoginView.as_view(template_name='login.html', form_class=LoginForm),
        name='home',
    ),
    path('feed/', views.feed, name='feed'),
    path('feed.html', views.feed, name='feed_legacy'),
    path('feed/feed.html', views.feed, name='feed_legacy_nested'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='login.html', form_class=LoginForm),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/new/', views.post_create, name='post_create'),
    path('post/<int:pk>/like/', views.post_like, name='post_like'),
    path('post/<int:pk>/repost/', views.post_repost, name='post_repost'),
    path('register/', views.register, name='register'),
    path('search/', views.search, name='search'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/read/', views.notifications_mark_read, name='notifications_mark_read'),
 
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('u/<str:username>/', views.user_profile, name='user_profile'),
    path('u/<str:username>/follow/', views.toggle_follow, name='toggle_follow'),
    path('report/', views.report, name='report'),
    path('rules/', TemplateView.as_view(template_name='rules.html'), name='rules'),
]
