from datetime import datetime
from decimal import Decimal

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from mongoengine import Q
import json
import uuid

from .models import Product, Comment, Order, UserProfile
from .views import login_required, create_system_log


PAGINATION_PAGE_SIZE = 10
SEARCH_PAGE_SIZE = 12
ADMIN_LOGS_PAGE_SIZE = 20
ADMIN_COMMENTS_PAGE_SIZE = 20
ADMIN_USERS_PAGE_SIZE = 10


def get_consumer_user_id(request):
    """
    从 session 中获取消费者用户 ID
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        str: 消费者用户 ID，如果未登录则返回 None
    """
    return request.session.get('consumer_user_id')


def build_product_search_query(search_keyword):
    """
    构建商品搜索查询条件
    
    Args:
        search_keyword (str): 搜索关键字
    
    Returns:
        Q: MongoEngine 查询对象
    """
    if search_keyword.isdigit():
        return Q(product_id=int(search_keyword)) | Q(product_name__icontains=search_keyword) | Q(product_tags__icontains=search_keyword)
    else:
        return Q(product_name__icontains=search_keyword) | Q(product_tags__icontains=search_keyword)


def calculate_average_rating(comments):
    """
    计算评论的平均评分
    
    Args:
        comments: 评论列表
    
    Returns:
        float or str: 平均评分，如果没有评论则返回 "暂无评分"
    """
    if comments:
        total_rating = sum(comment.comment_rating for comment in comments if comment.comment_rating)
        return round(total_rating / len(comments), 1)
    return "暂无评分"


@csrf_exempt
def get_product_clicks_api(request):
    """
    获取商品点击量的 API 接口
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        JsonResponse: 包含商品点击量数据的 JSON 响应
    """
    if request.method == 'POST':
        try:
            request_data = json.loads(request.body)
            product_ids = request_data.get('product_ids', [])
            
            if not product_ids:
                return JsonResponse({'success': False, 'message': '未提供商品ID列表'})
            
            clicks_data = []
            for product_id in product_ids:
                product = Product.objects(product_id=int(product_id)).first()
                if product:
                    clicks_data.append({
                        'product_id': product_id,
                        'clicks': product.product_click_count
                    })
            
            return JsonResponse({'success': True, 'clicks_data': clicks_data})
        except Exception as error:
            return JsonResponse({'success': False, 'message': str(error)})
    
    return JsonResponse({'success': False, 'message': '仅支持POST请求'})


@login_required
def consumer_home_view(request):
    """
    消费者主页视图，显示商品列表
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染消费者主页
    """
    search_keyword = request.GET.get('query', '').strip()
    products = Product.objects.all().order_by('-product_sales_volume')

    if search_keyword:
        products = products.filter(build_product_search_query(search_keyword))

    paginator = Paginator(products, PAGINATION_PAGE_SIZE)
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)

    return render(request, 'consumer_home.html', {'products': products_page, 'query': search_keyword})


@login_required
def search_products_view(request):
    """
    商品搜索视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染搜索结果页面
    """
    search_keyword = request.GET.get('query', '').strip()
    all_products = Product.objects.all().order_by('-product_sales_volume')

    if search_keyword:
        all_products = all_products.filter(build_product_search_query(search_keyword))

    paginator = Paginator(all_products, SEARCH_PAGE_SIZE)
    page_number = request.GET.get('page', 1)
    products = paginator.get_page(page_number)

    return render(request, 'consumer_home.html', {
        'products': products,
        'query': search_keyword,
    })


@login_required
def product_detail_view(request, product_id):
    """
    商品详情页视图
    
    Args:
        request: Django HttpRequest 对象
        product_id (int): 商品 ID
    
    Returns:
        HttpResponse: 渲染商品详情页
    """
    product = Product.objects(product_id=product_id).first()
    if not product:
        return render(request, '404.html')

    product.product_click_count += 1
    product.save()

    comments = Comment.objects(product_id=product_id).order_by('-comment_like_count')
    average_rating = calculate_average_rating(comments)

    context = {
        'product': product,
        'comments': comments,
        'average_rating': average_rating,
        'user_is_authenticated': request.user.is_authenticated
    }

    create_system_log(event_type="view_product", user_id=get_consumer_user_id(request), details={"product_id": product_id})

    return render(request, 'product_detail.html', context)


