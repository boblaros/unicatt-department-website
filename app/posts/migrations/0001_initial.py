from django.db import migrations, models
import posts.models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title_it', models.CharField(max_length=255)),
                ('title_en', models.CharField(max_length=255)),
                ('body_it', models.TextField()),
                ('body_en', models.TextField()),
                ('slug', models.SlugField(blank=True, max_length=255, unique=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published')], default='draft', max_length=16)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-published_at', '-created_at']},
        ),
        migrations.CreateModel(
            name='PostImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to=posts.models.post_image_upload_to)),
                ('thumbnail', models.ImageField(blank=True, upload_to=posts.models.thumb_upload_to)),
                ('caption', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='images', to='posts.post')),
            ],
            options={'ordering': ['created_at']},
        ),
    ]
