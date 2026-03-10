import io
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.db import transaction
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _
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
        DRAFT = 'draft', _('Draft')
        PUBLISHED = 'published', _('Published')

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
        return _('Image for %(post_id)s') % {'post_id': self.post_id}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_image_name = self.image.name if self.image else ''
        self._original_thumbnail_name = self.thumbnail.name if self.thumbnail else ''

    def clean(self):
        uploaded = self.image
        if not uploaded:
            return
        content_type = getattr(uploaded.file, 'content_type', None)
        ext = uploaded.name.split('.')[-1].lower()
        if ext not in {'jpg', 'jpeg', 'png', 'webp'}:
            raise ValidationError(_('Only JPG, PNG, and WEBP files are allowed.'))
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError(_('Only JPG, PNG, and WEBP files are allowed.'))
        if uploaded.size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise ValidationError(_('Image exceeds max size of %(size)sMB.') % {'size': settings.MAX_UPLOAD_SIZE_MB})

    def _image_has_changed(self):
        if not self.image:
            return False
        if self.pk is None:
            return True
        if not getattr(self.image, '_committed', True):
            return True
        return self.image.name != self._original_image_name

    def _process_image_file(self):
        self.image.open('rb')
        try:
            with Image.open(self.image) as img:
                clean_img, save_format, ext = self._normalized_image(img)
                original_file = self._make_content_file(clean_img, save_format, ext, quality=90)

                thumb = clean_img.copy()
                thumb.thumbnail((320, 320))
                thumb_file = self._make_content_file(thumb, save_format, ext, quality=85, prefix='thumb_')
        except OSError as exc:
            raise ValidationError(_('Uploaded file is not a valid image.')) from exc
        finally:
            self.image.close()

        return original_file, thumb_file

    def _normalized_image(self, image):
        original_format = (image.format or 'JPEG').upper()
        if original_format == 'JPG':
            original_format = 'JPEG'
        if original_format not in {'JPEG', 'PNG', 'WEBP'}:
            original_format = 'JPEG'

        if original_format == 'JPEG':
            return image.convert('RGB'), original_format, 'jpg'
        if image.mode in {'RGB', 'RGBA', 'L', 'LA'}:
            clean_img = image.copy()
        else:
            clean_img = image.convert('RGBA' if 'A' in image.getbands() else 'RGB')
        return clean_img, original_format, original_format.lower()

    def _make_content_file(self, image, save_format, ext, quality, prefix=''):
        buffer = io.BytesIO()
        save_kwargs = {}
        if save_format == 'JPEG':
            save_kwargs.update({'quality': quality, 'optimize': True})
        elif save_format == 'WEBP':
            save_kwargs.update({'quality': quality, 'method': 6})
        else:
            save_kwargs.update({'optimize': True})
        image.save(buffer, format=save_format, **save_kwargs)
        return ContentFile(buffer.getvalue(), name=f'{prefix}{uuid4().hex}.{ext}')

    def _delete_storage_file(self, name):
        if not name:
            return
        storage = self.image.storage
        if storage.exists(name):
            storage.delete(name)

    def save(self, *args, **kwargs):
        self.full_clean(exclude=['thumbnail'])
        image_changed = self._image_has_changed()
        old_files = [name for name in [self._original_image_name, self._original_thumbnail_name] if name]

        if image_changed:
            processed_image, processed_thumbnail = self._process_image_file()
            self.image = processed_image
            self.thumbnail = processed_thumbnail
            update_fields = kwargs.get('update_fields')
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'image', 'thumbnail'}

        try:
            with transaction.atomic():
                result = super().save(*args, **kwargs)
                if image_changed:
                    transaction.on_commit(lambda: [self._delete_storage_file(name) for name in old_files])
        except Exception:
            if image_changed:
                self._delete_storage_file(self.image.name)
                self._delete_storage_file(self.thumbnail.name)
            raise

        self._original_image_name = self.image.name if self.image else ''
        self._original_thumbnail_name = self.thumbnail.name if self.thumbnail else ''
        return result

    def delete(self, *args, **kwargs):
        image_name = self.image.name if self.image else ''
        thumbnail_name = self.thumbnail.name if self.thumbnail else ''
        with transaction.atomic():
            result = super().delete(*args, **kwargs)
            transaction.on_commit(
                lambda: [self._delete_storage_file(name) for name in [image_name, thumbnail_name] if name]
            )
        return result
