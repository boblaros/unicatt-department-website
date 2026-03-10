# UCSC International Integration Department Website

Production-oriented Dockerized Django web app for a bilingual (EN/IT) department portal at Università Cattolica del Sacro Cuore.

## 1) Initial Repository Audit (Before Changes)

The repository originally contained an AI Studio/Vite React scaffold and no Django backend:

- `src/`, `index.html`, `vite.config.ts`, `tsconfig.json`, `package.json`
- Old `README.md` with Node/Gemini instructions
- No PostgreSQL, no Dockerized Django stack, no Nginx/Gunicorn setup
- No domain model for users/posts/comments/gallery/auth workflows

## 2) Implementation Plan Applied

1. Remove unrelated Vite/React scaffold files.
2. Add Dockerized Python 3.12 stack with:
   - Django app container (Gunicorn)
   - PostgreSQL container
   - Nginx reverse proxy container
3. Create Django project and apps:
   - `core` for public pages (`home`, `about`, `privacy`)
   - `accounts` for custom auth user, domain-restricted registration, secure password-setup/reset links, rate limiting, ban/roles/profile data
   - `posts` for bilingual news posts and gallery images (EXIF stripping + thumbnails + size/type validation)
   - `comments` for threaded nested post comments (depth cap 5), soft delete, moderator/admin delete
4. Implement server-rendered templates + Bootstrap CDN + minimal CSS.
5. Configure language switching (EN/IT) and bilingual post rendering.
6. Provide migrations, env template, Nginx config, and deployment/ops documentation.

## 3) Final Repository Tree

```text
.
├── .env.example
├── .dockerignore
├── .gitignore
├── Dockerfile
├── README.md
├── docker-compose.yml
├── entrypoint.sh
├── nginx/
│   └── default.conf
├── requirements.txt
└── app/
    ├── manage.py
    ├── accounts/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── choices.py
    │   ├── forms.py
    │   ├── migrations/
    │   │   ├── 0001_initial.py
    │   │   └── __init__.py
    │   ├── models.py
    │   ├── urls.py
    │   ├── utils.py
    │   └── views.py
    ├── comments/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── migrations/
    │   │   ├── 0001_initial.py
    │   │   └── __init__.py
    │   ├── models.py
    │   ├── urls.py
    │   └── views.py
    ├── config/
    │   ├── __init__.py
    │   ├── asgi.py
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    ├── core/
    │   ├── __init__.py
    │   ├── apps.py
    │   ├── context_processors.py
    │   ├── migrations/
    │   │   └── __init__.py
    │   ├── urls.py
    │   └── views.py
    ├── posts/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── forms.py
    │   ├── migrations/
    │   │   ├── 0001_initial.py
    │   │   └── __init__.py
    │   ├── models.py
    │   ├── urls.py
    │   └── views.py
    ├── static/
    │   └── css/
    │       └── styles.css
    └── templates/
        ├── about.html
        ├── base.html
        ├── home.html
        ├── privacy.html
        ├── account/
        │   ├── forgot_password.html
        │   ├── login.html
        │   └── register.html
        ├── comments/
        │   └── comment_item.html
        └── posts/
            ├── post_detail.html
            └── post_list.html
```

## 4) Key Features Implemented

- Bilingual posts with required fields:
  - `title_it`, `title_en`, `body_it`, `body_en`
- Public pages:
  - Home, News list, Post detail, About, Privacy
- Auth:
  - Email/password login with custom user model (`email` as username)
  - Registration restricted to `@unicatt.it` and `@icatt.it`
  - Registration sends a secure password-setup link by email
  - Forgot-password sends a secure password-reset link
  - Password hashing via Django hashers
- Roles:
  - Student (default)
  - Moderator (`is_moderator`)
  - Admin (`is_superuser`)
- Ban:
  - `is_banned` blocks login and commenting
- Comments:
  - Threaded replies with `parent` FK, max depth 5
  - Only verified students can comment
  - Users can delete own comments (soft delete)
  - Moderators/admin can delete any comment (soft delete)
- Post gallery images:
  - Admin-managed on posts via inline images
  - Validation for jpg/jpeg/png/webp
  - File size capped by `MAX_UPLOAD_SIZE_MB` (default 10MB)
  - EXIF stripping and thumbnail generation via Pillow
- UI:
  - Django templates + Bootstrap CDN + language switch

## 5) Environment Variables

Copy `.env.example` to `.env` and update values.

