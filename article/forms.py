from django import forms
from .models import Article, File, Image


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'class': 'form-control-file'}))
        super().__init__(*args, **kwargs)

    def to_python(self, data):
        if data is None:
            return []

        # 如果是单个文件，转换为列表
        if not hasattr(data, '__iter__') or isinstance(data, (str, bytes)):
            return [data]

        return list(data)

    def validate(self, value):
        super().validate(value)

        # 验证每个文件
        for file in value:
            if file:
                # 使用父类的验证方法，但不抛出 required 错误
                if file.size > self.max_size:
                    raise forms.ValidationError(self.error_messages['invalid_file'])

                # 检查文件类型
                if hasattr(self, 'allowed_types') and file.content_type not in self.allowed_types:
                    raise forms.ValidationError(f'不支持的文件类型: {file.content_type}')


class ArticleForm(forms.ModelForm):
    # 图片上传将在视图中直接处理，不在表单中定义

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
