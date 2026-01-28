from datetime import datetime

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Log, Comment, Product, UserProfile
from .views import login_required


MANAGER_LOGS_PAGE_SIZE = 20
MANAGER_COMMENTS_PAGE_SIZE = 20
MANAGER_USERS_PAGE_SIZE = 10


def get_manager_user_id(request):
    """
    从 session 中获取管理员用户 ID
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        str: 管理员用户 ID，如果未登录则返回 None
    """
    return request.session.get('manager_user_id')


def verify_manager_permission(request):
    """
    验证用户是否为管理员
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        UserProfile: 管理员用户对象，如果不是管理员则返回 None
    """
    manager_user_id = get_manager_user_id(request)
    user = UserProfile.objects(user_id=manager_user_id).first()
    
    if user and user.user_type == 'manager':
        return user
    return None


@login_required
def logs_view(request):
    """
    系统日志视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染日志管理页面
    """
    event_type_filter = request.GET.get('query', '')
    user_id_filter = request.GET.get('user_id', '')
    start_date_filter = request.GET.get('start_date')
    end_date_filter = request.GET.get('end_date')
    page_number = request.GET.get('page', 1)

    logs = Log.objects.all()

    if event_type_filter:
        logs = logs.filter(log_event_type__icontains=event_type_filter)

    if user_id_filter:
        logs = logs.filter(log_user_id=user_id_filter)

    if start_date_filter:
        try:
            start_date_obj = datetime.strptime(start_date_filter, "%Y-%m-%d")
            logs = logs.filter(log_timestamp__gte=start_date_obj)
        except ValueError:
            pass

    if end_date_filter:
        try:
            end_date_obj = datetime.strptime(end_date_filter, "%Y-%m-%d")
            logs = logs.filter(log_timestamp__lte=end_date_obj)
        except ValueError:
            pass

    paginator = Paginator(logs.order_by('-log_timestamp'), MANAGER_LOGS_PAGE_SIZE)
    page_obj = paginator.get_page(page_number)

    context = {
        'logs': page_obj,
        'query': event_type_filter,
        'user_id': user_id_filter,
        'start_date': start_date_filter,
        'end_date': end_date_filter,
        'page_obj': page_obj,
    }
    return render(request, 'admin_logs.html', context)


@login_required
def comments_view(request):
    """
    评论管理视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染评论管理页面
    """
    manager_user = verify_manager_permission(request)
    if not manager_user:
        return JsonResponse({"success": False, "message": "权限不足"}, status=403)

    user_id_filter = request.GET.get('user_id', '')
    page_number = request.GET.get('page', 1)

    if user_id_filter:
        comments = Comment.objects.filter(user_id__icontains=user_id_filter).order_by('-comment_timestamp')
    else:
        comments = Comment.objects.all().order_by('-comment_timestamp')

    paginator = Paginator(comments, MANAGER_COMMENTS_PAGE_SIZE)
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_comments.html', {
        'comments': page_obj,
        'query': user_id_filter,
        'page_obj': page_obj,
    })


@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def delete_comment_view(request, comment_id):
    """
    删除评论视图
    
    Args:
        request: Django HttpRequest 对象
        comment_id (int): 评论 ID
    
    Returns:
        JsonResponse: 操作结果的 JSON 响应
    """
    manager_user = verify_manager_permission(request)
    if not manager_user:
        return JsonResponse({"success": False, "message": "权限不足"}, status=403)

    comment = Comment.objects.filter(comment_id=comment_id).first()
    if comment:
        comment.delete()
        return JsonResponse({"success": True, "message": "评论已成功删除"})
    else:
        return JsonResponse({"success": False, "message": "评论未找到"}, status=404)


@login_required
def clicks_view(request):
    """
    商品点击量统计视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染点击量统计页面
    """
    manager_user = verify_manager_permission(request)
    if not manager_user:
        return redirect('login')

    product_id_filter = request.GET.get('product_id', '')
    if product_id_filter:
        products = Product.objects.filter(product_id=int(product_id_filter))
    else:
        products = Product.objects.all()

    products = sorted(products, key=lambda x: x.product_click_count, reverse=True)

    products_list = [
        {
            "product_id": product.product_id,
            "name": product.product_name,
            "clicks": product.product_click_count
        }
        for product in products
    ]

    return render(request, 'admin_clicks.html', {'products': products_list, 'query': product_id_filter})


@login_required
def users_view(request):
    """
    用户管理视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染用户管理页面
    """
    manager_user = verify_manager_permission(request)
    if not manager_user:
        return redirect('login')

    user_id_filter = request.GET.get('user_id', '')
    page_number = request.GET.get('page', 1)

    users = UserProfile.objects.filter(user_id__icontains=user_id_filter) if user_id_filter else UserProfile.objects.all()

    paginator = Paginator(users, MANAGER_USERS_PAGE_SIZE)
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_users.html', {'users': page_obj, 'query': user_id_filter, 'page_obj': page_obj})


@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def delete_user_view(request, user_id):
    """
    删除用户视图
    
    Args:
        request: Django HttpRequest 对象
        user_id (str): 用户 ID
    
    Returns:
        JsonResponse: 操作结果的 JSON 响应
    """
    admin_user = verify_manager_permission(request)
    if not admin_user:
        return JsonResponse({"success": False, "message": "权限不足"}, status=403)

    user_to_delete = UserProfile.objects.filter(user_id=user_id).first()
    if user_to_delete:
        if user_to_delete.user_type == 'manager':
            return JsonResponse({"success": False, "message": "不能删除管理员账户"}, status=403)
        user_to_delete.delete()
        return JsonResponse({"success": True, "message": f"用户 {user_id} 已成功删除"})
    else:
        return JsonResponse({"success": False, "message": f"用户 {user_id} 未找到"}, status=404)