```env
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost
LANGUAGE_CODE=en
TIME_ZONE=Europe/Rome
POSTGRES_DB=department
POSTGRES_USER=department
POSTGRES_PASSWORD=department
DATABASE_URL=postgres://department:department@db:5432/department
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=True
FROM_EMAIL=no-reply@example.com
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
MAX_UPLOAD_SIZE_MB=10
```

Notes:
- Development default email backend is console output.
- For real SMTP, set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` and SMTP fields.

## 6) Local Setup and Run

### Prerequisites

- Docker + Docker Compose plugin

### Commands

```bash
cp .env.example .env
docker compose up --build -d
docker compose logs -f web
```

Create superuser:

```bash
docker compose exec web python manage.py createsuperuser
```

Open:

- `http://localhost/`
- `http://localhost/admin/`

Stop:

```bash
docker compose down
```

## 7) Hetzner CAX11 (ARM) Production Deployment

This stack is ARM-safe (`python:3.12-slim`, `postgres:16-alpine`, `nginx:alpine`).

### A) Provision server

1. Create Hetzner CAX11 Ubuntu VM.
2. Point domain A record to server IP (or Cloudflare proxy, see section 8).
3. SSH into server and install Docker:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Re-login SSH, then:

```bash
mkdir -p ~/apps/ucsc-department
cd ~/apps/ucsc-department
```

### B) Deploy app

1. Upload/clone repository to `~/apps/ucsc-department`.
2. Create production `.env` (`DEBUG=False`, strong `SECRET_KEY`, real SMTP, production hosts).
3. Start services:

```bash
docker compose up --build -d
```

4. Run superuser creation once:

```bash
docker compose exec web python manage.py createsuperuser
```

5. Verify service:

```bash
curl -I http://127.0.0.1
```

### C) Ongoing updates

```bash
cd ~/apps/ucsc-department
git pull
docker compose up --build -d
docker image prune -f
```

## 8) Cloudflare + Domain Attachment

1. Add your domain to Cloudflare.
2. At registrar, switch nameservers to Cloudflare nameservers.
3. In Cloudflare DNS:
   - Add `A` record `@` -> VPS public IP (`Proxied` enabled)
   - Add `A` record `www` -> VPS public IP (`Proxied` enabled)
4. In `.env`:
   - `ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`
   - `CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com`
5. Restart stack:

```bash
docker compose up --build -d
```

6. In Cloudflare SSL/TLS:
   - Use `Full` or `Full (strict)` depending on your TLS setup.

## 9) Backups (Postgres + Media)

### Manual backup commands

Postgres dump:

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup_$(date +%F).sql
```

Media archive:

```bash
docker compose exec -T web sh -c 'tar -czf - -C /app/media .' > media_backup_$(date +%F).tar.gz
```

Restore DB:

```bash
cat backup_YYYY-MM-DD.sql | docker compose exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

### Cron examples

Edit crontab with `crontab -e`:

```cron
0 2 * * * cd /home/ubuntu/apps/ucsc-department && docker compose exec -T db pg_dump -U department department > /home/ubuntu/backups/db_$(date +\%F).sql
15 2 * * * cd /home/ubuntu/apps/ucsc-department && docker compose exec -T web sh -c 'tar -czf - -C /app/media .' > /home/ubuntu/backups/media_$(date +\%F).tar.gz
```

## 10) Non-Developer Operations Guide

### Publish a news post

1. Login at `/admin/` as admin/moderator with post permissions.
2. Go to `Posts` -> `Add Post`.
3. Fill all required bilingual fields:
   - `title_en`, `title_it`, `body_en`, `body_it`
4. Set status to `Published`.
5. Save.

### Upload gallery photos

1. In the same Post admin page, use `Post images` inline section.
2. Upload jpg/png/webp images (<= configured max size).
3. Save post. Thumbnails are generated automatically and EXIF metadata is stripped.

### Add a moderator

1. Go to `Users` in admin.
2. Open target user.
3. Set:
   - `is_moderator = True`
   - `is_staff = True` (auto-enabled when `is_moderator` is set)
4. Save user.
5. Grant required model permissions/groups in admin if needed.

### Ban a user

1. Open user in admin.
2. Set `is_banned = True`.
3. Save.

Effect:
- Banned users cannot login.
- Banned users cannot comment.

### Comment moderation

- Users may delete only their own comments.
- Moderators/admin may delete any comment.
- Deletion is soft delete (`[deleted]`).

## 11) Key Run Commands

```bash
# First run
cp .env.example .env
docker compose up --build -d

# Create admin user
docker compose exec web python manage.py createsuperuser

# View logs
docker compose logs -f web
docker compose logs -f nginx

docker compose logs -f db

# Stop
docker compose down
```
