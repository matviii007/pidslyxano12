"""ПРИКЛАД форм. posts/forms.py"""
import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Post, Profile, Reply, Report, Tag

MAX_IMAGE_SIZE = 5 * 1024 * 1024


class UkrainianClearableFileInput(forms.ClearableFileInput):
    clear_checkbox_label = 'Видалити поточний файл'
    initial_text = 'Поточний файл'
    input_text = 'Замінити'


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = 'Нікнейм'
        self.fields['password'].widget.attrs['placeholder'] = 'Пароль'


class PostForm(forms.ModelForm):
    """Форма допису; режим публікації від модерації доступний лише довіреним ролям."""

 
    new_tag_name = forms.CharField(
        label='Створи кастомний хештег',
        required=False,
        max_length=31,
        widget=forms.TextInput(attrs={
            'placeholder': 'Наприклад, #шкільні_новини',
            'maxlength': 31,
        }),
    )
    as_moderation = forms.BooleanField(
        label='Опублікувати від імені «Модерація»',
        required=False,
        widget=forms.CheckboxInput(attrs={'data-moderation-toggle': ''}),
    )

    class Meta:
        model = Post
        fields = ['text', 'image', 'tag', 'is_anonymous']
        widgets = {
            'text': forms.Textarea(attrs={
                'maxlength': 500,
                'rows': 6,
                'placeholder': 'Що почув(-ла) сьогодні в ліцеї?',
                'required': True,
                'data-counter': '',
            }),
            'image': UkrainianClearableFileInput(attrs={'accept': 'image/*'}),
            'is_anonymous': forms.CheckboxInput(attrs={'data-anon-toggle': ''}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and image.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError('Розмір фото не може перевищувати 5 МБ.')
        return image

    def __init__(self, *args, allow_moderation=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_moderation = allow_moderation
        if not allow_moderation:
            self.fields.pop('as_moderation')

    def clean_new_tag_name(self):
        name = self.cleaned_data['new_tag_name'].strip()
        if not name:
            return ''

        if name.startswith('#'):
            name = name[1:]
        name = name.lower()

        if not name or len(name) > 30 or not re.fullmatch(r'\w+', name, re.UNICODE):
            raise forms.ValidationError(
                'Хештег має містити лише літери, цифри або підкреслення та бути до 30 символів.'
            )
        return name

    def clean(self):
        cleaned_data = super().clean()
        tag = cleaned_data.get('tag')
        new_tag_name = cleaned_data.get('new_tag_name')
 
        if cleaned_data.get('as_moderation') and cleaned_data.get('is_anonymous'):
            raise forms.ValidationError(
                'Обери анонімну публікацію або публікацію від імені «Модерація».'
            )

        if tag and new_tag_name:
            raise forms.ValidationError('Обери наявний хештег або створи новий, не обидва.')
        if new_tag_name:
            existing_tag = Tag.objects.filter(name__iexact=new_tag_name).first()
            if existing_tag:
                cleaned_data['tag'] = existing_tag
                cleaned_data['new_tag_name'] = ''

        return cleaned_data


class ReplyForm(forms.ModelForm):
    """Етап 6."""
    class Meta:
        model = Reply
        fields = ['text', 'is_anonymous']


class ReportForm(forms.ModelForm):
    reason = forms.ChoiceField(
        label='Причина скарги',
        choices=[('', '— Оберіть причину —'), *Report.REASONS],
        widget=forms.Select(),
    )

    class Meta:
        model = Report
        fields = ['reason', 'comment']
        labels = {
            'comment': 'Коментар (необов’язково)',
        }


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='Ім’я та прізвище', max_length=40)
    username = forms.CharField(label='Нікнейм', max_length=20)
    school_class = forms.ChoiceField(
        label='Клас',
        choices=[
            ('', 'Не вказано'),
            *[
                (f'{grade}-{letter}', f'{grade}-{letter}')
                for grade in range(5, 12)
                for letter in ('А', 'Б', 'В')
            ],
        ],
        required=False,
    )

    class Meta:
        model = Profile
        fields = ['school_class', 'bio', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
            'avatar': forms.FileInput(attrs={
                'accept': 'image/*',
                'data-avatar-input': '',
            }),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and avatar.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError('Розмір фото не може перевищувати 5 МБ.')
        return avatar

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_class = self.instance.school_class
        if current_class and current_class not in dict(self.fields['school_class'].choices):
            self.fields['school_class'].choices += [(current_class, current_class)]
        self.fields['first_name'].initial = self.instance.user.first_name
        self.fields['username'].initial = self.instance.user.username

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exclude(pk=self.instance.user_id).exists():
            raise forms.ValidationError('Цей нікнейм уже зайнятий.')
        return username


class RegisterForm(UserCreationForm):
    """Етап 7. UserCreationForm вже вміє username + password1 + password2,
    ми лише додаємо ім'я і клас."""
    first_name = forms.CharField(label='Ім’я та прізвище', max_length=40)
    school_class = forms.ChoiceField(
        label='Клас',
        choices=[
            ('', 'Обери свій клас'),
            *[
                (f'{grade}-{letter}', f'{grade}-{letter}')
                for grade in range(5, 12)
                for letter in ('А', 'Б', 'В')
            ],
        ],
    )
    rules_accepted = forms.BooleanField(label='Я прочитав(-ла) правила')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Нікнейм (латиницею)', 'autocomplete': 'username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs.update({'placeholder': 'Ім’я та прізвище'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Пароль', 'autocomplete': 'new-password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Повтори пароль', 'autocomplete': 'new-password'})
