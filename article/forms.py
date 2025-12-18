from django import forms
from .models import Article, File, Image


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入文章标题'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 15, 'placeholder': '请输入文章内容'}),
        }


class FileForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入文件标题'}),
            'content': forms.FileInput(attrs={'class': 'form-control-file'}),
        }


class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入图片标题'}),
            'content': forms.FileInput(attrs={'class': 'form-control-file'}),
        }