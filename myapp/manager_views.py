from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import Log, Comment, Product, UserProfile
from .views import login_required

@login_required
def logs_view(request):
    query = request.GET.get('query', '')  # 事件类型
    user_id = request.GET.get('user_id', '')  # 用户ID
    start_date = request.GET.get('start_date')  # 开始日期
    end_date = request.GET.get('end_date')  # 结束日期

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
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        logs = logs.filter(timestamp__gte=start_date_obj)
    if end_date:
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        logs = logs.filter(timestamp__lte=end_date_obj)

    # 返回上下文
    context = {
        'logs': logs,
        'query': query,
        'user_id': user_id,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'admin_logs.html', context)


@login_required
def comments_view(request):
    user_id = request.session.get('user_id')
    user = UserProfile.objects(user_id=user_id).first()

    # 确保只有管理员可以访问
    if user.type != 'manager':
        return redirect('login')

    # 按用户ID筛选评论
    query = request.GET.get('user_id', '')
    comments = Comment.objects.filter(user_id__icontains=query) if query else Comment.objects.all()

    if request.method == 'POST':
        # 获取评论ID并删除评论
        comment_id = request.POST.get('comment_id')
        comment = Comment.objects(comment_id=comment_id).first()
        if comment:
            comment.delete()
            return JsonResponse({"success": True, "message": "评论已删除"})
        return JsonResponse({"success": False, "message": "评论未找到"})

    return render(request, 'admin_comments.html', {'comments': comments, 'query': query})


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

    # 将 MongoEngine 查询结果手动转换为字典列表
    products_list = [
        {
            "product_id": product.product_id,
            "name": product.name,
            "clicks": product.clicks
        }
        for product in products
    ]

    # 调试日志
    print("序列化后的产品数据:", products_list)

    # 渲染模板
    return render(request, 'admin_clicks.html', {'products': products_list, 'query': query})


@login_required
def users_view(request):
    user_id = request.session.get('user_id')
    user = UserProfile.objects(user_id=user_id).first()

    # 确保只有管理员可以访问
    if user.type != 'manager':
        return redirect('login')

    # 按用户ID搜索用户
    query = request.GET.get('user_id', '')
    users = UserProfile.objects.filter(user_id__icontains=query) if query else UserProfile.objects.all()

    if request.method == 'POST':
        # 删除用户逻辑
        delete_user_id = request.POST.get('delete_user_id')
        user_to_delete = UserProfile.objects(user_id=delete_user_id).first()

        if user_to_delete:
            if user_to_delete.type != 'manager':  # 禁止删除管理员账户
                user_to_delete.delete()
                return JsonResponse({"success": True, "message": "用户已成功删除"})
            else:
                return JsonResponse({"success": False, "message": "管理员用户无法删除"})
        return JsonResponse({"success": False, "message": "用户未找到"})

    return render(request, 'admin_users.html', {'users': users, 'query': query})
