"""
ПРИКЛАД кількох view. posts/views.py
Тут показано лише головні. Решту (пошук, профіль, сповіщення) напиши сам
за тим самим зразком — підказки в README.
"""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm, RegisterForm, ReplyForm
from .models import Post, Profile, Tag


@login_required
def feed(request):
    """Стрічка. Шаблон: feed.html  (Етап 5)"""
    posts = Post.objects.filter(is_approved=True).select_related('author', 'tag')

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

    return render(request, 'feed.html', {
        'posts': posts,
        'tags': Tag.objects.all(),
        'active_tab': active_tab,
        'active_topic': active_topic,
    })


@login_required
def post_detail(request, pk):
    """Сторінка допису з відповідями. Шаблон: post_detail.html  (Етап 6)"""
    post = get_object_or_404(Post, pk=pk, is_approved=True)

    if request.method == 'POST':
        form = ReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)   # ще не зберігаємо в базу...
            reply.post = post                 # ...спершу допишемо, до якого допису
            reply.author = request.user       # ...і хто автор
            reply.save()
            messages.success(request, 'Відповідь додано')
            return redirect('post_detail', pk=post.pk)
    else:
        form = ReplyForm()

    return render(request, 'post_detail.html', {
        'post': post,
        'replies': post.replies.select_related('author'),
        'form': form,
    })


@login_required
def post_create(request):
    """Новий допис. Шаблон: post_form.html  (Етап 8)"""
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            # Звичайні дописи публікуються одразу, анонімні — чекають модератора
            post.is_approved = not post.is_anonymous
            post.save()
            if post.is_anonymous:
                messages.success(request, 'Надіслано на модерацію. Зазвичай до 15 хв')
            else:
                messages.success(request, 'Допис опубліковано')
            return redirect('feed')
    else:
        form = PostForm()
    return render(request, 'post_form.html', {'form': form, 'tags': Tag.objects.all()})


@login_required
def post_like(request, pk):
    """Лайк / зняти лайк. Працює лише через POST. (Етап 9)"""
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        if post.likes.filter(pk=request.user.pk).exists():
            post.likes.remove(request.user)
        else:
            post.likes.add(request.user)
    # Повертаємось на ту сторінку, звідки натиснули лайк
    return redirect(request.META.get('HTTP_REFERER', 'feed'))


def register(request):
    """Реєстрація. Шаблон: registration/register.html  (Етап 7)"""
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
    return render(request, 'registration/register.html', {'form': form})
