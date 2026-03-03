from django import forms
from django.utils.translation import gettext_lazy as _

from .models import WallPost


class WallPostForm(forms.ModelForm):
    class Meta:
        model = WallPost
        fields = ['body']
        widgets = {
            'body': forms.Textarea(
                attrs={
                    'rows': 4,
                    'placeholder': _('Share your message with the community...'),
                }
            ),
        }
