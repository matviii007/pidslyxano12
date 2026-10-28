"""
ПРИКЛАД моделей для «Підслухано у Ліцеї 8».
Скопіюй у свій застосунок posts/models.py на ЕТАПІ 4 (див. README).
Не обов'язково все одразу: почни з Tag і Post, решту додавай на своїх етапах.

Після кожної зміни моделей:
    python manage.py makemigrations
    python manage.py migrate
"""
from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Profile(models.Model):
    """Додаткові дані учня. У стандартного User є username, first_name, password,
    а клас і "про себе" ми зберігаємо тут. (Етап 7)"""
    ROLE_NONE = ''
    ROLE_JUNIOR_MODERATOR = 'junior_moderator'
    ROLE_SENIOR_MODERATOR = 'senior_moderator'
    ROLE_ADMIN = 'admin'
    ROLE_MODERATOR = ROLE_JUNIOR_MODERATOR
    ROLE_CHOICES = [
        (ROLE_NONE, 'No role'),
        (ROLE_JUNIOR_MODERATOR, 'Junior moderator'),
        (ROLE_SENIOR_MODERATOR, 'Senior moderator'),
        (ROLE_ADMIN, 'Administrator'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    school_class = models.CharField('Class', max_length=5)
    bio = models.CharField('About', max_length=160, blank=True)
    avatar = models.ImageField('Profile photo', upload_to='profile_images/', blank=True, null=True)
    color = models.CharField('Avatar color', max_length=7, default='#ff7a59')
    role = models.CharField('Role', max_length=20, choices=ROLE_CHOICES, blank=True, default=ROLE_NONE)
    is_verified = models.BooleanField('Verified account', default=False)
    # На кого підписаний. symmetrical=False: якщо я підписався на тебе, ти не підписаний на мене автоматично
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)

    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'

    def initials(self):
        """«Олена Коваль» -> «ОК». У шаблоні: {{ profile.initials }}"""
        name = self.user.first_name or self.user.username
        return ''.join(word[0] for word in name.split()[:2]).upper()

    def __str__(self):
        return f'{self.user.username} ({self.school_class})'


class Tag(models.Model):
    """Тема допису: #кохання, #їдальня ... (Етап 4)"""
    name = models.CharField('Name', max_length=30, unique=True)
    color = models.CharField('Color', max_length=7, default='#6b7f99')
    is_user_created = models.BooleanField('User-created', default=False)

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField('Назва', max_length=120)
    starts_at = models.DateTimeField('Дата й час')
    location = models.CharField('Місце проведення', max_length=120, blank=True)
    description = models.CharField('Додаткова інформація', max_length=240, blank=True)
    is_published = models.BooleanField('Опубліковано', default=True)

    class Meta:
        ordering = ['starts_at']
        verbose_name = 'Подія'
        verbose_name_plural = 'Події'

    def __str__(self):
        return self.title


class ModeratorPermissions(models.Model):
    role = models.CharField(
        'Moderation level',
        max_length=20,
        choices=[
            (Profile.ROLE_JUNIOR_MODERATOR, 'Junior moderator'),
            (Profile.ROLE_SENIOR_MODERATOR, 'Senior moderator'),
        ],
        unique=True,
    )
    can_approve_posts = models.BooleanField('Can approve posts', default=False)
    can_reject_posts = models.BooleanField('Can reject posts', default=False)
    can_manage_reports = models.BooleanField('Can manage reports', default=False)
    can_pin_posts = models.BooleanField('Can pin posts', default=False)
    can_publish_as_moderation = models.BooleanField(
        'Can publish as moderation',
        default=False,
    )

    class Meta:
        verbose_name = 'Moderator permissions'
        verbose_name_plural = 'Moderator permissions'
        ordering = ['role']

    def __str__(self):
        return self.get_role_display()


class Notification(models.Model):
    LIKE = 'like'
    REPLY = 'reply'
    REPOST = 'repost'
    FOLLOW = 'follow'
    POST_APPROVED = 'post_approved'
    POST_REJECTED = 'post_rejected'
    TYPE_CHOICES = [
        (LIKE, 'Like'),
        (REPLY, 'Reply'),
        (REPOST, 'Repost'),
        (FOLLOW, 'New follower'),
        (POST_APPROVED, 'Post approved'),
        (POST_REJECTED, 'Post rejected'),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Recipient',
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='sent_notifications',
        null=True,
        blank=True,
        verbose_name='Actor',
    )
    post = models.ForeignKey(
        'Post',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
        verbose_name='Post',
    )
    kind = models.CharField('Type', max_length=20, choices=TYPE_CHOICES)
    message = models.CharField('Message', max_length=300, blank=True)
    is_read = models.BooleanField('Read', default=False)
    created_at = models.DateTimeField('Created at', auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'is_read', '-created_at'])]

    def __str__(self):
        return f'{self.get_kind_display()} for {self.recipient}'


