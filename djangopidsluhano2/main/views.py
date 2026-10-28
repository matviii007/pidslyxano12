"""
ПРИКЛАД кількох view. posts/views.py
Тут показано лише головні. Решту (пошук, профіль, сповіщення) напиши сам
за тим самим зразком — підказки в README.
"""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PostForm, ProfileForm, RegisterForm, ReplyForm, ReportForm
from .models import ModeratorPermissions, Notification, Post, Profile, Reply, Report, Tag


def _get_profile(user):
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={'school_class': ''},
    )
    return profile


def _has_moderation_access(user):
    return _can_moderate(user, 'can_publish_as_moderation')


def _can_moderate(user, permission):
    if user.is_superuser or user.is_staff:
        return True
    profile = Profile.objects.filter(user=user).first()
    if profile and profile.role == Profile.ROLE_ADMIN:
        return True
    return bool(
        profile
        and profile.role
        and ModeratorPermissions.objects.filter(
            role=profile.role,
            **{permission: True},
        ).exists()
    )


def _notify(recipient, actor, kind, post=None, message=''):
    if recipient != actor:
        Notification.objects.create(
            recipient=recipient,
            actor=actor,
            kind=kind,
            post=post,
            message=message,
        )


def _profile_posts(user):
    return Post.objects.filter(
        author=user,
        is_approved=True,
        is_anonymous=False,
        is_moderation=False,
    ).select_related('author', 'tag').prefetch_related(
        'author__profile',
        'likes',
        'replies',
        'reposts',
    )


def _profile_reposts(user):
    return user.reposted_posts.filter(is_approved=True).select_related(
        'author', 'tag',
    ).prefetch_related('author__profile', 'likes', 'replies', 'reposts')


def _profile_replies(user):
    return Reply.objects.filter(
        author=user,
        is_anonymous=False,
        post__is_approved=True,
        post__is_anonymous=False,
    ).select_related('author', 'post', 'post__tag').prefetch_related(
        'author__profile',
    )


@login_required
def feed(request):
    """Стрічка. Шаблон: feed.html  (Етап 5)"""
    posts = Post.objects.filter(is_approved=True).select_related(
        'author',
        'tag',
    ).prefetch_related(
        'author__profile',
    ).annotate(
        user_reposted=Count('reposts', filter=Q(reposts=request.user), distinct=True),
        user_liked=Count('likes', filter=Q(likes=request.user), distinct=True),
    )

    active_tab = request.GET.get('tab', 'all')      # all | anon | following
    active_topic = request.GET.get('topic')          # назва теми або None

    if active_tab == 'anon':
        posts = posts.filter(is_anonymous=True)
    elif active_tab == 'following':
        # ВАЖЛИВО: у "Підписках" лише НЕ анонімні дописи, інакше можна вгадати автора
        posts = posts.filter(is_anonymous=False,
                             author__profile__in=request.user.profile.following.all())

    if active_topic:
        posts = posts.filter(tag__name=active_topic)

    promotion_threshold = 10
    tags = Tag.objects.annotate(
        approved_post_count=Count('posts', filter=Q(posts__is_approved=True)),
    )
    primary_tags = tags.filter(
        Q(is_user_created=False)
        | Q(is_user_created=True, approved_post_count__gt=promotion_threshold)
    ).order_by('pk')
    custom_tags = tags.filter(
        is_user_created=True,
        approved_post_count__gt=0,
        approved_post_count__lte=promotion_threshold,
    ).order_by('-approved_post_count', 'name')

    return render(request, 'feed.html', {
        'posts': posts,
        'tags': primary_tags,
        'custom_tags': custom_tags,
        'active_tab': active_tab,
        'active_topic': active_topic,
    })


