from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _
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
        context['latest_posts'] = Post.objects.published().prefetch_related('images')[:3]
        context['quick_register_form'] = RegistrationForm()
        context['wall_posts'] = (
            WallPost.objects.filter(parent__isnull=True, soft_deleted=False)
            .select_related('author')
            .prefetch_related(
                'replies__author',
                'replies__replies__author',
                'replies__replies__replies__author',
                'replies__replies__replies__replies__author',
            )[:30]
        )
        return context


class AboutView(TemplateView):
    template_name = 'about.html'


class PrivacyView(TemplateView):
    template_name = 'privacy.html'


@login_required
@require_POST
def create_wall_post(request):
    if request.user.is_banned:
        return HttpResponseForbidden(_('Banned users cannot post.'))

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    parent_id = request.POST.get('parent_id')
    parent = None
    if parent_id:
        parent = get_object_or_404(WallPost.objects.select_related('author'), pk=parent_id)
        if parent.soft_deleted:
            if is_ajax:
                return JsonResponse({'ok': False, 'error': _('You cannot reply to a deleted wall post.')}, status=400)
            return redirect(f"{reverse('core:home')}#wall")

    form = WallPostForm(request.POST)
    if form.is_valid():
        wall_post = form.save(commit=False)
        wall_post.author = request.user
        wall_post.parent = parent
        try:
            wall_post.save()
        except ValidationError as exc:
            if is_ajax:
                return JsonResponse({'ok': False, 'error': exc.messages[0]}, status=400)
            return redirect(f"{reverse('core:home')}#wall")
        if is_ajax:
            html = render_to_string(
                'core/wall_post_item.html',
                {'wall_post': wall_post, 'depth': wall_post.depth},
                request=request,
            )
            return JsonResponse(
                {
                    'ok': True,
                    'post_id': wall_post.id,
                    'parent_id': wall_post.parent_id,
                    'html': html,
                }
            )
    elif is_ajax:
        error_text = _('Please add a valid message before posting.')
        if form.errors:
            error_text = str(next(iter(form.errors.values()))[0])
        return JsonResponse({'ok': False, 'error': error_text}, status=400)
    return redirect(f"{reverse('core:home')}#wall")


@login_required
@require_POST
def delete_wall_post(request, pk):
    wall_post = get_object_or_404(WallPost, pk=pk)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    if not request.user.can_moderate_community_content:
        if is_ajax:
            return JsonResponse({'ok': False, 'error': _('You cannot delete this wall post.')}, status=403)
        return HttpResponseForbidden(_('You cannot delete this wall post.'))
    if not wall_post.soft_deleted:
        wall_post.soft_delete(request.user)
    if is_ajax:
        return JsonResponse({'ok': True, 'post_id': wall_post.id, 'removed': True})
    return redirect(f"{reverse('core:home')}#wall")


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