class Post(models.Model):
    """Допис у стрічці. (Етап 4)"""
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    text = models.TextField('Text', max_length=500)
    image = models.ImageField('Photo', upload_to='post_images/', blank=True, null=True)
    tag = models.ForeignKey(
        Tag,
        on_delete=models.PROTECT,
        related_name='posts',
        verbose_name='Tag',
        null=True,
        blank=True,
    )
    pending_tag_name = models.CharField('Pending tag name', max_length=30, blank=True)
    pending_tag_color = models.CharField('Pending tag color', max_length=7, blank=True)
    is_anonymous = models.BooleanField('Anonymous', default=True)
    is_moderation = models.BooleanField('Posted as moderation', default=False)
    # Анонімні дописи спочатку НЕ схвалені — модератор схвалює їх в адмінці
    is_approved = models.BooleanField('Approved by moderator', default=False)
    is_rejected = models.BooleanField('Rejected by moderator', default=False)
    is_pinned = models.BooleanField('Pinned', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)      # Етап 9
    reposts = models.ManyToManyField(User, related_name='reposted_posts', blank=True)  # Етап 9

    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        ordering = ['-is_pinned', '-created_at']   # закріплені зверху, далі найновіші

    def __str__(self):
        return self.text[:40]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.materialize_pending_tag()

    def materialize_pending_tag(self):
        if not self.is_approved or not self.pending_tag_name or self.tag_id:
            return

        tag, _ = Tag.objects.get_or_create(
            name=self.pending_tag_name,
            defaults={
                'color': self.pending_tag_color or '#6b7f99',
                'is_user_created': True,
            },
        )
        self.tag = tag
        self.pending_tag_name = ''
        self.pending_tag_color = ''
        self.save(update_fields=['tag', 'pending_tag_name', 'pending_tag_color'])


class PollOption(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=40)
    voters = models.ManyToManyField(User, related_name='poll_votes', blank=True)

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return self.text


class Reply(models.Model):
    """Відповідь (коментар) під дописом. (Етап 6)"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.CharField('Text', max_length=300)
    is_anonymous = models.BooleanField('Anonymous', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reply'
        verbose_name_plural = 'Replies'
        ordering = ['created_at']   # старі відповіді зверху, як у чаті


class Report(models.Model):
    """Скарга на допис. Видно в адмінці. (Етап 13)"""
    REASONS = [
        ('insult', 'Образи або цькування'),
        ('name', 'Розголошення справжнього імені без згоди'),
        ('photo', 'Чуже фото'),
        ('fake', 'Неправдива інформація'),
        ('spam', 'Спам'),
        ('other', 'Інше'),
    ]
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='Допис',
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Автор скарги')
    reason = models.CharField('Причина', max_length=10, choices=REASONS)
    comment = models.CharField('Коментар', max_length=300, blank=True)
    created_at = models.DateTimeField('Дата створення', auto_now_add=True)

    class Meta:
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
