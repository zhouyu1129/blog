from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
import threading
from .models import CustomUser


def send_verification_email(user):
    """
    发送邮箱验证邮件的函数
    """
    subject = '校园博客 - 邮箱验证'
    verification_url = f"{settings.SITE_URL}/user/email_verify/{user.id}"
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
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # 首先检查用户是否存在，以便提供更具体的错误信息
        try:
            user_obj = CustomUser.objects.get(email=email)
            if not user_obj.check_password(password):
                messages.error(request, '邮箱或密码错误，请重试')
                return render(request, 'login.html')
            elif not user_obj.email_verified:
                # 重新发送验证邮件
                email_thread = threading.Thread(target=send_verification_email, args=(user_obj,))
                email_thread.daemon = True
                email_thread.start()
                messages.error(request, '请先验证邮箱后再登录。验证邮件已重新发送，请查收。')
                return render(request, 'login.html')
        except CustomUser.DoesNotExist:
            messages.error(request, '邮箱或密码错误，请重试')
            return render(request, 'login.html')
            
        # 使用email进行认证
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, '登录成功！')
            return redirect(reverse('index'))
        else:
            messages.error(request, '登录失败，请重试')
            return render(request, 'login.html')


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
def email_verify(request, user_uuid):
    try:
        user_obj = CustomUser.objects.get(id=user_uuid)
        if user_obj.email_verified:
            messages.error(request, '重复的邮箱验证')
            return redirect(reverse('index'))
        user_obj.email_verified = True
        user_obj.save()
        return render(request, 'email_verified.html', {'user': user_obj, 'target_url': reverse('user:login')})
    except CustomUser.DoesNotExist:
        messages.error(request, '不存在的用户')
        return redirect(reverse('index'))
