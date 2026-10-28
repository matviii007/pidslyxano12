"""
ПРИКЛАД адмінки = панель модератора. posts/admin.py  (Етап 4 і 8)
Відкривається на /admin/ після: python manage.py createsuperuser
"""
from django.contrib import admin
from django import forms
from django.forms.models import modelform_factory
from django.db.models import Q

from .models import Event, ModeratorPermissions, Notification, Post, Profile, Reply, Report, Tag


def _moderator_role(user):
    return Profile.objects.filter(user_id=user.pk).values_list('role', flat=True).first()


def _has_full_admin_access(user):
    role = _moderator_role(user)
    if user.is_superuser or role == Profile.ROLE_ADMIN:
        return True
    if role in (Profile.ROLE_JUNIOR_MODERATOR, Profile.ROLE_SENIOR_MODERATOR):
        return False
    return user.is_staff


def _has_moderation_permission(user, permission):
    if _has_full_admin_access(user):
        return True
    role = _moderator_role(user)
    return bool(
        user.is_staff
        and role
        and ModeratorPermissions.objects.filter(role=role, **{permission: True}).exists()
    )


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['text', 'author', 'tag', 'is_anonymous', 'is_moderation', 'is_approved', 'is_pinned', 'created_at']
    list_filter = ['is_approved', 'is_anonymous', 'is_moderation', 'tag']   # фільтри справа
    search_fields = ['text']
    actions = ['approve', 'reject', 'toggle_pin']

    def has_module_permission(self, request):
        return _has_full_admin_access(request.user) or any(
            _has_moderation_permission(request.user, permission)
            for permission in (
                'can_approve_posts',
                'can_reject_posts',
                'can_pin_posts',
            )
        )

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return _has_full_admin_access(request.user)

    def has_delete_permission(self, request, obj=None):
        return _has_full_admin_access(request.user)

    def get_readonly_fields(self, request, obj=None):
        if _has_full_admin_access(request.user):
            return ()
        return tuple(field.name for field in self.model._meta.fields)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if _has_full_admin_access(request.user):
            return queryset

        can_review = (
            _has_moderation_permission(request.user, 'can_approve_posts')
            or _has_moderation_permission(request.user, 'can_reject_posts')
        )
        can_pin = _has_moderation_permission(request.user, 'can_pin_posts')
        if can_review and can_pin:
            return queryset.filter(
                Q(is_approved=False, is_rejected=False) | Q(is_approved=True)
            )
        if can_review:
            return queryset.filter(is_approved=False, is_rejected=False)
        if can_pin:
            return queryset.filter(is_approved=True)
        return queryset.none()

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not _has_full_admin_access(request.user):
            permissions = {
                'approve': 'can_approve_posts',
                'reject': 'can_reject_posts',
                'toggle_pin': 'can_pin_posts',
            }
            for action, permission in permissions.items():
                if not _has_moderation_permission(request.user, permission):
                    actions.pop(action, None)
            actions.pop('delete_selected', None)
        return actions

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change:
            previous_status = Post.objects.filter(pk=obj.pk).values(
                'is_approved', 'is_rejected',
            ).first()
        super().save_model(request, obj, form, change)
        if obj.is_approved:
            obj.materialize_pending_tag()
        if previous_status and obj.is_approved and not previous_status['is_approved']:
            Notification.objects.create(
                recipient=obj.author,
                actor=request.user,
                post=obj,
                kind=Notification.POST_APPROVED,
            )
        elif previous_status and obj.is_rejected and not previous_status['is_rejected']:
            Notification.objects.create(
                recipient=obj.author,
                actor=request.user,
                post=obj,
                kind=Notification.POST_REJECTED,
            )

    @admin.action(description='Схвалити вибрані дописи')
    def approve(self, request, queryset):
        if not _has_moderation_permission(request.user, 'can_approve_posts'):
            return
        for post in queryset.filter(is_approved=False, is_rejected=False):
            if not post.is_approved:
                post.is_approved = True
                post.save(update_fields=['is_approved'])
                Notification.objects.create(
                    recipient=post.author,
                    actor=request.user,
                    post=post,
                    kind=Notification.POST_APPROVED,
                )
            post.materialize_pending_tag()

    @admin.action(description='Відхилити вибрані дописи')
    def reject(self, request, queryset):
        if not _has_moderation_permission(request.user, 'can_reject_posts'):
            return
        for post in queryset.filter(is_approved=False, is_rejected=False):
            post.is_rejected = True
            post.save(update_fields=['is_rejected'])
            Notification.objects.create(
                recipient=post.author,
                actor=request.user,
                post=post,
                kind=Notification.POST_REJECTED,
            )

    @admin.action(description='Закріпити / відкріпити вибрані дописи')
    def toggle_pin(self, request, queryset):
        if not _has_moderation_permission(request.user, 'can_pin_posts'):
            return
        for post in queryset.filter(is_approved=True):
            post.is_pinned = not post.is_pinned
            post.save(update_fields=['is_pinned'])


