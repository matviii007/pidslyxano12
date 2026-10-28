from django.utils import timezone

from .models import Event, ModeratorPermissions, Profile


def upcoming_events(request):
    return {
        'upcoming_events': Event.objects.filter(
            is_published=True,
            starts_at__gte=timezone.now(),
        ).order_by('starts_at')[:3],
    }


def notification_counts(request):
    if not request.user.is_authenticated:
        return {
            'unread_notification_count': 0,
            'can_access_moderation': False,
        }
    role = Profile.objects.filter(user=request.user).values_list('role', flat=True).first()
    can_access_moderation = (
        request.user.is_staff
        or request.user.is_superuser
        or role == Profile.ROLE_ADMIN
    )
    if role and not can_access_moderation:
        permissions = ModeratorPermissions.objects.filter(role=role).values(
            'can_approve_posts',
            'can_reject_posts',
            'can_manage_reports',
            'can_pin_posts',
        ).first()
        can_access_moderation = bool(permissions and any(permissions.values()))
    return {
        'unread_notification_count': request.user.notifications.filter(is_read=False).count(),
        'can_access_moderation': can_access_moderation,
    }
