from datetime import datetime
from decimal import Decimal

from mongoengine import Document, StringField, IntField, DecimalField, URLField, FloatField, DateTimeField, ListField, \
    DictField, SequenceField, ValidationError


class UserProfile(Document):
    user_id = StringField(required=True, unique=True, max_length=100)  # 用户ID
    name = StringField(max_length=100)  # 用户名
    password = StringField(required=True, max_length=100)  # 密码
    address = StringField(max_length=255)  # 地址
    phone = StringField(max_length=20)  # 电话
    type = StringField(choices=["consumer", "business", "manager"], default="consumer")  # 用户类型

    meta = {
        'collection': 'user_info'  # 确保集合名称与 MongoDB 中的名称一致
    }

    def __str__(self):
        return f"UserProfile for {self.user_id}"

    def get_address(self):
        return self.address
    def get_phone(self):
        return self.phone

class Product(Document):
    product_id = IntField(required=True, unique=True)
    name = StringField(required=True, max_length=255)
    description = StringField()
    price = DecimalField(precision=2)
    stock = IntField()
    sales_volume = IntField()
    image_url = URLField()
    tags = ListField(StringField())  # 添加 tags 字段，用于存储商品标签
    clicks = IntField(default=0)  # 新增字段 clicks，用于记录产品点击量

    meta = {
        'collection': 'products'  # 确保集合名称与 MongoDB 中的名称一致
    }

    def __str__(self):
        return self.name


class Comment(Document):
    comment_id = SequenceField(unique=True)  # 自动生成自增整数 ID
    product_id = IntField(required=True)
    user_id = StringField(required=True, max_length=100)
    content = StringField(max_length=500)
    rating = FloatField(min_value=0.0, max_value=5.0)
    timestamp = DateTimeField(default=datetime.utcnow)
    reply = StringField()  # 商家回复字段
    likes = IntField(default=0)  # 新增字段：记录点赞数，默认为 0

    meta = {
        'collection': 'comments'  # 确保数据存储在 `comments` 集合中
    }

    def __str__(self):
        return f"{self.user_id} - {self.content[:20]}"

    @staticmethod
    def add_comment(product_id, user_id, content, rating):
        try:
            # 在创建评论时将 reply 设置为空
            comment = Comment(
                product_id=product_id,
                user_id=user_id,
                content=content,
                rating=rating,
                timestamp=datetime.utcnow(),
                reply="",  # 初始化 reply 字段为空
            )
            comment.save()
            return {"success": True, "message": "评论已提交！"}
        except ValidationError as e:
            return {"success": False, "message": f"评论保存失败: {str(e)}"}

    def add_like(self):
        """
        增加评论的点赞数。
        """
        self.likes += 1
        self.save()
        return {"success": True, "message": "点赞成功！"}

    def remove_like(self):
        """
        减少评论的点赞数（不低于 0）。
        """
        if self.likes > 0:
            self.likes -= 1
            self.save()
            return {"success": True, "message": "取消点赞成功！"}
        return {"success": False, "message": "点赞数不能小于 0！"}
class Order(Document):
    order_id = StringField(required=True, unique=True)
    user_id = StringField(required=True, max_length=100)
    product_list = ListField(DictField())  # 示例: [{"product_id": 1, "quantity": 2}]
    total_amount = DecimalField(precision=2)
    status = StringField(choices=["In Cart", "Pending", "Shipped", "Delivered", "Completed"], default="In Cart")
    timestamp = DateTimeField(default=datetime.utcnow)
    order_address = StringField(max_length=255)  # 确保字段定义无误
    order_phone = StringField(max_length=20)
    return_reason = StringField(max_length=500)  # 退货原因字段
    refund_reason = StringField(max_length=500)  # 退款原因字段
    refund_timestamp = DateTimeField()  # 退款时间字段

    meta = {
        'collection': 'orders'  # 确保集合名称与 MongoDB 中的名称一致
    }

    def __str__(self):
        return f"Order {self.order_id} by {self.user_id}"

    def calculate_total_amount(self):
        total = Decimal('0.00')
        for item in self.product_list:
            product = Product.objects(product_id=item["product_id"]).first()
            if product:
                print(f"Product ID: {product.product_id}, Price: {product.price}, Quantity: {item['quantity']}")
                print(f"Price Type: {type(product.price)}, Quantity Type: {type(item['quantity'])}")
                # 将 item["quantity"] 转换为整数
                total += product.price * int(item["quantity"])
        self.total_amount = total

class Log(Document):
    event_type = StringField(required=True, max_length=100)  # 事件类型 (如 "login", "view_product", "create_order" 等)
    timestamp = DateTimeField(default=datetime.utcnow)       # 事件发生时间
    user_id = StringField(max_length=100, required=False)    # 触发事件的用户ID (如果适用)
    details = DictField(required=True)                       # 事件详情，包含事件的具体信息

    meta = {
        'collection': 'logs'  # 存储在 MongoDB 中的集合名称
    }

    def __str__(self):
        return f"{self.event_type} - {self.timestamp}"