from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from posts.models import Post

from .models import Comment


class CommentTreeValidationTests(TestCase):
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
        self.post = Post.objects.create(
            title_it='Titolo',
            title_en='Title',
            body_it='Corpo',
            body_en='Body',
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.other_post = Post.objects.create(
            title_it='Altro titolo',
            title_en='Other Title',
            body_it='Corpo',
            body_en='Body',
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
        )

    def make_comment(self, body, parent=None, post=None):
        return Comment.objects.create(
            post=post or self.post,
            author=self.user,
            parent=parent,
            body=body,
        )

    def test_save_rejects_self_parent(self):
        comment = self.make_comment('Root comment')
        comment.parent = comment

        with self.assertRaises(ValidationError):
            comment.save()

    def test_save_rejects_ancestor_cycle(self):
        root = self.make_comment('Root comment')
        child = self.make_comment('Child comment', parent=root)
        grandchild = self.make_comment('Grandchild comment', parent=child)
        root.parent = grandchild

        with self.assertRaises(ValidationError):
            root.save()

    def test_save_rejects_parent_from_another_post(self):
        foreign_parent = self.make_comment('Foreign parent', post=self.other_post)
        comment = Comment(post=self.post, author=self.user, parent=foreign_parent, body='Invalid child')

        with self.assertRaises(ValidationError):
            comment.save()

    def test_valid_nested_comments_keep_finite_depth(self):
        root = self.make_comment('Level 1')
        second = self.make_comment('Level 2', parent=root)
        third = self.make_comment('Level 3', parent=second)
        fourth = self.make_comment('Level 4', parent=third)
        fifth = self.make_comment('Level 5', parent=fourth)

        self.assertEqual(root.depth, 1)
        self.assertEqual(second.depth, 2)
        self.assertEqual(third.depth, 3)
        self.assertEqual(fourth.depth, 4)
        self.assertEqual(fifth.depth, 5)

        with self.assertRaises(ValidationError):
            self.make_comment('Level 6', parent=fifth)

    def test_depth_stays_finite_even_if_a_cycle_is_introduced_outside_validation(self):
        root = self.make_comment('Root comment')
        child = self.make_comment('Child comment', parent=root)
        Comment.objects.filter(pk=root.pk).update(parent=child)
        root.refresh_from_db()

        self.assertLessEqual(root.depth, Comment.MAX_DEPTH)


class CommentDeletionInteractionTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email='student@unicatt.it',
            password='StudentPass123!',
            full_name='Student Example',
            study_program='medicine',
            year_of_study='1',
            country_of_origin='IT',
            is_verified_student=True,
        )
        self.post = Post.objects.create(
            title_it='Titolo',
            title_en='Title',
            body_it='Corpo',
            body_en='Body',
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.comment = Comment.objects.create(post=self.post, author=self.author, body='Root comment')
        self.reply = Comment.objects.create(post=self.post, author=self.author, parent=self.comment, body='Reply comment')

    def test_post_detail_shows_compact_delete_action_for_allowed_users(self):
        self.client.force_login(self.author)

        response = self.client.get(reverse('posts:detail', kwargs={'slug': self.post.slug}))

        self.assertContains(response, 'thread-action-row')
        self.assertContains(response, 'thread-action-btn thread-action-btn-danger')
        self.assertContains(response, 'js-thread-delete-form')

    def test_post_detail_links_comment_author_name_to_public_profile(self):
        response = self.client.get(reverse('posts:detail', kwargs={'slug': self.post.slug}))

        self.assertContains(response, reverse('accounts:public_profile', args=[self.author.pk]))

    def test_deleted_comment_disappears_from_post_detail(self):
        self.comment.soft_delete(self.author)
        self.client.force_login(self.author)

        response = self.client.get(reverse('posts:detail', kwargs={'slug': self.post.slug}))

        self.assertContains(response, 'No comments yet.')
        self.assertNotContains(response, '[deleted]')
        self.assertNotContains(response, 'Reply comment')
        self.assertNotContains(response, reverse('comments:delete', kwargs={'pk': self.comment.pk}))

    def test_ajax_delete_marks_comment_as_removed_without_redirect(self):
        self.client.force_login(self.author)

        response = self.client.post(
            reverse('comments:delete', kwargs={'pk': self.comment.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['removed'])
        self.assertNotIn('html', data)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.soft_deleted)
