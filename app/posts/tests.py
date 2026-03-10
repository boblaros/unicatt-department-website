import io
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.models import User
from comments.models import Comment

from .models import Post, PostImage


class PostImageLifecycleTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_dir = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_dir)
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls._media_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
        self.post = Post.objects.create(
            title_it='Titolo',
            title_en='Title',
            body_it='Corpo',
            body_en='Body',
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
        )

    def make_upload(self, name='photo.jpg', fmt='JPEG', color='navy', content_type='image/jpeg'):
        buffer = io.BytesIO()
        image = Image.new('RGB', (1200, 900), color=color)
        image.save(buffer, format=fmt)
        return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)

    def media_files(self):
        return sorted(path for path in Path(settings.MEDIA_ROOT).rglob('*') if path.is_file())

    def test_upload_creates_single_processed_image_and_thumbnail(self):
        image = PostImage(post=self.post, image=self.make_upload())

        image.save()
        image.refresh_from_db()

        self.assertTrue(Path(settings.MEDIA_ROOT, image.image.name).exists())
        self.assertTrue(Path(settings.MEDIA_ROOT, image.thumbnail.name).exists())
        self.assertEqual(len(self.media_files()), 2)

    def test_caption_update_does_not_duplicate_files(self):
        image = PostImage(post=self.post, image=self.make_upload())
        image.save()
        image.refresh_from_db()

        original_names = (image.image.name, image.thumbnail.name)
        original_files = self.media_files()

        image.caption = 'Updated caption'
        with self.captureOnCommitCallbacks(execute=True):
            image.save(update_fields=['caption'])

        image.refresh_from_db()
        self.assertEqual((image.image.name, image.thumbnail.name), original_names)
        self.assertEqual(self.media_files(), original_files)

    def test_invalid_image_processing_rolls_back_without_files(self):
        broken_upload = SimpleUploadedFile('broken.jpg', b'not-an-image', content_type='image/jpeg')

        with self.assertRaises(ValidationError):
            PostImage(post=self.post, image=broken_upload).save()

        self.assertEqual(PostImage.objects.count(), 0)
        self.assertEqual(self.media_files(), [])

    def test_replacing_image_cleans_previous_files(self):
        image = PostImage(post=self.post, image=self.make_upload(color='navy'))
        image.save()
        image.refresh_from_db()

        old_image_path = Path(settings.MEDIA_ROOT, image.image.name)
        old_thumbnail_path = Path(settings.MEDIA_ROOT, image.thumbnail.name)

        image.image = self.make_upload(name='replacement.png', fmt='PNG', color='orange', content_type='image/png')
        with self.captureOnCommitCallbacks(execute=True):
            image.save()

        image.refresh_from_db()
        self.assertFalse(old_image_path.exists())
        self.assertFalse(old_thumbnail_path.exists())
        self.assertTrue(Path(settings.MEDIA_ROOT, image.image.name).exists())
        self.assertTrue(Path(settings.MEDIA_ROOT, image.thumbnail.name).exists())
        self.assertEqual(len(self.media_files()), 2)


class NewsCommentThreadTemplateTests(TestCase):
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
        root = Comment.objects.create(post=self.post, author=self.user, body='Root comment')
        Comment.objects.create(post=self.post, author=self.user, parent=root, body='Reply comment')

    def test_post_detail_renders_original_comment_markup(self):
        response = self.client.get(reverse('posts:detail', kwargs={'slug': self.post.slug}))

        self.assertContains(response, 'class="comment-card ms-1 mt-2"')
        self.assertContains(response, 'class="comment-replies"')
        self.assertContains(response, 'id="comments-list"')
