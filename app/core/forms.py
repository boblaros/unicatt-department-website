from django import forms

from .models import WallPost


class WallPostForm(forms.ModelForm):
    class Meta:
        model = WallPost
        fields = ['body']
        widgets = {
            'body': forms.Textarea(
                attrs={
                    'rows': 4,
                    'placeholder': 'Share your message with the community...',
                }
            ),
        }
