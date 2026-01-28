from datetime import datetime
from decimal import Decimal
from django.contrib.sessions.models import Session
from django.shortcuts import render, redirect
from django.contrib import messages
from mongoengine import DoesNotExist

from .models import UserProfile, Log

def create_log(event_type, user_id=None, details=None):
    """
    创建日志记录并保存到 MongoDB 的 logs 集合中
    """
    if details is None:
        details = {}

    # 将 Decimal 类型转换为 float
    for key, value in details.items():
        if isinstance(value, Decimal):
            details[key] = float(value)

    try:
        log = Log(
            event_type=event_type,
            user_id=user_id,
            details=details,
            timestamp=datetime.utcnow()
        )
        log.save()
    except Exception as e:
        print(f"Failed to save log: {e}")


#登录视图
def login_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        password = request.POST.get('password')
        user = UserProfile.objects(user_id=user_id, password=password).first()

        if user:
            # 记录登录事件
            create_log(event_type="login", user_id=user.user_id, details={"status": "success"})
            # 根据用户类型设置不同的session key，避免不同身份账号互相覆盖
            if user.type == 'consumer':
                request.session['consumer_user_id'] = user.user_id
                request.session['user_type'] = 'consumer'
                return redirect('consumer_home')
            elif user.type == 'business':
                request.session['business_user_id'] = user.user_id
                request.session['user_type'] = 'business'
                return redirect('business_home')
            elif user.type == 'manager':
                request.session['manager_user_id'] = user.user_id
                request.session['user_type'] = 'manager'
                return redirect('logs_view')
        else:
            # 记录失败的登录尝试
            create_log(event_type="login", details={"user_id": user_id, "status": "failed"})
            messages.error(request, "用户名或密码错误")

    return render(request, 'login.html')

#注册视图
def register_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        password = request.POST.get('password')
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        user_type = request.POST.get('type')  # 获取用户类型

        # 检查用户ID是否已经存在
        if UserProfile.objects.filter(user_id=user_id).count() > 0:
            messages.error(request, "User ID already exists.")
            return redirect('register')

        # 创建新用户
        new_user = UserProfile(
            user_id=user_id,
            password=password,  # 在实际应用中，确保对密码进行加密处理！
            name=name,
            address=address,
            phone=phone,
            type=user_type  # 保存用户类型
        )
        new_user.save()

        messages.success(request, "Registration successful. Please log in.")
        return redirect('login')  # 注册成功后跳转到登录页面

    return render(request, 'register.html')

# 自定义登录验证装饰器
def login_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        # 根据请求路径判断用户类型，使用对应的session key
        user_id = None
        path = request.path
        
        # 根据路径判断用户类型
        if '/consumer' in path:
            user_id = request.session.get('consumer_user_id')
        elif '/business' in path:
            user_id = request.session.get('business_user_id')
        elif '/manager' in path:
            user_id = request.session.get('manager_user_id')
        else:
            # 默认检查所有可能的session key
            user_id = (request.session.get('consumer_user_id') or 
                      request.session.get('business_user_id') or 
                      request.session.get('manager_user_id'))
        
        if user_id:
            try:
                # 验证用户是否存在
                UserProfile.objects.get(user_id=user_id)
                return view_func(request, *args, **kwargs)
            except DoesNotExist:
                # 用户不存在，清除会话并重定向到登录页面
                request.session.flush()
        # 如果用户未登录，重定向到登录页面
        return redirect('login')
    return _wrapped_view

