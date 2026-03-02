from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView

from comments.models import Comment

from .forms import CommentCreateForm
from .models import Post


class PostListView(ListView):
    model = Post
    template_name = 'posts/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        return Post.objects.published()


def _comment_tree(post):
    comments = Comment.objects.filter(post=post, parent__isnull=True).select_related('author')
    return comments


def post_detail_view(request, slug):
    post = get_object_or_404(Post.objects.published(), slug=slug)
    comment_form = CommentCreateForm()
    context = {
        'post': post,
        'comment_form': comment_form,
        'comments': _comment_tree(post),
    }
    return render(request, 'posts/post_detail.html', context)
