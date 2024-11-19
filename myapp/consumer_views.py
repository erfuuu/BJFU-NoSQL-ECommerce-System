from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
import json
from django.views.decorators.http import require_http_methods
from mongoengine import Q
from .models import Product, Comment, Order, UserProfile
from datetime import datetime
import uuid
from .views import login_required, create_log


# 消费者主页面
@login_required
def consumer_home_view(request):
    query = request.GET.get('query', '').strip()  # 获取搜索关键字
    products = Product.objects.all().order_by('-sales_volume')  # 默认按销量降序排列

    # 搜索功能
    if query:
        if query.isdigit():
            products = products.filter(
                Q(product_id=int(query)) |
                Q(name__icontains=query) |
                Q(tags__icontains=query)
            )
        else:
            products = products.filter(
                Q(name__icontains=query) |
                Q(tags__icontains=query)
            )

    # 分页功能
    paginator = Paginator(products, 10)  # 每页显示10个商品
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)

    return render(request, 'consumer_home.html', {'products': products_page, 'query': query})


def search_products(request):
    query = request.GET.get('query', '').strip()  # 获取搜索关键字
    all_products = Product.objects.all().order_by('-sales_volume')  # 默认按销量降序排列

    # 搜索逻辑
    if query:
        all_products = all_products.filter(
            Q(name__icontains=query) |
            Q(tags__icontains=query)
        )

    # 分页功能
    paginator = Paginator(all_products, 12)  # 每页显示12个商品
    page_number = request.GET.get('page', 1)
    products = paginator.get_page(page_number)

    return render(request, 'consumer_home.html', {
        'products': products,
        'query': query,
    })

#产品细节页面
@login_required
def product_detail_view(request, product_id):
    # 查询商品
    product = Product.objects(product_id=product_id).first()
    if not product:
        return render(request, '404.html')

    # 增加产品点击量
    product.clicks += 1
    product.save()

    # 查询评论并按时间倒序排序
    comments = Comment.objects(product_id=product_id).order_by('-timestamp')

    # 计算平均评分
    if comments:
        total_rating = sum(comment.rating for comment in comments if comment.rating)
        average_rating = round(total_rating / len(comments), 1)
    else:
        average_rating = "暂无评分"  # 无评分时的默认显示

    # 上下文
    context = {
        'product': product,
        'comments': comments,
        'average_rating': average_rating,  # 添加平均评分
        'user_is_authenticated': request.user.is_authenticated
    }

    # 记录商品浏览事件
    create_log(event_type="view_product", user_id=request.session.get('user_id'), details={"product_id": product_id})

    return render(request, 'product_detail.html', context)

#加入购物车
@login_required
def add_to_cart(request, product_id):
    if request.method == "POST":
        # 获取 session 中的 user_id
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({"success": False, "error": "用户未登录"})

        user_profile = UserProfile.objects(user_id=user_id).first()
        if not user_profile:
            return JsonResponse({"success": False, "error": "用户信息未找到"})
        order_address = user_profile.get_address()
        order_phone = user_profile.get_phone()

        # 获取商品数量
        data = json.loads(request.body)
        quantity = int(data.get("quantity", 1))

        # 查找或创建“在购物车中”的订单
        order = Order.objects.filter(user_id=user_id, status="In Cart").first()
        if not order:
            order = Order(
                order_id=str(uuid.uuid4()),
                user_id=user_id,
                product_list=[],
                status="In Cart",
                timestamp=datetime.utcnow(),
                order_address = order_address,  # 赋值 order_address
                order_phone=order_phone
            )

        # 更新商品数量或添加新商品
        product_found = False
        for item in order.product_list:
            if item["product_id"] == product_id:
                item["quantity"] += quantity
                product_found = True
                break
        if not product_found:
            order.product_list.append({"product_id": product_id, "quantity": quantity})

        # 重新计算总金额并保存订单
        order.calculate_total_amount()
        order.save()

        return JsonResponse({"success": True, "message": "商品已成功加入购物车！"})
    return JsonResponse({"success": False, "error": "无效请求"})

#立即购买
@login_required
def buy_now(request, product_id):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        data = json.loads(request.body)
        quantity = int(data.get("quantity", 1))

        user_profile = UserProfile.objects(user_id=user_id).first()
        if not user_profile:
            return JsonResponse({"success": False, "error": "用户信息未找到"})
        order_address = user_profile.get_address()
        order_phone = user_profile.get_phone()

        product = Product.objects(product_id=product_id).first()
        if not product:
            return JsonResponse({"success": False, "error": "商品未找到"})

        total_amount = product.price * quantity

        order = Order(
            order_id=str(uuid.uuid4()),
            user_id=user_id,
            product_list=[{"product_id": product_id, "quantity": quantity}],
            total_amount=total_amount,
            status="Pending",
            timestamp=datetime.utcnow(),
            order_address = order_address,  # 赋值 order_address
            order_phone = order_phone
        )
        order.save()

        # 更新商品库存和销量
        product.stock -= quantity  # 减少库存
        product.sales_volume += quantity  # 增加销量
        product.save()  # 保存更改

        # 记录订单创建事件
        create_log(event_type="create_order", user_id=user_id,
                   details={"order_id": order.order_id, "total_amount": total_amount})

        return JsonResponse({"success": True, "message": "订单已创建并等待发货！"})
    return JsonResponse({"success": False, "error": "无效请求"})

