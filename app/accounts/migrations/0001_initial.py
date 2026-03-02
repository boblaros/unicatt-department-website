from django.db import migrations, models
import django.utils.timezone
import accounts.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('full_name', models.CharField(max_length=255)),
                ('study_program', models.CharField(choices=[('medicine', 'Medicine and Surgery'), ('economics', 'Economics and Management'), ('law', 'Law'), ('psychology', 'Psychology'), ('education', 'Education Sciences'), ('nursing', 'Nursing')], max_length=32)),
                ('year_of_study', models.CharField(choices=[('1', '1st year'), ('2', '2nd year'), ('3', '3rd year'), ('4', '4th year'), ('5', '5th year'), ('6', '6th year'), ('postgrad', 'Postgraduate')], max_length=16)),
                ('country_of_origin', models.CharField(choices=[('IT', 'Italy'), ('AL', 'Albania'), ('BR', 'Brazil'), ('CN', 'China'), ('FR', 'France'), ('DE', 'Germany'), ('IN', 'India'), ('NG', 'Nigeria'), ('ES', 'Spain'), ('TR', 'Turkey'), ('UA', 'Ukraine'), ('US', 'United States'), ('OTHER', 'Other')], max_length=16)),
                ('is_verified_student', models.BooleanField(default=False)),
                ('is_moderator', models.BooleanField(default=False)),
                ('is_banned', models.BooleanField(default=False)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            managers=[('objects', accounts.models.UserManager())],
        ),
        migrations.CreateModel(
            name='RateLimitRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=50)),
                ('key', models.CharField(max_length=255)),
                ('count', models.PositiveIntegerField(default=0)),
                ('window_started_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={'unique_together': {('action', 'key')}},
        ),
    ]
