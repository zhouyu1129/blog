import uuid

from django.contrib import admin
from django.db import models, transaction
from user.models import CustomUser


# Create your models here.
class Article_index_id_ProductSequenceLock(models.Model):
    """
    一个用于生成 Article.index_id 的锁模型。
    这个表应该永远只有一行数据。
    """
    pass

    class Meta:
        verbose_name = "Article.index_id序列锁"
        verbose_name_plural = verbose_name


class Article(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    index_id = models.IntegerField()
    title = models.CharField(max_length=200)
    content = models.TextField()
    author_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """
        重写 save 方法，使用悲观锁来安全地生成 index_id。
        """
        # 只在新建对象且 index_id 未设置时执行
        print(self.index_id)
        if self.index_id is None:
            # 使用 atomic 事务包裹整个操作
            with transaction.atomic():
                # 1. 获取锁对象并加锁
                # select_for_update() 会锁定这一行，直到事务结束
                # 其他试图获取这个锁的事务会在这里等待
                try:
                    lock = Article_index_id_ProductSequenceLock.objects.select_for_update().get(pk=1)
                except Article_index_id_ProductSequenceLock.DoesNotExist:
                    # 如果锁对象不存在，创建它（通常只需要在第一次运行时发生）
                    lock = Article_index_id_ProductSequenceLock.objects.create(pk=1)

                # 2. 在锁的保护下，安全地查询最大值并计算新值
                # 因为有锁，所以这个查询不会被其他事务干扰
                max_result = Article.objects.aggregate(max_val=models.Max('index_id'))
                current_max = max_result['max_val']

                self.index_id = (current_max or 0) + 1  # 如果为None, -1+1=0

                # 3. 调用父类的 save() 方法保存当前对象
                # 事务提交后，锁会自动释放
                super().save(*args, **kwargs)
        else:
            # 如果是更新操作或 index_id 已被设置，则正常保存
            super().save(*args, **kwargs)

    files = models.ManyToManyField(
        'File',
        through='FileQuote',
        through_fields=('article', 'file'),  # 指定 FileQuote 中用于连接的字段
        related_name='articles'  # 这样就可以用 File.articles.all() 来反向查询
    )
    images = models.ManyToManyField(
        'Image',
        through='ImageQuote',
        through_fields=('article', 'image'),  # 指定 ImageQuote 中用于连接的字段
        related_name='articles'  # 这样就可以用 Image.articles.all() 来反向查询
    )


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    content = models.FileField(upload_to='files/')
    author_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class FileQuote(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    file = models.ForeignKey(File, on_delete=models.CASCADE)
    pk = models.CompositePrimaryKey('article', 'file')


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    content = models.ImageField(upload_to='images/')
    author_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class ImageQuote(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    pk = models.CompositePrimaryKey('article', 'image')


admin.site.register(Article)
admin.site.register(File)
admin.site.register(Image)