@login_required
def add_to_cart_view(request, product_id):
    """
    添加商品到购物车
    
    Args:
        request: Django HttpRequest 对象
        product_id (int): 商品 ID
    
    Returns:
        JsonResponse: 操作结果的 JSON 响应
    """
    if request.method == "POST":
        user_id = get_consumer_user_id(request)
        if not user_id:
            return JsonResponse({"success": False, "error": "用户未登录"})

        user_profile = UserProfile.objects(user_id=user_id).first()
        if not user_profile:
            return JsonResponse({"success": False, "error": "用户信息未找到"})
        
        delivery_address = user_profile.get_delivery_address()
        contact_phone = user_profile.get_contact_phone()

        request_data = json.loads(request.body)
        quantity = int(request_data.get("quantity", 1))

        cart_order = Order.objects.filter(user_id=user_id, order_status="In Cart").first()
        if not cart_order:
            cart_order = Order(
                order_id=str(uuid.uuid4()),
                user_id=user_id,
                order_items=[],
                order_status="In Cart",
                order_timestamp=datetime.utcnow(),
                delivery_address=delivery_address,
                contact_phone=contact_phone
            )

        product_found = False
        for order_item in cart_order.order_items:
            if order_item["product_id"] == product_id:
                order_item["quantity"] += quantity
                product_found = True
                break
        if not product_found:
            cart_order.order_items.append({"product_id": product_id, "quantity": quantity})

        cart_order.calculate_order_total()
        cart_order.save()

        return JsonResponse({"success": True, "message": "商品已成功加入购物车！"})
    
    return JsonResponse({"success": False, "error": "无效请求"})


@login_required
def buy_now_view(request, product_id):
    """
    立即购买商品
    
    Args:
        request: Django HttpRequest 对象
        product_id (int): 商品 ID
    
    Returns:
        JsonResponse: 操作结果的 JSON 响应
    """
    if request.method == "POST":
        user_id = get_consumer_user_id(request)
        request_data = json.loads(request.body)
        quantity = int(request_data.get("quantity", 1))

        user_profile = UserProfile.objects(user_id=user_id).first()
        if not user_profile:
            return JsonResponse({"success": False, "error": "用户信息未找到"})
        
        delivery_address = user_profile.get_delivery_address()
        contact_phone = user_profile.get_contact_phone()

        product = Product.objects(product_id=product_id).first()
        if not product:
            return JsonResponse({"success": False, "error": "商品未找到"})

        total_amount = product.product_price * quantity

        new_order = Order(
            order_id=str(uuid.uuid4()),
            user_id=user_id,
            order_items=[{"product_id": product_id, "quantity": quantity}],
            order_total_amount=total_amount,
            order_status="Pending",
            order_timestamp=datetime.utcnow(),
            delivery_address=delivery_address,
            contact_phone=contact_phone
        )
        new_order.save()

        product.product_stock -= quantity
        product.product_sales_volume += quantity
        product.save()

        create_system_log(event_type="create_order", user_id=user_id,
                         details={"order_id": new_order.order_id, "total_amount": total_amount})

        return JsonResponse({"success": True, "message": "订单已创建并等待发货！"})
    
    return JsonResponse({"success": False, "error": "无效请求"})


@csrf_exempt
@login_required
def like_comment_view(request, comment_id):
    """
    点赞评论
    
    Args:
        request: Django HttpRequest 对象
        comment_id (int): 评论 ID
    
    Returns:
        JsonResponse: 操作结果的 JSON 响应
    """
    if request.method == 'POST':
        comment = Comment.objects(comment_id=comment_id).first()
        if not comment:
            return JsonResponse({"success": False, "message": "评论不存在"})

        comment.increment_like_count()
        return JsonResponse({"success": True, "likes": comment.comment_like_count})

    return JsonResponse({"success": False, "message": "仅支持 POST 请求"})


@login_required
def cart_view(request):
    """
    购物车视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染购物车页面
    """
    user_id = get_consumer_user_id(request)
    in_cart_orders = Order.objects(user_id=user_id, order_status="In Cart")
    return render(request, 'cart.html', {'in_cart_orders': in_cart_orders})


