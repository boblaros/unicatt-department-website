from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from accounts.forms import RegistrationForm
from core.forms import WallPostForm
from core.models import WallPost
from posts.models import Post


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['latest_posts'] = Post.objects.published()[:3]
        context['quick_register_form'] = RegistrationForm()
        context['wall_posts'] = WallPost.objects.select_related('author')[:30]
        return context


class AboutView(TemplateView):
    template_name = 'about.html'


class PrivacyView(TemplateView):
    template_name = 'privacy.html'


@login_required
@require_POST
def create_wall_post(request):
    if request.user.is_banned:
        return HttpResponseForbidden('Banned users cannot post.')

    form = WallPostForm(request.POST)
    if form.is_valid():
        wall_post = form.save(commit=False)
        wall_post.author = request.user
        wall_post.save()
        messages.success(request, 'Message posted to the community wall.')
    else:
        messages.error(request, 'Please add a valid message before posting.')
    return redirect('core:home')


def switch_language(request, lang_code):
    allowed_languages = {code for code, _ in settings.LANGUAGES}
    if lang_code not in allowed_languages:
        lang_code = settings.LANGUAGE_CODE

    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or '/'
    parsed = urlparse(next_url)
    if parsed.netloc:
        next_url = '/'
        parsed = urlparse(next_url)

    path = parsed.path or '/'
    for code, _ in settings.LANGUAGES:
        exact = f'/{code}'
        prefix = f'/{code}/'
        if path == exact:
            path = '/'
            break
        if path.startswith(prefix):
            path = f"/{path[len(prefix):]}"
            break

    if not path.startswith('/'):
        path = f'/{path}'

    if lang_code == settings.LANGUAGE_CODE:
        target_path = path
    else:
        target_path = f'/{lang_code}{path}' if path != '/' else f'/{lang_code}/'

    clean_query = urlencode(parse_qsl(parsed.query, keep_blank_values=True), doseq=True)
    translated_url = urlunparse(('', '', target_path, '', clean_query, parsed.fragment))
    response = redirect(translated_url)

    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        lang_code,
        max_age=settings.LANGUAGE_COOKIE_AGE,
        path=settings.LANGUAGE_COOKIE_PATH,
        domain=settings.LANGUAGE_COOKIE_DOMAIN,
        secure=settings.LANGUAGE_COOKIE_SECURE,
        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
    )
    return response
