import hashlib
import random
import string
import threading

import markdown

from article.models import Article
from comment.models import Comment
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .models import CustomUser


def send_verification_email(user):
    """
    发送邮箱验证邮件的函数
    """
    subject = '校园博客 - 邮箱验证'

    # 生成邮箱哈希值
    email_hash = hashlib.md5((user.email + str(user.id)).encode()).hexdigest()

    verification_url = f"{settings.SITE_URL}/user/email_verify/{user.id}/{email_hash}"
    message = f"""
    尊敬的 {user.username}，

    感谢您注册校园博客！请点击以下链接验证您的邮箱：
    
    {verification_url}
    
    如果您没有注册校园博客，请忽略此邮件。
    
    校园博客团队
    """

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"发送验证邮件失败: {e}")


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == "GET":
        return render(request, 'login.html')
    else:
        login_input = request.POST.get('email')  # 可以是邮箱或用户名
        password = request.POST.get('password')
        
        if not login_input or not password:
            messages.error(request, '请输入邮箱/用户名和密码')
            return render(request, 'login.html')

        # 判断输入的是邮箱还是用户名
        is_email = '@' in login_input
        
        try:
            if is_email:
                # 使用邮箱查找用户
                user_obj = CustomUser.objects.get(email=login_input)
            else:
                # 使用用户名查找用户
                user_obj = CustomUser.objects.get(username=login_input)
                
            if not user_obj.check_password(password):
                messages.error(request, '邮箱/用户名或密码错误，请重试')
                return render(request, 'login.html')
            elif not user_obj.email_verified:
                # 重新发送验证邮件
                email_thread = threading.Thread(target=send_verification_email, args=(user_obj,))
                email_thread.daemon = True
                email_thread.start()
                messages.error(request, '请先验证邮箱后再登录。验证邮件已重新发送，请查收。')
                return render(request, 'login.html')
        except CustomUser.DoesNotExist:
            messages.error(request, '邮箱/用户名或密码错误，请重试')
            return render(request, 'login.html')

        # 使用邮箱进行认证（无论用户输入的是邮箱还是用户名）
        user = authenticate(request, email=user_obj.email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, '登录成功！')
            return redirect(reverse('index'))
        else:
            messages.error(request, '登录失败，请重试')
            return render(request, 'login.html')


@require_http_methods(["GET"])
def logout_view(request):
    logout(request)
    messages.info(request, '您已成功登出')
    return redirect(reverse('index'))


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.method == "GET":
        return render(request, 'register.html')
    else:
        username = request.POST.get('username')
        email = request.POST.get('email')
        student_number = request.POST.get('student_number')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # 验证密码是否匹配
        if password != confirm_password:
            messages.error(request, '两次输入的密码不一致')
            return render(request, 'register.html')

        # 检查用户名是否已存在
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, '用户名已存在')
            return render(request, 'register.html')

        # 检查邮箱是否已存在
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, '邮箱已被注册')
            return render(request, 'register.html')

        # 检查学号是否已存在
        if CustomUser.objects.filter(student_number=student_number).exists():
            messages.error(request, '学号已被注册')
            return render(request, 'register.html')

        try:
            # 创建新用户
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                student_number=student_number,
                password=password
            )

            # 启动子线程发送验证邮件
            email_thread = threading.Thread(target=send_verification_email, args=(user,))
            email_thread.daemon = True
            email_thread.start()

            messages.success(request, '注册成功！请查看您的邮箱并点击验证链接完成注册。')
            return redirect(reverse('login'))
        except Exception as e:
            messages.error(request, f'注册失败：{str(e)}')
            return render(request, 'register.html')


@require_http_methods(["GET"])
def email_verify(request, user_uuid, user_email_hash):
    try:
        user_obj = CustomUser.objects.get(id=user_uuid)

        # 验证邮箱哈希值
        expected_hash = hashlib.md5((user_obj.email + str(user_obj.id)).encode()).hexdigest()
        if user_email_hash != expected_hash:
            messages.error(request, '无效的验证链接')
            return redirect(reverse('index'))

        if user_obj.email_verified:
            messages.error(request, '重复的邮箱验证')
            return redirect(reverse('index'))

        user_obj.email_verified = True
        user_obj.save()
        return render(request, 'email_verified.html', {'user': user_obj, 'target_url': reverse('user:login')})
    except CustomUser.DoesNotExist:
        messages.error(request, '不存在的用户')
        return redirect(reverse('index'))


@login_required
def profile_view(request):
    """
    用户中心主页面，显示用户信息
    """
    return render(request, 'profile.html', {'user': request.user})