@admin.register(ModeratorPermissions)
class ModeratorPermissionsAdmin(admin.ModelAdmin):
    list_display = ['role', 'can_approve_posts', 'can_reject_posts', 'can_manage_reports',
                    'can_pin_posts', 'can_publish_as_moderation']
    list_editable = ['can_approve_posts', 'can_reject_posts', 'can_manage_reports',
                     'can_pin_posts', 'can_publish_as_moderation']
    ordering = ['role']

    def has_module_permission(self, request):
        return _has_full_admin_access(request.user)

    def has_view_permission(self, request, obj=None):
        return _has_full_admin_access(request.user)

    def has_add_permission(self, request):
        return _has_full_admin_access(request.user)

    def has_change_permission(self, request, obj=None):
        return _has_full_admin_access(request.user)

    def has_delete_permission(self, request, obj=None):
        return _has_full_admin_access(request.user)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['post', 'reason', 'author', 'created_at']
    list_filter = ['reason']

    def has_module_permission(self, request):
        return _has_moderation_permission(request.user, 'can_manage_reports')

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return _has_full_admin_access(request.user)

    def has_delete_permission(self, request, obj=None):
        return _has_full_admin_access(request.user)

    def get_readonly_fields(self, request, obj=None):
        if _has_full_admin_access(request.user):
            return ()
        return tuple(field.name for field in self.model._meta.fields)


admin.site.register(Tag)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'starts_at', 'location', 'is_published']
    list_filter = ['is_published', 'starts_at']
    list_editable = ['is_published']
    search_fields = ['title', 'location', 'description']
    ordering = ['starts_at']

    def has_module_permission(self, request):
        return _has_full_admin_access(request.user)

    def has_view_permission(self, request, obj=None):
        return _has_full_admin_access(request.user)

    def has_add_permission(self, request):
        return _has_full_admin_access(request.user)

    def has_change_permission(self, request, obj=None):
        return _has_full_admin_access(request.user)

    def has_delete_permission(self, request, obj=None):
        return _has_full_admin_access(request.user)


class ProfileAdminForm(forms.ModelForm):
    SCHOOL_CLASSES = [
        f'{grade}-{letter}'
        for grade in range(5, 12)
        for letter in ('А', 'Б', 'В')
    ]
    school_class = forms.ChoiceField(
        label='Клас',
        required=False,
        choices=[('', 'Не вказано'), *((school_class, school_class) for school_class in SCHOOL_CLASSES)],
    )

    class Meta:
        model = Profile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_class = self.instance.school_class
        if current_class and current_class not in self.SCHOOL_CLASSES:
            self.fields['school_class'].choices += [(current_class, current_class)]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    form = ProfileAdminForm
    list_display = ['user', 'school_class', 'role', 'is_verified']
    list_filter = ['role', 'school_class']
    list_editable = ['school_class', 'role', 'is_verified']
    search_fields = ['user__username', 'user__first_name']

    def get_changelist_form(self, request, **kwargs):
        defaults = {'form': self.form}
        defaults.update(kwargs)
        return modelform_factory(self.model, **defaults)

    def has_module_permission(self, request):
        return _has_full_admin_access(request.user)

    def has_view_permission(self, request, obj=None):
        return _has_full_admin_access(request.user)

    def has_add_permission(self, request):
        return _has_full_admin_access(request.user)

    def has_change_permission(self, request, obj=None):
        return _has_full_admin_access(request.user)

    def has_delete_permission(self, request, obj=None):
        return _has_full_admin_access(request.user)

admin.site.register(Reply)
admin.site.register(Notification)
