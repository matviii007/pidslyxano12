import re

from django.contrib.auth.models import User

from .models import Notification


def notify_mentions(text, actor, post, is_anonymous=False):
    usernames = {
        username.casefold()
        for username in re.findall(
            r'(?<![\w@])@([\w](?:[\w.+-]*[\w])?)',
            text,
        )
    }
    if not usernames:
        return

    users = User.objects.filter(is_active=True).exclude(pk=actor.pk)
    for username in usernames:
        user = users.filter(username__iexact=username).first()
        if user:
            Notification.objects.create(
                recipient=user,
                actor=None if is_anonymous else actor,
                kind=Notification.MENTION,
                post=post,
                message=text[:120],
            )
