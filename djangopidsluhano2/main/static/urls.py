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
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path('', views.feed, name='feed'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/new/', views.post_create, name='post_create'),
    path('post/<int:pk>/like/', views.post_like, name='post_like'),
    path('register/', views.register, name='register'),
    path('rules/', TemplateView.as_view(template_name='rules.html'), name='rules'),

    # Допиши сам на своїх етапах:
    # path('search/', views.search, name='search'),
    # path('notifications/', views.notifications, name='notifications'),
    # path('profile/', views.profile, name='profile'),
    # path('profile/edit/', views.profile_edit, name='profile_edit'),
    # path('u/<str:username>/', views.user_profile, name='user_profile'),
    # path('post/<int:pk>/report/', views.post_report, name='post_report'),
]
