from django import forms
from django.utils.translation import gettext_lazy as _

from comments.models import Comment


class CommentCreateForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 3, 'placeholder': _('Write your comment...')}),
        }
