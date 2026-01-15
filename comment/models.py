from django.db import models
import uuid
from django.contrib import admin
from user.models import CustomUser
from article.models import Article

# Create your models here.
class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    top = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)

    class Meta:
        verbose_name = '评论'
        verbose_name_plural = verbose_name
