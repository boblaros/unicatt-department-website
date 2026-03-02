from django.views.generic import TemplateView

from posts.models import Post


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['latest_posts'] = Post.objects.published()[:3]
        return context


class AboutView(TemplateView):
    template_name = 'about.html'


class PrivacyView(TemplateView):
    template_name = 'privacy.html'
