from django.db import models
from user.models import CustomUser


# Create your models here.
class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class File(models.Model):
    title = models.CharField(max_length=200)
    content = models.FileField('./uploads/files/')
    article_id = models.ForeignKey(Article, on_delete=models.CASCADE)
    author_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Image(models.Model):
    title = models.CharField(max_length=200)
    content = models.ImageField('./uploads/images/')
    article_id = models.ForeignKey(Article, on_delete=models.CASCADE)
    author_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