@login_required
def purchase_order_view(request, order_id):
    """
    从购物车下单
    
    Args:
        request: Django HttpRequest 对象
        order_id (str): 订单 ID
    
    Returns:
        JsonResponse: 操作结果的 JSON 响应
    """
    if request.method == "POST":
        user_id = get_consumer_user_id(request)
        order = Order.objects(order_id=order_id, user_id=user_id, order_status="In Cart").first()
        if order:
            order.order_status = "Pending"
            order.order_timestamp = datetime.utcnow()
            for order_item in order.order_items:
                product = Product.objects(product_id=order_item["product_id"]).first()
                if product:
                    if product.product_stock >= order_item["quantity"]:
                        product.product_stock -= order_item["quantity"]
                        product.product_sales_volume += order_item["quantity"]
                        product.save()
                    else:
                        return JsonResponse({"success": False, "error": f"商品 {product.product_name} 库存不足"})
            order.save()
            create_system_log(event_type="create_order", user_id=user_id,
                             details={"order_id": order.order_id, "total_amount": order.order_total_amount})
            return JsonResponse({"success": True, "message": "订单已更新为待处理状态！"})
        return JsonResponse({"success": False, "error": "订单未找到或无法更新"})
    return JsonResponse({"success": False, "error": "无效请求"})


@login_required
@require_http_methods(["DELETE"])
def delete_order_view(request, order_id):
    """
    删除购物车中的订单
    
    Args:
        request: Django HttpRequest 对象
        order_id (str): 订单 ID
    
    Returns:
        JsonResponse: 操作结果的 JSON 响应
    """
    user_id = get_consumer_user_id(request)
    order = Order.objects.filter(order_id=order_id, user_id=user_id, order_status="In Cart").first()

    if order:
        order.delete()
        return JsonResponse({"success": True, "message": "订单已删除"})
    else:
        return JsonResponse({"success": False, "error": "订单未找到或无法删除"}, status=404)


@login_required
def order_view(request):
    """
    订单列表视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染订单列表页面
    """
    user_id = get_consumer_user_id(request)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    orders = Order.objects.filter(user_id=user_id, order_status__in=["Pending", "Shipped", "Delivered", "Completed"]).order_by('-order_timestamp')

    if start_date:
        orders = orders.filter(order_timestamp__gte=datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        orders = orders.filter(order_timestamp__lte=datetime.strptime(end_date, '%Y-%m-%d'))

    return render(request, 'order.html', {'orders': orders, 'start_date': start_date, 'end_date': end_date})


@login_required
def confirm_receipt_view(request, order_id):
    """
    确认收货
    
    Args:
        request: Django HttpRequest 对象
        order_id (str): 订单 ID
    
    Returns:
        JsonResponse: 操作结果的 JSON 响应
    """
    if request.method == "POST":
        try:
            order = Order.objects.get(order_id=order_id)
            if order.order_status == "Delivered":
                order.order_status = "Completed"
                order.save()
                return JsonResponse({"success": True, "message": "订单已确认收货"})
            else:
                return JsonResponse({"success": False, "message": "订单状态不允许确认收货"})
        except Order.DoesNotExist:
            return JsonResponse({"success": False, "message": "订单未找到"}, status=404)
        except Exception as error:
            return JsonResponse({"success": False, "message": str(error)}, status=500)
    return JsonResponse({"success": False, "message": "无效请求"}, status=400)


@login_required
def add_comment_for_order_view(request, order_id, product_id):
    """
    为订单商品添加评论
    
    Args:
        request: Django HttpRequest 对象
        order_id (str): 订单 ID
        product_id (int): 商品 ID
    
    Returns:
        JsonResponse: 操作结果的 JSON 响应
    """
    if request.method == "POST":
        user_id = get_consumer_user_id(request)
        order = Order.objects.filter(order_id=order_id, user_id=user_id).first()

        if order:
            if order.order_status == "Completed":
                comment_content = request.POST.get("content")
                comment_rating = float(request.POST.get("rating"))

                response = Comment.create_new_comment(
                    product_id=product_id,
                    user_id=user_id,
                    content=comment_content,
                    rating=comment_rating
                )

                return JsonResponse(response, status=200 if response["success"] else 500)
            else:
                return JsonResponse({"success": False, "message": "订单状态不允许评论"})
        return JsonResponse({"success": False, "message": "订单未找到或无法评论"})
    return JsonResponse({"success": False, "message": "无效请求"})


@login_required
def user_profile_view(request):
    """
    用户个人信息视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染用户个人信息页面
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user_profile = UserProfile.objects(user_id=user_id).first()

    if request.method == 'POST':
        user_profile.name = request.POST.get('name')
        user_profile.address = request.POST.get('address')
        user_profile.phone = request.POST.get('phone')
        user_profile.save()
        messages.success(request, "个人信息已更新")

    return render(request, 'user_profile.html', {'user_profile': user_profile})