@login_required
def edit_profile_view(request):
    """
    编辑个人资料页面（低安全等级字段）
    """
    if request.method == 'GET':
        return render(request, 'edit_profile.html', {'user': request.user})
    else:
        nickname = request.POST.get('nickname', '').strip()
        real_name = request.POST.get('real_name', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        gender = request.POST.get('gender', '')
        age = request.POST.get('age', '')

        # 更新用户信息
        user = request.user
        user.nickname = nickname
        user.real_name = real_name
        user.mobile = mobile
        user.gender = gender

        # 处理年龄字段
        if age:
            try:
                user.age = int(age)
            except ValueError:
                messages.error(request, '年龄必须是数字')
                return render(request, 'edit_profile.html', {'user': user})
        else:
            user.age = None

        try:
            user.save()
            messages.success(request, '个人资料更新成功')
            return redirect(reverse('user:profile'))
        except Exception as e:
            messages.error(request, f'更新失败：{str(e)}')
            return render(request, 'edit_profile.html', {'user': user})


@login_required
def change_email_view(request):
    """
    修改邮箱页面（中安全等级，需要验证码）
    """
    if request.method == 'GET':
        return render(request, 'change_email.html', {'user': request.user})
    else:
        new_email = request.POST.get('new_email', '').strip()
        verification_code = request.POST.get('verification_code', '').strip()

        if not new_email:
            messages.error(request, '请输入新邮箱')
            return render(request, 'change_email.html', {'user': request.user})

        if not verification_code:
            messages.error(request, '请输入验证码')
            return render(request, 'change_email.html', {'user': request.user})

        # 检查验证码是否正确
        stored_code = request.session.get('email_verification_code')
        if not stored_code or stored_code != verification_code:
            messages.error(request, '验证码错误或已过期')
            return render(request, 'change_email.html', {'user': request.user})

        # 检查新邮箱是否已被使用
        if CustomUser.objects.filter(email=new_email).exists():
            messages.error(request, '该邮箱已被其他用户使用')
            return render(request, 'change_email.html', {'user': request.user})

        try:
            # 更新邮箱并设置为未验证状态
            user = request.user
            user.email = new_email
            user.email_verified = False
            user.save()

            # 清除验证码
            del request.session['email_verification_code']

            # 发送验证邮件
            email_thread = threading.Thread(target=send_verification_email, args=(user,))
            email_thread.daemon = True
            email_thread.start()

            messages.success(request, '邮箱修改成功，请查收验证邮件并完成验证')
            return redirect(reverse('user:profile'))
        except Exception as e:
            messages.error(request, f'邮箱修改失败：{str(e)}')
            return render(request, 'change_email.html', {'user': request.user})


@login_required
def change_password_view(request):
    """
    修改密码页面（高安全等级，需要验证旧密码）
    """
    if request.method == 'GET':
        return render(request, 'change_password.html', {'user': request.user})
    else:
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not old_password:
            messages.error(request, '请输入当前密码')
            return render(request, 'change_password.html', {'user': request.user})

        if not new_password:
            messages.error(request, '请输入新密码')
            return render(request, 'change_password.html', {'user': request.user})

        if new_password != confirm_password:
            messages.error(request, '两次输入的新密码不一致')
            return render(request, 'change_password.html', {'user': request.user})

        # 验证旧密码
        user = request.user
        if not user.check_password(old_password):
            messages.error(request, '当前密码不正确')
            return render(request, 'change_password.html', {'user': user})

        try:
            user.set_password(new_password)
            user.save()

            # 更新密码后需要重新登录，指定认证后端
            from django.contrib.auth import get_backends
            backend_path = get_backends()[0].__module__ + '.' + get_backends()[0].__class__.__name__
            login(request, user, backend=backend_path)

            messages.success(request, '密码修改成功')
            return redirect(reverse('user:profile'))
        except Exception as e:
            messages.error(request, f'密码修改失败：{str(e)}')
            return render(request, 'change_password.html', {'user': user})


@login_required
def send_email_code_view(request):
    """
    发送邮箱验证码
    """
    if request.method == 'POST':
        # 生成4位随机验证码
        verification_code = ''.join(random.choices(string.digits, k=4))

        # 将验证码存储到session中，设置5分钟过期
        request.session['email_verification_code'] = verification_code
        request.session.set_expiry(300)  # 5分钟过期

        # 发送验证邮件
        subject = '校园博客 - 邮箱验证码'
        message = f"""
        尊敬的 {request.user.username}，
        
        您正在修改邮箱，验证码为：{verification_code}
        
        验证码5分钟内有效，请及时使用。
        
        如果您没有进行此操作，请忽略此邮件。
        
        校园博客团队
        """

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=False,
            )
            return JsonResponse({'status': 'success', 'message': '验证码已发送，请查收邮件'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'发送失败：{str(e)}'})

    return JsonResponse({'status': 'error', 'message': '请求方法错误'})


