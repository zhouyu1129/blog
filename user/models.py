from django.contrib import admin

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
import re
import uuid


def validate_student_number(value):
    """验证学号是否为10位数字"""
    if not re.match(r'^\d{10}', value):
        raise ValidationError('学号必须是10位数字')


def validate_username(value):
    """验证用户名是否为ASCII字符且不包含空格"""
    if not re.match(r'^[\x00-\x7F]+', value):
        raise ValidationError('用户名只能包含ASCII字符')
    if ' ' in value:
        raise ValidationError('用户名不能包含空格')


def validate_mobile(value):
    """验证手机号是否合法"""
    if not re.match(r'^1[3-9]\d{9}', value):
        raise ValidationError('请输入有效的手机号码')


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[validate_username],
        verbose_name='用户名'
    )

    # 必填字段
    email = models.EmailField(verbose_name='邮箱', unique=True)
    student_number = models.CharField(
        max_length=10,
        validators=[validate_student_number],
        unique=True,
        verbose_name='学号'
    )

    # 可选字段
    email_verified = models.BooleanField(default=False, verbose_name='邮箱已验证')
    nickname = models.CharField(max_length=20, blank=True, verbose_name='昵称')
    real_name = models.CharField(max_length=50, blank=True, verbose_name='姓名')
    mobile = models.CharField(
        max_length=11,
        blank=True,
        validators=[validate_mobile],
        verbose_name='手机号'
    )
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', '男'),
            ('female', '女'),
            ('other', '其他'),
        ],
        blank=True,
        verbose_name='性别'
    )
    age = models.PositiveIntegerField(null=True, blank=True, verbose_name='年龄')

    # 使用email作为登录字段
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'student_number']

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        constraints = [
            models.UniqueConstraint(
                fields=['nickname'], 
                condition=models.Q(nickname__gt=''), 
                name='unique_non_empty_nickname'
            )
        ]

    def __str__(self):
        return self.username


class EmailBackend:
    """
    自定义认证后端，允许使用邮箱登录
    """

    @staticmethod
    def authenticate(request, email=None, password=None, **kwargs): # noqa
        try:
            user = CustomUser.objects.get(email=email)
            if user.check_password(password) and user.email_verified:
                return user
        except CustomUser.DoesNotExist:
            return None

    @staticmethod
    def get_user(user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None


admin.site.register(CustomUser)
