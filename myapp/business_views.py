import random
from decimal import Decimal

from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from mongoengine import DoesNotExist

from .models import Product, Comment, Order, UserProfile
from .views import login_required


BUSINESS_PAGINATION_PAGE_SIZE = 10
PRODUCT_ID_MIN = 1
PRODUCT_ID_MAX = 99999999


def get_business_user_id(request):
    """
    从 session 中获取商家用户 ID
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        str: 商家用户 ID，如果未登录则返回 None
    """
    return request.session.get('business_user_id')


@login_required
def business_home_view(request):
    """
    商家主页视图，显示商品列表
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染商家主页
    """
    products = Product.objects.all().order_by('-product_sales_volume')
    paginator = Paginator(products, BUSINESS_PAGINATION_PAGE_SIZE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'business_home.html', {'products': page_obj})


@login_required
def business_product_detail_view(request, product_id):
    """
    商家商品详情页视图
    
    Args:
        request: Django HttpRequest 对象
        product_id (int): 商品 ID
    
    Returns:
        HttpResponse: 渲染商家商品详情页或返回 JSON 错误响应
    """
    product = Product.objects(product_id=product_id).first()
    if not product:
        return JsonResponse({"error": "商品未找到"}, status=404)

    comments = Comment.objects(product_id=product_id).order_by('-comment_timestamp')

    if request.method == "POST":
        comment_id = request.POST.get("comment_id")
        reply_content = request.POST.get("reply")

        comment = Comment.objects(comment_id=comment_id).first()
        if comment and reply_content:
            comment.merchant_reply = reply_content
            comment.save()
            return redirect('business_product_detail', product_id=product_id)

    return render(request, 'business_product_detail.html', {'product': product, 'comments': comments})


@login_required
def add_product_view(request):
    """
    添加商品视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染添加商品页面或重定向到商家主页
    """
    if request.method == 'POST':
        product_name = request.POST.get('name')
        product_price = request.POST.get('price')
        product_stock = request.POST.get('stock')
        product_description = request.POST.get('description')
        product_tags = request.POST.get('tags')
        product_image_url = request.POST.get('image_url')

        try:
            product_price = Decimal(product_price)
            product_stock = int(product_stock)
        except ValueError:
            messages.error(request, "价格或库存输入无效，请重新输入")
            return redirect('add_product')

        tags_list = [tag.strip() for tag in product_tags.split(",") if tag.strip()]

        product_id = random.randint(PRODUCT_ID_MIN, PRODUCT_ID_MAX)

        new_product = Product(
            product_id=product_id,
            product_name=product_name,
            product_price=product_price,
            product_stock=product_stock,
            product_description=product_description,
            product_sales_volume=0,
            product_tags=tags_list,
            product_image_url=product_image_url
        )
        new_product.save()

        messages.success(request, "商品已成功添加！")
        return redirect('business_home')

    return render(request, 'business_add_product.html')


@login_required
def update_product_view(request):
    """
    更新商品视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染更新商品页面或返回 JSON 响应
    """
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        product_id = request.GET.get('product_id')
        product = Product.objects.filter(product_id=product_id).first()

        if product:
            return JsonResponse({
                'success': True,
                'data': {
                    'product_id': product.product_id,
                    'name': product.product_name,
                    'description': product.product_description,
                    'price': str(product.product_price),
                    'stock': product.product_stock,
                    'image_url': product.product_image_url,
                    'tags': ', '.join(product.product_tags),
                }
            })

        return JsonResponse({'success': False, 'message': '商品未找到'})

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        product = Product.objects.filter(product_id=product_id).first()

        if product:
            product.product_name = request.POST.get('name')
            product.product_description = request.POST.get('description')
            try:
                product.product_price = Decimal(request.POST.get('price'))
                product.product_stock = int(request.POST.get('stock'))
            except (ValueError, TypeError):
                messages.error(request, f"价格或库存输入无效：商品 {product.product_name}")
                return redirect('update_product')

            product.product_image_url = request.POST.get('image_url')
            tags = request.POST.get('tags')
            product.product_tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
            product.save()

            messages.success(request, f"商品 '{product.product_name}' 信息已更新")
            return redirect('update_product')

    products = Product.objects.all()
    return render(request, 'business_update_product.html', {'products': products})


@login_required
def delete_product_view(request):
    """
    删除商品视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染删除商品页面
    """
    products = Product.objects.all()

    paginator = Paginator(products, BUSINESS_PAGINATION_PAGE_SIZE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'business_delete_product.html', {'page_obj': page_obj})


@login_required
def delete_single_product_view(request, product_id):
    """
    删除单个商品
    
    Args:
        request: Django HttpRequest 对象
        product_id (int): 商品 ID
    
    Returns:
        HttpResponse: 重定向到删除商品页面
    """
    if request.method == 'POST':
        try:
            product = Product.objects.get(product_id=product_id)
            product.delete()
        except DoesNotExist:
            raise Http404("Product not found")
    return redirect(reverse('delete_product'))


@login_required
def business_orders_view(request):
    """
    商家订单视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染商家订单页面
    """
    orders = Order.objects.all()
    return render(request, 'business_orders.html', {'orders': orders})


@login_required
def ship_order_view(request, order_id):
    """
    发货视图
    
    Args:
        request: Django HttpRequest 对象
        order_id (str): 订单 ID
    
    Returns:
        HttpResponse: 重定向到订单页面
    """
    if request.method == 'POST':
        try:
            order = Order.objects.get(order_id=order_id)
            if order.order_status == "Pending":
                order.order_status = "Shipped"
                order.save()
        except DoesNotExist:
            raise Http404("Order not found")
    return redirect('orders')


@login_required
def business_profile_view(request):
    """
    商家个人信息视图
    
    Args:
        request: Django HttpRequest 对象
    
    Returns:
        HttpResponse: 渲染商家个人信息页面
    """
    user_id = get_business_user_id(request)
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
