import io
import os
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.template.defaultfilters import slugify
from PIL import Image


ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def post_image_upload_to(instance, filename):
    ext = filename.split('.')[-1].lower()
    return f'posts/{instance.post_id}/{uuid4().hex}.{ext}'


def thumb_upload_to(instance, filename):
    ext = filename.split('.')[-1].lower()
    return f'posts/{instance.post_id}/thumbs/{uuid4().hex}.{ext}'


class PublishedPostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Post.Status.PUBLISHED)


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    title_it = models.CharField(max_length=255)
    title_en = models.CharField(max_length=255)
    body_it = models.TextField()
    body_en = models.TextField()
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PublishedPostQuerySet.as_manager()

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title_en

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title_en)[:220] or uuid4().hex[:8]
            slug = base_slug
            i = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{i}'
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def title_for_language(self, lang_code):
        return self.title_it if lang_code == 'it' else self.title_en

    def body_for_language(self, lang_code):
        return self.body_it if lang_code == 'it' else self.body_en


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=post_image_upload_to)
    thumbnail = models.ImageField(upload_to=thumb_upload_to, blank=True)
    caption = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Image for {self.post_id}'

    def clean(self):
        uploaded = self.image
        if not uploaded:
            return
        content_type = getattr(uploaded.file, 'content_type', None)
        ext = uploaded.name.split('.')[-1].lower()
        if ext not in {'jpg', 'jpeg', 'png', 'webp'}:
            raise ValidationError('Only JPG, PNG, and WEBP files are allowed.')
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError('Only JPG, PNG, and WEBP files are allowed.')
        if uploaded.size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise ValidationError(f'Image exceeds max size of {settings.MAX_UPLOAD_SIZE_MB}MB.')

    def save(self, *args, **kwargs):
        self.full_clean(exclude=['thumbnail'])
        super().save(*args, **kwargs)
        if not self.image:
            return
        self._strip_exif_and_generate_thumbnail()

    def _strip_exif_and_generate_thumbnail(self):
        self.image.open('rb')
        with Image.open(self.image) as img:
            mode = 'RGB' if img.mode not in ('RGB', 'L') else img.mode
            clean_img = img.convert(mode)

            original_buffer = io.BytesIO()
            original_format = img.format or 'JPEG'
            save_format = 'JPEG' if original_format.upper() == 'JPG' else original_format.upper()
            if save_format not in {'JPEG', 'PNG', 'WEBP'}:
                save_format = 'JPEG'
            ext = save_format.lower()
            clean_img.save(original_buffer, format=save_format, quality=90)
            original_name = os.path.basename(self.image.name)
            self.image.save(original_name, ContentFile(original_buffer.getvalue()), save=False)

            thumb = clean_img.copy()
            thumb.thumbnail((320, 320))
            thumb_buffer = io.BytesIO()
            thumb.save(thumb_buffer, format=save_format, quality=85)
            thumb_name = f'thumb_{uuid4().hex}.{ext}'
            self.thumbnail.save(thumb_name, ContentFile(thumb_buffer.getvalue()), save=False)

        super().save(update_fields=['image', 'thumbnail'])
