from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0002_wallpost_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name='wallpost',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='wallpost',
            name='soft_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='wallpost',
            name='deleted_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='deleted_wall_posts',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