@login_required
def post_detail(request, pk):
    """Сторінка допису з відповідями. Шаблон: post_detail.html  (Етап 6)"""
    post = get_object_or_404(
        Post.objects.select_related('author', 'tag').prefetch_related(
            'author__profile',
            'likes',
        ),
        pk=pk,
        is_approved=True,
    )

    if request.method == 'POST':
        form = ReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)   # ще не зберігаємо в базу...
            reply.post = post                 # ...спершу допишемо, до якого допису
            reply.author = request.user       # ...і хто автор
            reply.save()
            _notify(post.author, request.user, Notification.REPLY, post, reply.text[:120])
            messages.success(request, 'Відповідь додано')
            return redirect('post_detail', pk=post.pk)
    else:
        form = ReplyForm()

    return render(request, 'post_detail.html', {
        'post': post,
        'replies': post.replies.select_related('author').prefetch_related(
            'author__profile',
        ),
        'form': form,
        'is_liked': post.likes.filter(pk=request.user.pk).exists(),
        'is_reposted': post.reposts.filter(pk=request.user.pk).exists(),
    })


@login_required
def post_create(request):
    """Новий допис. Шаблон: post_form.html  (Етап 8)"""
    can_post_as_moderation = _has_moderation_access(request.user)
    if request.method == 'POST':
        form = PostForm(
            request.POST,
            request.FILES,
            allow_moderation=can_post_as_moderation,
        )
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.is_moderation = (
                can_post_as_moderation
                and form.cleaned_data.get('as_moderation', False)
            )
            post.pending_tag_name = form.cleaned_data.get('new_tag_name', '')
            if post.is_moderation:
                post.is_anonymous = False
                post.is_approved = True
            else:
                post.is_approved = False
            post.save()
            if post.is_moderation:
                messages.success(request, 'Допис від імені «Модерація» опубліковано.')
            else:
                messages.success(request, 'Надіслано на модерацію. Зазвичай до 15 хв')
            return redirect('feed')
    else:
        form = PostForm(allow_moderation=can_post_as_moderation)
    return render(request, 'post_form.html', {
        'form': form,
        'tags': Tag.objects.order_by('pk'),
        'can_post_as_moderation': can_post_as_moderation,
        'as_moderation_checked': (
            bool(form['as_moderation'].value())
            if can_post_as_moderation else False
        ),
    })


@login_required
def post_like(request, pk):
    """Лайк / зняти лайк. Працює лише через POST. (Етап 9)"""
    post = get_object_or_404(Post, pk=pk, is_approved=True)
    if post.likes.filter(pk=request.user.pk).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
        _notify(post.author, request.user, Notification.LIKE, post)
    # Повертаємось на ту сторінку, звідки натиснули лайк
    return redirect(request.META.get('HTTP_REFERER', 'feed'))


@login_required
@require_POST
def post_repost(request, pk):
    post = get_object_or_404(Post, pk=pk, is_approved=True)
    if post.reposts.filter(pk=request.user.pk).exists():
        post.reposts.remove(request.user)
        messages.success(request, 'Репост скасовано.')
    else:
        post.reposts.add(request.user)
        _notify(post.author, request.user, Notification.REPOST, post)
        messages.success(request, 'Допис додано до ваших репостів.')
    return redirect(request.META.get('HTTP_REFERER', 'feed'))


def register(request):
    """Реєстрація нового учнівського облікового запису."""
    if request.user.is_authenticated:
        return redirect('feed')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user, school_class=form.cleaned_data['school_class'])
            login(request, user)
            messages.success(request, 'Вітаємо в «Підслухано»!')
            return redirect('feed')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


@login_required
def notifications(request):
    active_tab = request.GET.get('tab', 'all')
    if active_tab not in {'all', 'mentions'}:
        active_tab = 'all'

    items = request.user.notifications.select_related('actor', 'post', 'post__author')
    if active_tab == 'mentions':
        items = items.filter(kind=Notification.REPLY)
    return render(request, 'notifications.html', {
        'notifications': items,
        'unread_count': request.user.notifications.filter(is_read=False).count(),
        'active_tab': active_tab,
    })


@login_required
@require_POST
def notifications_mark_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, 'Усі сповіщення позначено прочитаними.')
    return redirect('notifications')


