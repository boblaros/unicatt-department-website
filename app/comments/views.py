from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from posts.forms import CommentCreateForm
from posts.models import Post

from .models import Comment


@login_required
@require_POST
def create_comment_view(request, slug):
    if request.user.is_banned:
        return HttpResponseForbidden('Banned users cannot comment.')
    if not request.user.is_verified_student:
        return HttpResponseForbidden('Only verified students can comment.')

    post = get_object_or_404(Post.objects.published(), slug=slug)
    form = CommentCreateForm(request.POST)
    parent_id = request.POST.get('parent_id')
    parent = None

    if parent_id:
        parent = get_object_or_404(Comment, pk=parent_id, post=post)
        if parent.depth >= 5:
            messages.error(request, 'Maximum reply depth reached.')
            return redirect('posts:detail', slug=slug)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.parent = parent
        comment.save()
        messages.success(request, 'Comment published.')
    else:
        messages.error(request, 'Failed to publish comment.')

    return redirect('posts:detail', slug=slug)


@login_required
@require_POST
def delete_comment_view(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    can_delete = request.user == comment.author or request.user.is_superuser or request.user.is_moderator
    if not can_delete:
        return HttpResponseForbidden('You cannot delete this comment.')
    if not comment.soft_deleted:
        comment.soft_delete(request.user)
    return redirect('posts:detail', slug=comment.post.slug)
