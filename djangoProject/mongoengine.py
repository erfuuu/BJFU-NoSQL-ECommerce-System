# mongoengine.py

from mongoengine import connect

# 连接 MongoDB 数据库
connect(
    db="commerce",  # 替换为您的 MongoDB 数据库名称
    host="mongodb://localhost:27017/commerce",  # MongoDB 主机地址
    alias="default"  # 设置为默认连接
)