@login_required
def search(request):
    query = request.GET.get('q', '').strip()
    current_profile = _get_profile(request.user)
    following_profile_ids = set(
        current_profile.following.values_list('pk', flat=True),
    )
    posts = Post.objects.none()
    users = Profile.objects.none()
    popular_tags = Tag.objects.none()
    if query:
        posts = Post.objects.filter(
            is_approved=True,
        ).filter(
            Q(text__icontains=query)
            | Q(tag__name__icontains=query)
        ).select_related('author', 'tag').prefetch_related(
            'author__profile', 'likes', 'replies', 'reposts',
        )[:50]
        users = Profile.objects.filter(
            Q(user__username__icontains=query)
            | Q(user__first_name__icontains=query)
        ).select_related('user')[:20]
    else:
        popular_tags = Tag.objects.annotate(
            post_count=Count('posts', filter=Q(posts__is_approved=True)),
        ).filter(post_count__gt=0).order_by('-post_count', 'name')[:8]
        users = Profile.objects.filter(user__is_active=True).exclude(
            user=request.user,
        ).select_related('user').order_by('-user__date_joined')[:5]
    return render(request, 'search.html', {
        'query': query,
        'posts': posts,
        'users': users,
        'popular_tags': popular_tags,
        'has_results': bool(posts) or bool(users),
        'following_profile_ids': following_profile_ids,
    })


@login_required
def report(request):
    post_id = request.GET.get('post') or request.POST.get('post')
    post = get_object_or_404(Post, pk=post_id, is_approved=True)
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report_item = form.save(commit=False)
            report_item.post = post
            report_item.author = request.user
            report_item.save()
            messages.success(request, 'Дякуємо! Модератори перевірять скаргу.')
            return redirect('post_detail', pk=post.pk)
    else:
        form = ReportForm()
    return render(request, 'report.html', {'form': form, 'post': post})


@login_required
def profile(request):
    profile_data = _get_profile(request.user)
    posts = _profile_posts(request.user)
    return render(request, 'profile.html', {
        'profile_user': request.user,
        'profile_data': profile_data,
        'posts': posts,
        'reposted_posts': _profile_reposts(request.user),
        'replies': _profile_replies(request.user),
        'liked_posts': request.user.liked_posts.filter(
            is_approved=True,
            is_anonymous=False,
            is_moderation=False,
        ).select_related('author', 'tag').prefetch_related(
            'author__profile',
            'likes',
            'replies',
            'reposts',
        ),
        'post_count': posts.count(),
        'followers_count': profile_data.followers.count(),
        'following_count': profile_data.following.count(),
    })


@login_required
def profile_edit(request):
    profile_data = _get_profile(request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile_data)
        if form.is_valid():
            with transaction.atomic():
                profile_data = form.save(commit=False)
                user = profile_data.user
                user.first_name = form.cleaned_data['first_name']
                user.username = form.cleaned_data['username']
                user.save(update_fields=['first_name', 'username'])
                profile_data.save()
                form.save_m2m()
            messages.success(request, 'Профіль оновлено.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile_data)

    return render(request, 'profile_edit.html', {'form': form})


@login_required
def user_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile_data = _get_profile(profile_user)
    current_profile = _get_profile(request.user)
    posts = _profile_posts(profile_user)
    return render(request, 'user_profile.html', {
        'profile_user': profile_user,
        'profile_data': profile_data,
        'posts': posts,
        'replies': _profile_replies(profile_user),
        'post_count': posts.count(),
        'followers_count': profile_data.followers.count(),
        'following_count': profile_data.following.count(),
        'is_following': current_profile.following.filter(pk=profile_data.pk).exists(),
    })


@login_required
@require_POST
def toggle_follow(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        messages.error(request, 'Не можна підписатися на власний профіль.')
        return redirect('profile')

    current_profile = _get_profile(request.user)
    target_profile = _get_profile(target)
    if current_profile.following.filter(pk=target_profile.pk).exists():
        current_profile.following.remove(target_profile)
    else:
        current_profile.following.add(target_profile)
        _notify(target, request.user, Notification.FOLLOW)
    return redirect('user_profile', username=target.username)
