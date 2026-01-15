import uuid

from article.models import Article
from django.contrib import admin
from django.db import models, transaction
from user.models import CustomUser


class Comment_index_id_ProductSequenceLock(models.Model):
    pass

    class Meta:
        verbose_name = "Comment.index_id序列锁"
        verbose_name_plural = verbose_name


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    index_id = models.IntegerField()
    article_index_id = models.IntegerField()
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    top = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)

    def get_article(self):
        return Article.objects.filter(
            index_id=self.article_index_id,
            deleted=False
        ).order_by('-updated_at').first()

    def save(self, *args, **kwargs):
        if self.index_id is None:
            with transaction.atomic():
                try:
                    lock = Comment_index_id_ProductSequenceLock.objects.select_for_update().get(pk=1)
                except Comment_index_id_ProductSequenceLock.DoesNotExist:
                    lock = Comment_index_id_ProductSequenceLock.objects.create(pk=1)

                max_result = Comment.objects.aggregate(max_val=models.Max('index_id'))
                current_max = max_result['max_val']
                self.index_id = (current_max or 0) + 1
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    class Meta:
        verbose_name = '评论'
        verbose_name_plural = verbose_name
        ordering = ['-top', '-create_time']


admin.site.register(Comment)
admin.site.register(Comment_index_id_ProductSequenceLock)
