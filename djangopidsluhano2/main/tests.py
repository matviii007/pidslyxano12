from io import BytesIO
import tempfile

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ModeratorPermissions, Notification, Post, Profile, Reply


def make_test_image():
    image = Image.new('RGB', (2, 2), color='red')
    image_file = BytesIO()
    image.save(image_file, format='PNG')
    return SimpleUploadedFile(
        'test-image.png',
        image_file.getvalue(),
        content_type='image/png',
    )


class AuthenticationPageTests(TestCase):
    def test_login_and_registration_render_forms(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

        response = self.client.get(reverse('register'))
        self.assertContains(response, 'placeholder="Ім’я та прізвище"')
        self.assertContains(response, 'placeholder="Нікнейм (латиницею)"')
        self.assertContains(response, 'placeholder="Повтори пароль"')


class SocialActionsTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='author', password='StrongPass#1234')
        Profile.objects.create(user=self.author, school_class='10-А')
        self.actor = User.objects.create_user(username='actor', password='StrongPass#1234')
        Profile.objects.create(user=self.actor, school_class='10-Б')
        self.post = Post.objects.create(
            author=self.author,
            text='Перевірочний допис',
            is_anonymous=False,
            is_approved=True,
        )
        self.client.force_login(self.actor)

    def test_repost_can_be_added_and_removed(self):
        response = self.client.post(reverse('post_repost', args=[self.post.pk]))
        self.assertRedirects(response, reverse('feed'))
        self.assertTrue(self.post.reposts.filter(pk=self.actor.pk).exists())
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.author,
                actor=self.actor,
                kind=Notification.REPOST,
                post=self.post,
            ).exists()
        )

        self.client.post(reverse('post_repost', args=[self.post.pk]))
        self.assertFalse(self.post.reposts.filter(pk=self.actor.pk).exists())

    def test_notification_list_is_private_and_mark_all_read(self):
        Notification.objects.create(
            recipient=self.actor,
            actor=self.author,
            post=self.post,
            kind=Notification.LIKE,
        )
        Notification.objects.create(
            recipient=self.actor,
            actor=self.author,
            post=self.post,
            kind=Notification.REPLY,
            message='Відповідь для вкладки',
        )
        response = self.client.get(reverse('notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'вподобав(-ла) ваш допис')
        self.assertContains(response, 'notif__badge--like')
        self.assertEqual(response.context['unread_count'], 2)

        replies_response = self.client.get(reverse('notifications'), {'tab': 'mentions'})
        self.assertContains(replies_response, 'Відповідь для вкладки')
        self.assertNotContains(replies_response, 'вподобав(-ла) ваш допис')

        invalid_tab_response = self.client.get(reverse('notifications'), {'tab': 'invalid'})
        self.assertEqual(invalid_tab_response.context['active_tab'], 'all')
        self.assertContains(invalid_tab_response, 'вподобав(-ла) ваш допис')

        self.client.post(reverse('notifications_mark_read'))
        self.assertFalse(self.actor.notifications.filter(is_read=False).exists())

    def test_search_uses_real_posts_and_profiles(self):
        response = self.client.get(reverse('search'), {'q': 'Перевірочний'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Перевірочний допис')
        self.assertNotContains(response, 'Вирішуємо раз і назавжди')

    def test_primary_navigation_destinations_render(self):
        urls = [
            reverse('feed'),
            reverse('search'),
            reverse('notifications'),
            reverse('profile'),
            reverse('profile_edit'),
            reverse('user_profile', args=[self.author.username]),
            reverse('post_detail', args=[self.post.pk]),
            reverse('report') + f'?post={self.post.pk}',
            reverse('rules'),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                if url == reverse('profile_edit'):
                    self.assertContains(response, 'data-avatar-crop-modal')
                    self.assertContains(response, 'data-avatar-filename')
                    self.assertContains(response, 'Обрати фото')

    def test_post_author_avatar_links_to_profile(self):
        profile_url = reverse('user_profile', args=[self.author.username])
        feed_response = self.client.get(reverse('feed'))
        detail_response = self.client.get(reverse('post_detail', args=[self.post.pk]))

        self.assertContains(feed_response, f'href="{profile_url}"')
        self.assertContains(detail_response, f'href="{profile_url}"')

    def test_post_can_be_created_with_an_image(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(reverse('post_create'), {
                    'text': 'Допис із фото',
                    'is_anonymous': 'on',
                    'image': make_test_image(),
                })

                self.assertRedirects(response, reverse('feed'))
                post = Post.objects.get(text='Допис із фото')
                self.assertTrue(post.image.name.startswith('post_images/'))

                post.is_approved = True
                post.save(update_fields=['is_approved'])
                feed_response = self.client.get(reverse('feed'))
                self.assertContains(feed_response, post.image.url)

    def test_profile_can_be_saved_with_a_photo(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(reverse('profile_edit'), {
                    'first_name': 'Actor Student',
                    'username': 'actor',
                    'school_class': '10-Б',
                    'bio': 'Про себе',
                    'avatar': make_test_image(),
                })

                self.assertRedirects(response, reverse('profile'))
                self.actor.profile.refresh_from_db()
                self.assertTrue(
                    self.actor.profile.avatar.name.startswith('profile_images/')
                )
                profile_response = self.client.get(reverse('profile'))
                self.assertContains(profile_response, self.actor.profile.avatar.url)
                edit_response = self.client.get(reverse('profile_edit'))
                self.assertContains(edit_response, self.actor.profile.avatar.url)
                self.assertContains(edit_response, 'data-avatar-input')
                self.assertNotContains(edit_response, 'Поточний файл')
                self.assertNotContains(edit_response, 'Видалити поточний файл')

    def test_profile_replies_use_full_card_width(self):
        Reply.objects.create(
            post=self.post,
            author=self.actor,
            text='Тестова відповідь',
        )

        response = self.client.get(
            reverse('user_profile', args=[self.actor.username]),
            {'tab': 'replies'},
        )

        self.assertContains(response, 'class="post post--reply"')
        self.assertContains(response, 'Тестова відповідь')

    def test_logout_action_is_only_shown_on_own_profile(self):
        own_profile = self.client.get(reverse('profile'))
        other_profile = self.client.get(
            reverse('user_profile', args=[self.author.username])
        )

        self.assertContains(own_profile, 'action="/logout/"')
        self.assertContains(own_profile, 'profile__edit-btn')
        self.assertContains(own_profile, 'profile__logout-btn')
        self.assertNotContains(other_profile, 'action="/logout/"')

    def test_report_form_creates_report_for_selected_post(self):
        form_response = self.client.get(
            f"{reverse('report')}?post={self.post.pk}"
        )
        self.assertContains(form_response, '— Оберіть причину —')
        self.assertContains(form_response, 'Образи або цькування')
        self.assertContains(form_response, 'Розголошення справжнього імені без згоди')
        self.assertContains(form_response, 'Чуже фото')
        self.assertContains(form_response, 'Неправдива інформація')
        self.assertContains(form_response, 'Спам')
        self.assertContains(form_response, 'Інше')

        response = self.client.post(
            f"{reverse('report')}?post={self.post.pk}",
            {'post': self.post.pk, 'reason': 'spam', 'comment': 'Перевірка посилання'},
        )
        self.assertRedirects(response, reverse('post_detail', args=[self.post.pk]))
        self.assertTrue(self.post.reports.filter(author=self.actor, reason='spam').exists())

    def test_registration_creates_profile_and_logs_user_in(self):
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        response = self.client.post(reverse('register'), {
            'username': 'new_student',
            'first_name': 'Новий Учень',
            'school_class': '9-А',
            'password1': 'StrongPass#1234',
            'password2': 'StrongPass#1234',
            'rules_accepted': 'on',
        })
        self.assertRedirects(response, reverse('feed'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(
            Profile.objects.get(user__username='new_student').school_class,
            '9-А',
        )


class ModeratorPermissionsTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username='student', password='StrongPass#1234')
        Profile.objects.create(user=self.student, school_class='9-А')
        self.pending = Post.objects.create(
            author=self.student,
            text='На перевірці',
            is_approved=False,
        )
        ModeratorPermissions.objects.update_or_create(
            role=Profile.ROLE_JUNIOR_MODERATOR,
            defaults={'can_approve_posts': True},
        )

    def test_moderator_can_approve_from_django_admin_when_configured(self):
        moderator = User.objects.create_user(username='mod', password='StrongPass#1234')
        Profile.objects.create(
            user=moderator,
            school_class='11-А',
            role=Profile.ROLE_JUNIOR_MODERATOR,
        )
        moderator.is_staff = True
        moderator.save(update_fields=['is_staff'])
        self.client.force_login(moderator)
        response = self.client.post(
            reverse('admin:main_post_changelist'),
            {
                'action': 'approve',
                '_selected_action': [str(self.pending.pk)],
                'index': 0,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.pending.refresh_from_db()
        self.assertTrue(self.pending.is_approved)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                kind=Notification.POST_APPROVED,
            ).exists()
        )

    def test_moderator_cannot_change_role_or_permission_configuration(self):
        moderator = User.objects.create_user(
            username='mod',
            password='StrongPass#1234',
            is_staff=True,
        )
        Profile.objects.create(
            user=moderator,
            school_class='11-А',
            role=Profile.ROLE_JUNIOR_MODERATOR,
        )
        self.client.force_login(moderator)

        profile_response = self.client.get(reverse('admin:main_profile_changelist'))
        permissions_response = self.client.get(
            reverse('admin:main_moderatorpermissions_changelist')
        )

        self.assertEqual(profile_response.status_code, 403)
        self.assertEqual(permissions_response.status_code, 403)

    def test_website_moderation_routes_are_removed(self):
        self.assertEqual(self.client.get('/moderation/').status_code, 404)
