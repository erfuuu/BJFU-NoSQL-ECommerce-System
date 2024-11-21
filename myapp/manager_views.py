from datetime import datetime

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Log, Comment, Product, UserProfile
from .views import login_required

@login_required
def logs_view(request):
    query = request.GET.get('query', '')  # 事件类型
    user_id = request.GET.get('user_id', '')  # 用户ID
    start_date = request.GET.get('start_date')  # 开始日期
    end_date = request.GET.get('end_date')  # 结束日期
    page_number = request.GET.get('page', 1)  # 当前页码

    # 初始查询集
    logs = Log.objects.all()

    # 按事件类型筛选
    if query:
        logs = logs.filter(event_type__icontains=query)

    # 按用户ID筛选
    if user_id:
        logs = logs.filter(user_id=user_id)

    # 按时间范围筛选
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            logs = logs.filter(timestamp__gte=start_date_obj)
        except ValueError:
            pass  # 如果日期格式无效，忽略此条件
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            logs = logs.filter(timestamp__lte=end_date_obj)
        except ValueError:
            pass  # 如果日期格式无效，忽略此条件

    # 添加分页
    paginator = Paginator(logs.order_by('-timestamp'), 20)  # 每页20条
    page_obj = paginator.get_page(page_number)

    # 返回上下文
    context = {
        'logs': page_obj,
        'query': query,
        'user_id': user_id,
        'start_date': start_date,
        'end_date': end_date,
        'page_obj': page_obj,
    }
    return render(request, 'admin_logs.html', context)


@login_required
def comments_view(request):
    user_id = request.session.get('user_id')
    user = UserProfile.objects(user_id=user_id).first()

    # 确保只有管理员可以访问
    if not user or user.type != 'manager':
        return JsonResponse({"success": False, "message": "权限不足"}, status=403)

    # 获取筛选条件
    query = request.GET.get('user_id', '')  # 用户ID筛选
    page = request.GET.get('page', 1)  # 当前页码

    # 查询评论
    if query:
        comments = Comment.objects.filter(user_id__icontains=query).order_by('-timestamp')
    else:
        comments = Comment.objects.all().order_by('-timestamp')

    # 分页处理，每页显示20条评论
    paginator = Paginator(comments, 20)
    page_obj = paginator.get_page(page)

    # 渲染评论管理页面
    return render(request, 'admin_comments.html', {
        'comments': page_obj,
        'query': query,
        'page_obj': page_obj,
    })

@csrf_exempt  # 确保支持 AJAX 请求
@login_required
@require_http_methods(["DELETE"])
def delete_comment_view(request, comment_id):
    user_id = request.session.get('user_id')
    user = UserProfile.objects(user_id=user_id).first()

    # 确保只有管理员可以删除评论
    if not user or user.type != 'manager':
        return JsonResponse({"success": False, "message": "权限不足"}, status=403)

    comment = Comment.objects.filter(comment_id=comment_id).first()
    if comment:
        comment.delete()
        return JsonResponse({"success": True, "message": "评论已成功删除"})
    else:
        return JsonResponse({"success": False, "message": "评论未找到"}, status=404)

@login_required
def clicks_view(request):
    user_id = request.session.get('user_id')
    user = UserProfile.objects(user_id=user_id).first()

    # 验证用户权限
    if not user or user.type != 'manager':
        return redirect('login')

    # 获取查询参数并筛选产品
    query = request.GET.get('product_id', '')
    if query:
        products = Product.objects.filter(product_id=int(query))
    else:
        products = Product.objects.all()

    # 按点击量降序排序
    products = sorted(products, key=lambda x: x.clicks, reverse=True)

    # 将 MongoEngine 查询结果手动转换为字典列表
    products_list = [
        {
            "product_id": product.product_id,
            "name": product.name,
            "clicks": product.clicks
        }
        for product in products
    ]

    # 渲染模板
    return render(request, 'admin_clicks.html', {'products': products_list, 'query': query})


@login_required
def users_view(request):
    user_id = request.session.get('user_id')
    user = UserProfile.objects(user_id=user_id).first()

    # 确保只有管理员可以访问
    if not user or user.type != 'manager':
        return redirect('login')

    # 获取搜索条件和分页参数
    query = request.GET.get('user_id', '')
    page_number = request.GET.get('page', 1)

    # 查询用户
    users = UserProfile.objects.filter(user_id__icontains=query) if query else UserProfile.objects.all()

    # 分页
    paginator = Paginator(users, 10)  # 每页10个用户
    page_obj = paginator.get_page(page_number)

    # 渲染用户管理页面
    return render(request, 'admin_users.html', {'users': page_obj, 'query': query, 'page_obj': page_obj})

@csrf_exempt  # 确保支持 AJAX 请求
@login_required
@require_http_methods(["DELETE"])
def delete_user_view(request, user_id):
    admin_user_id = request.session.get('user_id')
    admin_user = UserProfile.objects(user_id=admin_user_id).first()

    # 确保只有管理员可以删除用户
    if not admin_user or admin_user.type != 'manager':
        return JsonResponse({"success": False, "message": "权限不足"}, status=403)

    user_to_delete = UserProfile.objects.filter(user_id=user_id).first()
    if user_to_delete:
        if user_to_delete.type == 'manager':
            return JsonResponse({"success": False, "message": "不能删除管理员账户"}, status=403)
        user_to_delete.delete()
        return JsonResponse({"success": True, "message": f"用户 {user_id} 已成功删除"})
    else:
        return JsonResponse({"success": False, "message": f"用户 {user_id} 未找到"}, status=404)
