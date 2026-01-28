import requests
from bs4 import BeautifulSoup

# 创建一个会话
session = requests.Session()

# 首先获取登录页面，获取CSRF令牌
login_url = 'http://127.0.0.1:8000/login/'
response = session.get(login_url)

# 解析HTML，提取CSRF令牌
soup = BeautifulSoup(response.content, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']

# 准备登录数据
data = {
    'user_id': 'testuser',
    'password': 'testpass',
    'csrfmiddlewaretoken': csrf_token
}

# 发送登录请求
headers = {
    'Referer': login_url,
    'X-CSRFToken': csrf_token
}
response = session.post(login_url, data=data, headers=headers)

# 检查登录是否成功
print('Login Status Code:', response.status_code)
print('Login URL:', response.url)

# 尝试访问主页
home_url = 'http://127.0.0.1:8000/home/'
response = session.get(home_url)

print('\nHome Status Code:', response.status_code)
print('Home URL:', response.url)

# 检查是否成功进入主页
if 'consumer_home' in response.url or response.status_code == 200:
    print('\nSUCCESS: Login and access to home page successful!')
else:
    print('\nFAILURE: Login or access to home page failed!')
    print('Response content:', response.content[:500])  # 打印部分响应内容
