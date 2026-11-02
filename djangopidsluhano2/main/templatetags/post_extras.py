import re

from django import template
from django.contrib.auth.models import User
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe
from django.urls import reverse

register = template.Library()


@register.filter
def mentionify(value):
    text = str(value or '')
    parts = []
    start = 0
    for match in re.finditer(r'(?<![\w@])@([\w](?:[\w.+-]*[\w])?)', text):
        parts.append(conditional_escape(text[start:match.start()]))
        username = match.group(1)
        user = User.objects.filter(username__iexact=username).first()
        if user:
            parts.append(format_html(
                '<a class="mention" href="{}">@{}</a>',
                reverse('user_profile', kwargs={'username': user.username}),
                user.username,
            ))
        else:
            parts.append(conditional_escape(match.group(0)))
        start = match.end()
    parts.append(conditional_escape(text[start:]))
    return mark_safe(''.join(parts))
