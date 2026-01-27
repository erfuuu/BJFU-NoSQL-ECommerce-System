import random
from decimal import Decimal
from datetime import datetime

from django.core.paginator import Paginator
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from mongoengine import DoesNotExist
from .models import Product, Comment, Order, UserProfile
from .views import login_required

#商家主页面
@login_required
def business_home(request):
    products = Product.objects.all().order_by('-sales_volume')  # 默认按销量排序
    paginator = Paginator(products, 10)  # 每页10个商品
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'business_home.html', {'products': page_obj})

#产品细节页面
@login_required
def business_product_detail(request, product_id):
    product = Product.objects(product_id=product_id).first()
    if not product:
        return JsonResponse({"error": "商品未找到"}, status=404)

    # 查询评论并按时间倒序排序
    comments = Comment.objects(product_id=product_id).order_by('-timestamp')

    # 处理商家回复
    if request.method == "POST":
        comment_id = request.POST.get("comment_id")
        reply_content = request.POST.get("reply")

        comment = Comment.objects(comment_id=comment_id).first()
        if comment and reply_content:
            comment.reply = reply_content
            comment.save()
            return redirect('business_product_detail', product_id=product_id)

    return render(request, 'business_product_detail.html', {'product': product, 'comments': comments})

#添加商品
@login_required
def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        description = request.POST.get('description')
        tags = request.POST.get('tags')
        image_url = request.POST.get('image_url')  # 获取用户输入的图片 URL
        image_file = request.FILES.get('image_file')  # 获取上传的图片文件

        # 转换 price 和 stock 字段为正确类型
        try:
            price = Decimal(price)
            stock = int(stock)
        except ValueError:
            messages.error(request, "价格或库存输入无效，请重新输入")
            return redirect('add_product')

        # 处理 tags 字段
        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # 使用较小范围的整数生成唯一的 product_id
        product_id = random.randint(1, 99999999)  # 确保 product_id 在 Int32 范围内

        # 创建新的商品
        product = Product(
            product_id=product_id,
            name=name,
            price=price,
            stock=stock,
            description=description,
            sales_volume=0,
            tags=tags_list
        )

        # 只在有URL时才设置image_url
        if image_url and image_url.strip():
            product.image_url = image_url

        # 如果上传了图片文件，保存图片数据
        if image_file:
            product.image_data = image_file.read()
            product.image_content_type = image_file.content_type

        product.save()

        messages.success(request, "商品已成功添加！")
        return redirect('business_home')

    return render(request, 'business_add_product.html')

#更新商品

@login_required
def update_product(request):
    if request.method == 'GET' and request.is_ajax():
        product_id = request.GET.get('product_id')
        product = Product.objects.filter(product_id=product_id).first()

        if product:
            return JsonResponse({
                'success': True,
                'data': {
                    'product_id': product.product_id,
                    'name': product.name,
                    'description': product.description,
                    'price': str(product.price),
                    'stock': product.stock,
                    'image_url': product.image_url,
                    'tags': ', '.join(product.tags),
                }
            })

        return JsonResponse({'success': False, 'message': '商品未找到'})

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        product = Product.objects.filter(product_id=product_id).first()

        if product:
            # 更新特定商品信息
            product.name = request.POST.get('name')
            product.description = request.POST.get('description')
            try:
                product.price = Decimal(request.POST.get('price'))
                product.stock = int(request.POST.get('stock'))
            except (ValueError, TypeError):
                messages.error(request, f"价格或库存输入无效：商品 {product.name}")
                return redirect('update_product')

            product.image_url = request.POST.get('image_url')
            tags = request.POST.get('tags')
            product.tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
            product.save()

            messages.success(request, f"商品 '{product.name}' 信息已更新")
            return redirect('update_product')

    products = Product.objects.all()
    return render(request, 'business_update_product.html', {'products': products})


#下架商品
@login_required
def delete_product(request):
    products = Product.objects.all()

    # 分页逻辑
    paginator = Paginator(products, 10)  # 每页显示10个商品
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'business_delete_product.html', {'page_obj': page_obj})

#下架按钮
@login_required
def delete_single_product(request, product_id):
    if request.method == 'POST':
        try:
            product = Product.objects.get(product_id=product_id)
            product.delete()
        except DoesNotExist:
            raise Http404("Product not found")
    return redirect(reverse('delete_product'))

#订单视图
@login_required
def orders(request):
    orders = Order.objects.all()  # 获取所有订单
    return render(request, 'business_orders.html', {'orders': orders})

