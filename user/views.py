import hashlib
import random
import string
import threading

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
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
            backend = get_backends()[0]  # 获取第一个认证后端
            login(request, user, backend=backend)

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
