import random
from decimal import Decimal
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from mongoengine import DoesNotExist
from .models import Product, Comment, Order, UserProfile
from .views import login_required


#商家主页面
@login_required
def business_home(request):
    products = Product.objects.all()  # 获取所有商品
    return render(request, 'business_home.html', {'products': products})

#产品细节页面
@login_required
def business_product_detail(request, product_id):
    product = Product.objects(product_id=product_id).first()
    if not product:
        return JsonResponse({"error": "商品未找到"}, status=404)

    comments = Comment.objects.filter(product_id=product_id)

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
            tags=tags_list,
            image_url=image_url  # 直接保存用户输入的图片 URL
        )
        product.save()

        messages.success(request, "商品已成功添加！")
        return redirect('business_home')

    return render(request, 'business_add_product.html')

#更新商品
@login_required
def update_product(request):
    products = Product.objects.all()  # 获取所有商品

    if request.method == 'POST':
        product_id = request.POST.get('product_id')  # 获取表单提交的商品ID
        product = Product.objects.filter(product_id=product_id).first()

        if product:
            # 更新特定商品信息
            product.name = request.POST.get(f'name_{product.product_id}')
            product.description = request.POST.get(f'description_{product.product_id}')
            try:
                product.price = Decimal(request.POST.get(f'price_{product.product_id}'))
                product.stock = int(request.POST.get(f'stock_{product.product_id}'))
            except (ValueError, TypeError):
                messages.error(request, f"价格或库存输入无效：商品 {product.name}")
                return redirect('update_product')

            product.image_url = request.POST.get(f'image_url_{product.product_id}')
            tags = request.POST.get(f'tags_{product.product_id}')
            product.tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
            product.save()  # 保存更新后的商品信息

            messages.success(request, f"商品 '{product.name}' 信息已更新")
            return redirect('update_product')

    return render(request, 'business_update_product.html', {'products': products})

#下架商品
@login_required
def delete_product(request):
    products = Product.objects.all()
    return render(request, 'business_delete_product.html', {'products': products})

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