#发货按钮
@login_required
def ship_order(request, order_id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(order_id=order_id)
            if order.status == "Pending":
                order.status = "Shipped"
                order.save()
        except DoesNotExist:
            raise Http404("Order not found")
    return redirect('orders')

# 审批退款
@login_required
def approve_refund(request, order_id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(order_id=order_id)
            if order.status == "Refund Pending":
                order.status = "Refunded"
                order.refund_timestamp = datetime.utcnow()
                
                # 恢复库存和销量
                for item in order.product_list:
                    product = Product.objects(product_id=item["product_id"]).first()
                    if product:
                        product.stock += item["quantity"]
                        product.sales_volume -= item["quantity"]
                        product.save()
                
                order.save()
                messages.success(request, "退款已批准，库存已恢复")
            else:
                messages.error(request, "订单状态不允许审批退款")
        except DoesNotExist:
            raise Http404("Order not found")
    return redirect('orders')

# 拒绝退款
@login_required
def reject_refund(request, order_id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(order_id=order_id)
            if order.status == "Refund Pending":
                order.status = "Pending"
                order.save()
                messages.success(request, "退款申请已拒绝，订单恢复为待发货状态")
            else:
                messages.error(request, "订单状态不允许拒绝退款")
        except DoesNotExist:
            raise Http404("Order not found")
    return redirect('orders')

# 审批退货
@login_required
def approve_return(request, order_id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(order_id=order_id)
            if order.status == "Return Pending":
                order.status = "Returned"
                order.return_timestamp = datetime.utcnow()
                
                # 恢复库存和销量
                for item in order.product_list:
                    product = Product.objects(product_id=item["product_id"]).first()
                    if product:
                        product.stock += item["quantity"]
                        product.sales_volume -= item["quantity"]
                        product.save()
                
                order.save()
                messages.success(request, "退货已批准，库存已恢复")
            else:
                messages.error(request, "订单状态不允许审批退货")
        except DoesNotExist:
            raise Http404("Order not found")
    return redirect('orders')

# 拒绝退货
@login_required
def reject_return(request, order_id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(order_id=order_id)
            if order.status == "Return Pending":
                order.status = "Delivered"
                order.save()
                messages.success(request, "退货申请已拒绝，订单恢复为已送达状态")
            else:
                messages.error(request, "订单状态不允许拒绝退货")
        except DoesNotExist:
            raise Http404("Order not found")
    return redirect('orders')

#商家个人信息
@login_required
def business_profile(request):
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

    return render(request, 'business_profile.html', {'user_profile': user_profile})

# 显示商品图片
@login_required
def product_image_view(request, product_id):
    product = Product.objects(product_id=product_id).first()
    if not product or not product.image_data:
        return HttpResponse(status=404)
    
    return HttpResponse(product.image_data, content_type=product.image_content_type)

# 数据分析工作台
@login_required
def analytics_dashboard(request):
    from datetime import timedelta
    from collections import defaultdict
    
    # 获取所有商品
    products = Product.objects.all()
    
    # 获取所有订单
    orders = Order.objects.all()
    
    # 计算总销售额
    total_sales = sum(order.total_amount for order in orders if order.status in ["Completed", "Delivered", "Shipped", "Pending"])
    
    # 计算总订单数
    total_orders = orders.count()
    
    # 商品销量排行（前10）
    top_sales_products = sorted(products, key=lambda x: x.sales_volume, reverse=True)[:10]
    
    # 商品点击量排行（前10）
    top_clicks_products = sorted(products, key=lambda x: x.clicks, reverse=True)[:10]
    
    # 订单状态分布
    order_status_counts = {}
    for status in ["In Cart", "Pending", "Shipped", "Delivered", "Completed", "Refunded", "Returned"]:
        order_status_counts[status] = orders.filter(status=status).count()
    
    # 计算订单状态百分比
    order_status_percentages = {}
    for status, count in order_status_counts.items():
        if total_orders > 0:
            order_status_percentages[status] = round(count / total_orders * 100, 1)
        else:
            order_status_percentages[status] = 0
    
    # 近期订单趋势（最近7天）
    recent_orders = defaultdict(int)
    for i in range(7):
        date = datetime.utcnow() - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        recent_orders[date_str] = 0
    
    for order in orders:
        date_str = order.timestamp.strftime('%Y-%m-%d')
        if date_str in recent_orders:
            recent_orders[date_str] += 1
    
    # 按日期排序
    recent_orders = dict(sorted(recent_orders.items(), reverse=True))
    
    # 计算最大订单数（用于图表比例）
    max_orders = max(recent_orders.values()) if recent_orders else 0
    
    # 计算每个日期的百分比
    recent_orders_percentages = {}
    for date, count in recent_orders.items():
        if max_orders > 0:
            recent_orders_percentages[date] = round(count / max_orders * 100, 1)
        else:
            recent_orders_percentages[date] = 0
    
    # 商品分类统计
    category_stats = defaultdict(int)
    for product in products:
        for tag in product.tags:
            category_stats[tag] += product.sales_volume
    
    # 按销量排序分类
    category_stats = dict(sorted(category_stats.items(), key=lambda x: x[1], reverse=True))
    
    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'top_sales_products': top_sales_products,
        'top_clicks_products': top_clicks_products,
        'order_status_counts': order_status_counts,
        'order_status_percentages': order_status_percentages,
        'recent_orders': recent_orders,
        'recent_orders_percentages': recent_orders_percentages,
        'category_stats': category_stats,
    }
    
    return render(request, 'business_analytics.html', context)
