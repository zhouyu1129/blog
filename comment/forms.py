from django import forms
from .models import Comment


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': '请输入评论内容（支持Markdown格式）'}),
        }
        labels = {
            'content': '评论内容',
        }