#购物车视图
@login_required
def cart_view(request):
    user_id = request.session.get('user_id')
    in_cart_orders = Order.objects(user_id=user_id, status="In Cart")
    return render(request, 'cart.html', {'in_cart_orders': in_cart_orders})

#购物车里下单
@login_required
def purchase_order(request, order_id):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        order = Order.objects(order_id=order_id, user_id=user_id,status="In Cart").first()
        if order:
            order.status = "Pending"
            order.timestamp = datetime.utcnow()
            for item in order.product_list:
                product = Product.objects(product_id=item["product_id"]).first()
                if product:
                    if product.stock >= item["quantity"]:
                        product.stock -= item["quantity"]
                        product.sales_volume += item["quantity"]
                        product.save()
                    else:
                        return JsonResponse({"success": False, "error": f"商品 {product.name} 库存不足"})
            order.save()
            print({"order_id": order.order_id, "total_amount": order.total_amount})
            create_log(event_type="create_order", user_id=user_id,
                       details={"order_id": order.order_id, "total_amount": order.total_amount})
            return JsonResponse({"success": True, "message": "订单已更新为待处理状态！"})
        return JsonResponse({"success": False, "error": "订单未找到或无法更新"})
    return JsonResponse({"success": False, "error": "无效请求"})

#购物车里删除商品
@login_required
@require_http_methods(["DELETE"])
def delete_order(request, order_id):
    user_id = request.session.get('user_id')
    order = Order.objects.filter(order_id=order_id, user_id=user_id, status="In Cart").first()

    if order:
        order.delete()
        return JsonResponse({"success": True, "message": "订单已删除"})
    else:
        return JsonResponse({"success": False, "error": "订单未找到或无法删除"}, status=404)

#订单视图
@login_required
def order_view(request):
    user_id = request.session.get('user_id')

    # 获取时间范围参数
    start_date = request.GET.get('start_date')  # 格式: YYYY-MM-DD
    end_date = request.GET.get('end_date')  # 格式: YYYY-MM-DD

    # 初始化订单查询集
    orders = Order.objects.filter(user_id=user_id, status__in=["Pending", "Shipped", "Delivered", "Completed"])

    # 按时间范围过滤
    if start_date:
        orders = orders.filter(timestamp__gte=datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        orders = orders.filter(timestamp__lte=datetime.strptime(end_date, '%Y-%m-%d'))

    return render(request, 'order.html', {'orders': orders, 'start_date': start_date, 'end_date': end_date})

# 确认收货视图
@login_required
def confirm_receipt(request, order_id):
    if request.method == "POST":
        try:
            # 获取订单对象并检查状态
            order = Order.objects.get(order_id=order_id)
            if order.status == "Delivered":
                order.status = "Completed"
                order.save()
                return JsonResponse({"success": True, "message": "订单已确认收货"})
            else:
                return JsonResponse({"success": False, "message": "订单状态不允许确认收货"})
        except Order.DoesNotExist:
            return JsonResponse({"success": False, "message": "订单未找到"}, status=404)
        except Exception as e:
            # 捕获其他异常并返回错误信息
            return JsonResponse({"success": False, "message": str(e)}, status=500)
    return JsonResponse({"success": False, "message": "无效请求"}, status=400)


# 评论订单商品视图
@login_required
def add_comment_for_order(request, order_id, product_id):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        order = Order.objects.filter(order_id=order_id, user_id=user_id).first()

        if order:
            if order.status == "Completed":
                content = request.POST.get("content")
                rating = float(request.POST.get("rating"))

                # 调用 Comment 的静态方法插入评论
                response = Comment.add_comment(
                    product_id=product_id,
                    user_id=user_id,
                    content=content,
                    rating=rating
                )

                return JsonResponse(response, status=200 if response["success"] else 500)
            else:
                return JsonResponse({"success": False, "message": "订单状态不允许评论"})
        return JsonResponse({"success": False, "message": "订单未找到或无法评论"})
    return JsonResponse({"success": False, "message": "无效请求"})

#个人信息视图
@login_required
def user_profile_view(request):
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