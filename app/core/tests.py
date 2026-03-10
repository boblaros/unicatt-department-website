from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from posts.models import Post

from .models import WallPost


class WallPostValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='student@unicatt.it',
            password='StudentPass123!',
            full_name='Student Example',
            study_program='medicine',
            year_of_study='1',
            country_of_origin='IT',
            is_verified_student=True,
        )

    def test_wall_post_rejects_cycles(self):
        root = WallPost.objects.create(author=self.user, body='Root post')
        child = WallPost.objects.create(author=self.user, body='Reply', parent=root)
        root.parent = child

        with self.assertRaises(ValidationError):
            root.save()


class HomeWallThreadTemplateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='student@unicatt.it',
            password='StudentPass123!',
            full_name='Student Example',
            study_program='medicine',
            year_of_study='1',
            country_of_origin='IT',
            is_verified_student=True,
        )
        Post.objects.create(
            title_it='Titolo',
            title_en='Title',
            body_it='Corpo',
            body_en='Body',
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        root = WallPost.objects.create(author=self.user, body='Root post')
        WallPost.objects.create(author=self.user, body='Reply post', parent=root)

    def test_home_renders_original_wall_thread_markup(self):
        response = self.client.get(reverse('core:home'))

        self.assertContains(response, 'class="posts wall-thread-list"')
        self.assertContains(response, 'class="comment-card wall-thread-item depth-1"')
        self.assertContains(response, 'class="wall-replies"')

    def test_home_links_wall_author_name_to_public_profile(self):
        response = self.client.get(reverse('core:home'))

        self.assertContains(response, reverse('accounts:public_profile', args=[self.user.pk]))

    def test_unverified_user_does_not_see_wall_post_forms(self):
        unverified_user = User.objects.create_user(
            email='unverified@unicatt.it',
            password='StudentPass123!',
            full_name='Unverified Example',
            study_program='medicine',
            year_of_study='1',
            country_of_origin='IT',
            is_verified_student=False,
        )
        self.client.force_login(unverified_user)

        response = self.client.get(reverse('core:home'))

        self.assertContains(response, 'Only verified students can post on the wall.')
        self.assertNotContains(response, 'id="wall-form"')
        self.assertNotContains(response, 'id="wall-reply-form-')


class WallPostPermissionTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email='author@unicatt.it',
            password='StudentPass123!',
            full_name='Author Example',
            study_program='medicine',
            year_of_study='1',
            country_of_origin='IT',
            is_verified_student=True,
        )
        self.unverified_user = User.objects.create_user(
            email='unverified@unicatt.it',
            password='StudentPass123!',
            full_name='Unverified Example',
            study_program='medicine',
            year_of_study='2',
            country_of_origin='IT',
            is_verified_student=False,
        )
        self.wall_post = WallPost.objects.create(author=self.author, body='Root post')

    def test_unverified_user_cannot_create_root_wall_post(self):
        self.client.force_login(self.unverified_user)

        response = self.client.post(reverse('core:create_wall_post'), {'body': 'New wall post'})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content.decode(), 'Only verified students can post on the wall.')
        self.assertEqual(WallPost.objects.count(), 1)

    def test_unverified_user_cannot_create_wall_reply_via_ajax(self):
        self.client.force_login(self.unverified_user)

        response = self.client.post(
            reverse('core:create_wall_post'),
            {'body': 'Reply', 'parent_id': self.wall_post.pk},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(
            response.content,
            {'ok': False, 'error': 'Only verified students can post on the wall.'},
        )
        self.assertEqual(WallPost.objects.count(), 1)


class WallPostDeletionTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email='author@unicatt.it',
            password='StudentPass123!',
            full_name='Author Example',
            study_program='medicine',
            year_of_study='1',
            country_of_origin='IT',
            is_verified_student=True,
        )
        self.moderator = User.objects.create_user(
            email='moderator@unicatt.it',
            password='ModeratorPass123!',
            full_name='Moderator Example',
            study_program='medicine',
            year_of_study='2',
            country_of_origin='IT',
            is_verified_student=True,
            is_moderator=True,
        )
        self.other_user = User.objects.create_user(
            email='other@unicatt.it',
            password='StudentPass123!',
            full_name='Other Example',
            study_program='medicine',
            year_of_study='3',
            country_of_origin='IT',
            is_verified_student=True,
        )
        self.wall_post = WallPost.objects.create(author=self.author, body='Root post')
        self.reply = WallPost.objects.create(author=self.author, body='Reply post', parent=self.wall_post)

    def test_author_can_soft_delete_own_wall_post(self):
        self.client.force_login(self.author)

        response = self.client.post(reverse('core:delete_wall_post', kwargs={'pk': self.wall_post.pk}))

        self.assertRedirects(response, f"{reverse('core:home')}#wall")
        self.wall_post.refresh_from_db()
        self.assertTrue(self.wall_post.soft_deleted)
        self.assertEqual(self.wall_post.deleted_by, self.author)

    def test_moderator_can_soft_delete_wall_post_without_removing_replies(self):
        self.client.force_login(self.moderator)

        response = self.client.post(reverse('core:delete_wall_post', kwargs={'pk': self.wall_post.pk}))

        self.assertRedirects(response, f"{reverse('core:home')}#wall")
        self.wall_post.refresh_from_db()
        self.reply.refresh_from_db()
        self.assertTrue(self.wall_post.soft_deleted)
        self.assertEqual(self.wall_post.deleted_by, self.moderator)
        self.assertEqual(self.wall_post.body, '[deleted]')
        self.assertEqual(self.reply.parent, self.wall_post)

    def test_other_student_cannot_delete_wall_post(self):
        self.client.force_login(self.other_user)

        response = self.client.post(reverse('core:delete_wall_post', kwargs={'pk': self.wall_post.pk}))

        self.assertEqual(response.status_code, 403)
        self.wall_post.refresh_from_db()
        self.assertFalse(self.wall_post.soft_deleted)

    def test_delete_control_visible_only_to_author_or_privileged_users(self):
        self.client.force_login(self.author)
        author_response = self.client.get(reverse('core:home'))
        self.assertContains(author_response, reverse('core:delete_wall_post', kwargs={'pk': self.wall_post.pk}))
        self.assertContains(author_response, 'thread-action-btn thread-action-btn-danger')

        self.client.force_login(self.other_user)
        other_response = self.client.get(reverse('core:home'))
        self.assertNotContains(other_response, reverse('core:delete_wall_post', kwargs={'pk': self.wall_post.pk}))

        self.client.force_login(self.moderator)
        moderator_response = self.client.get(reverse('core:home'))
        self.assertContains(moderator_response, reverse('core:delete_wall_post', kwargs={'pk': self.wall_post.pk}))
        self.assertContains(moderator_response, 'thread-action-btn thread-action-btn-danger')
        self.assertContains(moderator_response, 'js-thread-delete-form')

    def test_ajax_delete_rejects_other_student(self):
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse('core:delete_wall_post', kwargs={'pk': self.wall_post.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(response.content, {'ok': False, 'error': 'You cannot delete this wall post.'})
        self.wall_post.refresh_from_db()
        self.assertFalse(self.wall_post.soft_deleted)

    def test_deleted_wall_post_disappears_from_home(self):
        self.wall_post.soft_delete(self.moderator)
        self.client.force_login(self.moderator)

        response = self.client.get(reverse('core:home'))

        self.assertContains(response, 'No posts yet. Be the first one.')
        self.assertNotContains(response, '[deleted]')
        self.assertNotContains(response, 'Reply post')
        self.assertNotContains(response, reverse('core:delete_wall_post', kwargs={'pk': self.wall_post.pk}))
        self.assertNotContains(response, 'name="parent_id" value="%s"' % self.wall_post.pk)

    def test_ajax_delete_marks_wall_item_as_removed_without_redirect(self):
        self.client.force_login(self.moderator)

        response = self.client.post(
            reverse('core:delete_wall_post', kwargs={'pk': self.wall_post.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['removed'])
        self.assertNotIn('html', data)
        self.wall_post.refresh_from_db()
        self.assertTrue(self.wall_post.soft_deleted)
