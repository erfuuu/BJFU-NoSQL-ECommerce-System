from datetime import datetime
from decimal import Decimal
from django.contrib.sessions.models import Session
from django.shortcuts import render, redirect
from django.contrib import messages
from mongoengine import DoesNotExist

from .models import UserProfile, Log


def create_system_log(event_type, user_id=None, details=None):
    """
    创建系统日志记录并保存到 MongoDB 的 logs 集合中
    
    Args:
        event_type (str): 事件类型，如 "login", "view_product", "create_order" 等
        user_id (str, optional): 触发事件的用户ID
        details (dict, optional): 事件详情，包含事件的具体信息
    
    Returns:
        None
    """
    if details is None:
        details = {}

    for key, value in details.items():
        if isinstance(value, Decimal):
            details[key] = float(value)

    try:
        log_entry = Log(
            log_event_type=event_type,
            log_user_id=user_id,
            log_details=details,
            log_timestamp=datetime.utcnow()
        )
        log_entry.save()
    except Exception as error:
        print(f"Failed to save log: {error}")


def login_view(request):
    """
    处理用户登录请求
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 登录页面或重定向到用户主页
    """
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        password = request.POST.get('password')
        user_profile = UserProfile.objects(user_id=user_id, password=password).first()

        if user_profile:
            create_system_log(event_type="login", user_id=user_profile.user_id, details={"status": "success"})
            
            if user_profile.user_type == 'consumer':
                request.session['consumer_user_id'] = user_profile.user_id
                request.session['user_type'] = 'consumer'
                return redirect('consumer_home')
            elif user_profile.user_type == 'business':
                request.session['business_user_id'] = user_profile.user_id
                request.session['user_type'] = 'business'
                return redirect('business_home')
            elif user_profile.user_type == 'manager':
                request.session['manager_user_id'] = user_profile.user_id
                request.session['user_type'] = 'manager'
                return redirect('logs_view')
        else:
            create_system_log(event_type="login", details={"user_id": user_id, "status": "failed"})
            messages.error(request, "用户名或密码错误")

    return render(request, 'login.html')


def register_view(request):
    """
    处理用户注册请求
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 注册页面或重定向到登录页面
    """
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        password = request.POST.get('password')
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        user_type = request.POST.get('type')

        if UserProfile.objects.filter(user_id=user_id).count() > 0:
            messages.error(request, "User ID already exists.")
            return redirect('register')

        new_user_profile = UserProfile(
            user_id=user_id,
            password=password,
            name=name,
            address=address,
            phone=phone,
            user_type=user_type
        )
        new_user_profile.save()

        messages.success(request, "Registration successful. Please log in.")
        return redirect('login')

    return render(request, 'register.html')


def login_required(view_func):
    """
    自定义登录验证装饰器，用于保护需要登录才能访问的视图
    
    Args:
        view_func: 被装饰的视图函数
    
    Returns:
        function: 包装后的视图函数
    """
    def _wrapped_view(request, *args, **kwargs):
        user_id = None
        request_path = request.path
        
        if '/consumer' in request_path:
            user_id = request.session.get('consumer_user_id')
        elif '/business' in request_path:
            user_id = request.session.get('business_user_id')
        elif '/manager' in request_path:
            user_id = request.session.get('manager_user_id')
        else:
            user_id = (request.session.get('consumer_user_id') or 
                      request.session.get('business_user_id') or 
                      request.session.get('manager_user_id'))
        
        if user_id:
            try:
                UserProfile.objects.get(user_id=user_id)
                return view_func(request, *args, **kwargs)
            except DoesNotExist:
                request.session.flush()
        
        return redirect('login')
    
    return _wrapped_view
