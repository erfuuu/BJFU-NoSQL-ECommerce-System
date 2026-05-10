from datetime import datetime
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib import messages
from mongoengine import DoesNotExist

from .models import UserProfile, Log

SESSION_KEYS = {
    'consumer': 'consumer_user_id',
    'business': 'business_user_id',
    'manager': 'manager_user_id',
}

def get_session_key(user_type):
    return SESSION_KEYS.get(user_type)

def get_user_id_by_type(request, user_type):
    session_key = get_session_key(user_type)
    return request.session.get(session_key) if session_key else None

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
            session_key = get_session_key(user.type)
            
            if session_key:
                existing_user_id = request.session.get(session_key)
                if existing_user_id and existing_user_id != user.user_id:
                    messages.error(request, f"当前浏览器已有{user.type}类型的其他用户登录，请先登出")
                    return render(request, 'login.html')

                # 记录登录事件
                create_log(event_type="login", user_id=user.user_id, details={"status": "success"})
                request.session[session_key] = user.user_id
                
                if user.type == 'consumer':
                    return redirect('consumer_home')
                elif user.type == 'business':
                    return redirect('business_home')
                elif user.type == 'manager':
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

# 通用登录验证装饰器（检查任一类型用户是否登录）
def login_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        for session_key in SESSION_KEYS.values():
            user_id = request.session.get(session_key)
            if user_id:
                try:
                    UserProfile.objects.get(user_id=user_id)
                    return view_func(request, *args, **kwargs)
                except DoesNotExist:
                    pass
        return redirect('login')
    return _wrapped_view

# 消费者专用装饰器
def consumer_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        user_id = get_user_id_by_type(request, 'consumer')
        if user_id:
            try:
                UserProfile.objects.get(user_id=user_id)
                return view_func(request, *args, **kwargs)
            except DoesNotExist:
                pass
        return redirect('login')
    return _wrapped_view

# 商家专用装饰器
def business_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        user_id = get_user_id_by_type(request, 'business')
        if user_id:
            try:
                UserProfile.objects.get(user_id=user_id)
                return view_func(request, *args, **kwargs)
            except DoesNotExist:
                pass
        return redirect('login')
    return _wrapped_view

# 管理员专用装饰器
def manager_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        user_id = get_user_id_by_type(request, 'manager')
        if user_id:
            try:
                UserProfile.objects.get(user_id=user_id)
                return view_func(request, *args, **kwargs)
            except DoesNotExist:
                pass
        return redirect('login')
    return _wrapped_view

def logout_consumer_view(request):
    session_key = get_session_key('consumer')
    if session_key in request.session:
        del request.session[session_key]
    return redirect('login')

def logout_business_view(request):
    session_key = get_session_key('business')
    if session_key in request.session:
        del request.session[session_key]
    return redirect('login')

def logout_manager_view(request):
    session_key = get_session_key('manager')
    if session_key in request.session:
        del request.session[session_key]
    return redirect('login')

def logout_all_view(request):
    for session_key in SESSION_KEYS.values():
        if session_key in request.session:
            del request.session[session_key]
    return redirect('login')
