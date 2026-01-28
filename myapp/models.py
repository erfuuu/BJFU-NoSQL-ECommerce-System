from datetime import datetime
from decimal import Decimal

from mongoengine import Document, StringField, IntField, DecimalField, URLField, FloatField, DateTimeField, ListField, \
    DictField, SequenceField, ValidationError


USER_TYPE_CONSUMER = "consumer"
USER_TYPE_BUSINESS = "business"
USER_TYPE_MANAGER = "manager"

USER_TYPE_CHOICES = [USER_TYPE_CONSUMER, USER_TYPE_BUSINESS, USER_TYPE_MANAGER]

ORDER_STATUS_IN_CART = "In Cart"
ORDER_STATUS_PENDING = "Pending"
ORDER_STATUS_SHIPPED = "Shipped"
ORDER_STATUS_DELIVERED = "Delivered"
ORDER_STATUS_COMPLETED = "Completed"

ORDER_STATUS_CHOICES = [ORDER_STATUS_IN_CART, ORDER_STATUS_PENDING, ORDER_STATUS_SHIPPED, ORDER_STATUS_DELIVERED, ORDER_STATUS_COMPLETED]

DEFAULT_RATING_MIN = 0.0
DEFAULT_RATING_MAX = 5.0


class UserProfile(Document):
    user_id = StringField(required=True, unique=True, max_length=100)
    name = StringField(max_length=100)
    password = StringField(required=True, max_length=100)
    address = StringField(max_length=255)
    phone = StringField(max_length=20)
    user_type = StringField(choices=USER_TYPE_CHOICES, default=USER_TYPE_CONSUMER)

    meta = {
        'collection': 'user_info'
    }

    def __str__(self):
        return f"UserProfile for {self.user_id}"

    def get_delivery_address(self):
        return self.address

    def get_contact_phone(self):
        return self.phone


class Product(Document):
    product_id = IntField(required=True, unique=True)
    product_name = StringField(required=True, max_length=255)
    product_description = StringField()
    product_price = DecimalField(precision=2)
    product_stock = IntField()
    product_sales_volume = IntField()
    product_image_url = URLField()
    product_tags = ListField(StringField())
    product_click_count = IntField(default=0)

    meta = {
        'collection': 'products'
    }

    def __str__(self):
        return self.product_name


class Comment(Document):
    comment_id = SequenceField(unique=True)
    product_id = IntField(required=True)
    user_id = StringField(required=True, max_length=100)
    comment_content = StringField(max_length=500)
    comment_rating = FloatField(min_value=DEFAULT_RATING_MIN, max_value=DEFAULT_RATING_MAX)
    comment_timestamp = DateTimeField(default=datetime.utcnow)
    merchant_reply = StringField()
    comment_like_count = IntField(default=0)

    meta = {
        'collection': 'comments'
    }

    def __str__(self):
        return f"{self.user_id} - {self.comment_content[:20]}"

    @staticmethod
    def create_new_comment(product_id, user_id, content, rating):
        try:
            new_comment = Comment(
                product_id=product_id,
                user_id=user_id,
                comment_content=content,
                comment_rating=rating,
                comment_timestamp=datetime.utcnow(),
                merchant_reply=""
            )
            new_comment.save()
            return {"success": True, "message": "评论已提交！"}
        except ValidationError as error:
            return {"success": False, "message": f"评论保存失败: {str(error)}"}

    def increment_like_count(self):
        self.comment_like_count += 1
        self.save()
        return {"success": True, "message": "点赞成功！"}

    def decrement_like_count(self):
        if self.comment_like_count > 0:
            self.comment_like_count -= 1
            self.save()
            return {"success": True, "message": "取消点赞成功！"}
        return {"success": False, "message": "点赞数不能小于 0！"}


class Order(Document):
    order_id = StringField(required=True, unique=True)
    user_id = StringField(required=True, max_length=100)
    order_items = ListField(DictField())
    order_total_amount = DecimalField(precision=2)
    order_status = StringField(choices=ORDER_STATUS_CHOICES, default=ORDER_STATUS_IN_CART)
    order_timestamp = DateTimeField(default=datetime.utcnow)
    delivery_address = StringField(max_length=255)
    contact_phone = StringField(max_length=20)
    return_reason = StringField(max_length=500)
    refund_reason = StringField(max_length=500)
    refund_timestamp = DateTimeField()

    meta = {
        'collection': 'orders'
    }

    def __str__(self):
        return f"Order {self.order_id} by {self.user_id}"

    def calculate_order_total(self):
        total = Decimal('0.00')
        for order_item in self.order_items:
            product = Product.objects(product_id=order_item["product_id"]).first()
            if product:
                total += product.product_price * int(order_item["quantity"])
        self.order_total_amount = total


class Log(Document):
    log_event_type = StringField(required=True, max_length=100)
    log_timestamp = DateTimeField(default=datetime.utcnow)
    log_user_id = StringField(max_length=100, required=False)
    log_details = DictField(required=True)

    meta = {
        'collection': 'logs'
    }

    def __str__(self):
        return f"{self.log_event_type} - {self.log_timestamp}"
