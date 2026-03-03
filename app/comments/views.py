from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from posts.forms import CommentCreateForm
from posts.models import Post

from .models import Comment


@login_required
@require_POST
def create_comment_view(request, slug):
    if request.user.is_banned:
        return HttpResponseForbidden(_('Banned users cannot comment.'))
    if not request.user.is_verified_student:
        return HttpResponseForbidden(_('Only verified students can comment.'))

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    post = get_object_or_404(Post.objects.published(), slug=slug)
    form = CommentCreateForm(request.POST)
    parent_id = request.POST.get('parent_id')
    parent = None

    if parent_id:
        parent = get_object_or_404(Comment, pk=parent_id, post=post)
        if parent.depth >= 5:
            if is_ajax:
                return JsonResponse({'ok': False, 'error': _('Maximum reply depth reached.')}, status=400)
            return redirect(f"{reverse('posts:detail', kwargs={'slug': slug})}#comments")

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.parent = parent
        try:
            comment.full_clean()
        except ValidationError as exc:
            if is_ajax:
                return JsonResponse({'ok': False, 'error': exc.messages[0]}, status=400)
            return redirect(f"{reverse('posts:detail', kwargs={'slug': slug})}#comments")
        comment.save()
        if is_ajax:
            html = render_to_string(
                'comments/comment_item.html',
                {'comment': comment, 'depth': comment.depth},
                request=request,
            )
            return JsonResponse({'ok': True, 'comment_id': comment.id, 'parent_id': comment.parent_id, 'html': html})
    elif is_ajax:
        error_text = _('Failed to publish comment.')
        if form.errors:
            error_text = str(next(iter(form.errors.values()))[0])
        return JsonResponse({'ok': False, 'error': error_text}, status=400)

    return redirect(f"{reverse('posts:detail', kwargs={'slug': slug})}#comments")


@login_required
@require_POST
def delete_comment_view(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    can_delete = request.user == comment.author or request.user.is_superuser or request.user.is_moderator
    if not can_delete:
        return HttpResponseForbidden(_('You cannot delete this comment.'))
    if not comment.soft_deleted:
        comment.soft_delete(request.user)
    return redirect(f"{reverse('posts:detail', kwargs={'slug': comment.post.slug})}#comments")