def forgot_password_view(request):
    """
    忘记密码页面
    """
    if request.method == 'GET':
        return render(request, 'forgot_password.html')
    else:
        email = request.POST.get('email', '').strip()
        student_number = request.POST.get('student_number', '').strip()
        
        if not email or not student_number:
            messages.error(request, '请填写邮箱和学号')
            return render(request, 'forgot_password.html')
        
        try:
            user = CustomUser.objects.get(email=email, student_number=student_number)
            
            # 生成重置哈希
            import hashlib
            import time
            reset_hash = hashlib.md5((email + student_number + str(int(time.time()))).encode()).hexdigest()
            
            # 存储重置哈希到session，设置20分钟过期
            request.session[f'password_reset_{user.id}'] = reset_hash
            request.session.set_expiry(1200)  # 20分钟过期
            
            # 发送重置邮件
            subject = '校园博客 - 密码重置'
            reset_url = f"{settings.SITE_URL}/user/reset_password/{user.id}/{reset_hash}"
            message = f"""
            尊敬的 {user.username}，
            
            您请求重置密码，请点击以下链接重置密码：
            
            {reset_url}
            
            该链接20分钟内有效，请及时使用。
            
            如果您没有请求重置密码，请忽略此邮件。
            
            校园博客团队
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            messages.success(request, '密码重置链接已发送到您的邮箱，请查收')
            return redirect(reverse('user:login'))
            
        except CustomUser.DoesNotExist:
            messages.error(request, '邮箱和学号不匹配')
            return render(request, 'forgot_password.html')
        except Exception as e:
            messages.error(request, f'发送失败：{str(e)}')
            return render(request, 'forgot_password.html')


def reset_password_view(request, user_uuid, reset_hash):
    """
    密码重置页面
    """
    try:
        user = CustomUser.objects.get(id=user_uuid)
        
        # 验证重置哈希
        stored_hash = request.session.get(f'password_reset_{user.id}')
        if not stored_hash or stored_hash != reset_hash:
            messages.error(request, '无效或已过期的重置链接')
            return redirect(reverse('user:login'))
            
        # 重置密码为学号
        user.set_password(user.student_number)
        user.save()
        
        # 清除重置哈希
        del request.session[f'password_reset_{user.id}']
        
        # 自动登录用户
        from django.contrib.auth import get_backends
        backend_path = get_backends()[0].__module__ + '.' + get_backends()[0].__class__.__name__
        login(request, user, backend=backend_path)
        
        return render(request, 'password_reset.html', {'user': user})
        
    except CustomUser.DoesNotExist:
        messages.error(request, '不存在的用户')
        return redirect(reverse('user:login'))
    except Exception as e:
        messages.error(request, f'重置失败：{str(e)}')
        return redirect(reverse('user:login'))


def user_profile_view(request, user_id):
    """
    显示目标用户的个人信息、文章和评论
    """
    try:
        target_user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return render(request, '404.html', status=404)

    # 获取用户发布的文章（最新版本）
    subquery = Article.objects.filter(
        author_id=target_user,
        deleted=False
    ).values('index_id').annotate(
        max_updated=Max('updated_at')
    )

    articles = Article.objects.filter(
        author_id=target_user,
        deleted=False,
        updated_at__in=[item['max_updated'] for item in subquery]
    ).order_by('-updated_at')

    # 为文章内容渲染Markdown并生成预览
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.sane_lists',
        'markdown.extensions.nl2br',
    ])

    for article in articles:
        article.content_html = md.convert(article.content)
        # 截取HTML内容的前200个字符作为预览，确保标签完整
        content_preview = article.content_html[:200]
        if len(article.content_html) > 200:
            # 确保不截断在标签中间
            last_open_tag = content_preview.rfind('<')
            last_close_tag = content_preview.rfind('>')
            if last_open_tag > last_close_tag:
                # 截断在标签中间，截取到上一个闭合标签
                content_preview = content_preview[:last_close_tag + 1]
            article.content_preview = content_preview + '...'
        else:
            article.content_preview = content_preview

    # 获取用户发布的评论（最新版本）
    all_comments = Comment.objects.filter(
        author=target_user,
        deleted=False,
        hidden=False
    ).order_by('-update_time')

    latest_comments = {}
    for comment in all_comments:
        if comment.index_id not in latest_comments:
            latest_comments[comment.index_id] = comment

    comments = list(latest_comments.values())
    comments.sort(key=lambda x: x.create_time, reverse=True)

    # 为评论渲染Markdown
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.sane_lists',
        'markdown.extensions.nl2br',
    ])

    for comment in comments:
        comment.content_html = md.convert(comment.content)
        comment.article = Article.objects.filter(
            index_id=comment.article_index_id,
            deleted=False
        ).order_by('-updated_at').first()

    # 分页处理
    article_paginator = Paginator(articles, 10)
    article_page = request.GET.get('article_page', 1)
    article_page_obj = article_paginator.get_page(article_page)

    comment_paginator = Paginator(comments, 10)
    comment_page = request.GET.get('comment_page', 1)
    comment_page_obj = comment_paginator.get_page(comment_page)

    context = {
        'target_user': target_user,
        'article_page_obj': article_page_obj,
        'comment_page_obj': comment_page_obj,
    }
    return render(request, 'user_profile.html', context)
