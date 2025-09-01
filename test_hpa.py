# -*- coding: utf-8 -*-
import requests
import time
import threading
import json
import random
import string

# HPA压测配置
BASE_URL = "http://localhost:30009"  # 默认NodePort地址
TEST_DURATION = 300  # 测试持续时间（秒），设置为5分钟以便观察HPA效果
MAX_WORKERS = 50    # 最大并发线程数，设置较高以产生足够负载
REQUESTS_PER_SECOND = 20  # 每秒请求数，设置较高以产生足够负载

# 测试结果统计
stats = {
    'total_requests': 0,
    'successful_requests': 0,
    'failed_requests': 0,
    'response_times': [],
    'status_codes': {}
}

# 打开日志文件
log_file = open("hpa_test_results.log", "w")

def log_print(message):
    """同时打印到屏幕和写入日志文件"""
    print(message)
    log_file.write(message + "\n")
    log_file.flush()  # 确保立即写入文件

def generate_random_email():
    """生成随机邮箱地址"""
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(8)) + '@test.com'

def generate_random_username():
    """生成随机用户名"""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))

def register_user():
    """注册新用户 - 会产生数据库写入负载"""
    email = generate_random_email()
    username = generate_random_username()
    
    payload = {
        "username": username,
        "password": "Test123!",
        "password_repeat": "Test123!",
        "email": email,
        "captcha": "123456"
    }
    
    try:
        start_time = time.time()
        response = requests.post("{}/auth/register/".format(BASE_URL), 
                                json=payload, 
                                headers={'Content-Type': 'application/json'},
                                timeout=30)  # 增加超时时间
        end_time = time.time()
        
        stats['total_requests'] += 1
        stats['response_times'].append(end_time - start_time)
        
        if response.status_code in stats['status_codes']:
            stats['status_codes'][response.status_code] += 1
        else:
            stats['status_codes'][response.status_code] = 1
            
        if 200 <= response.status_code < 300:
            stats['successful_requests'] += 1
            return response.json()
        else:
            stats['failed_requests'] += 1
            return None
    except Exception as e:
        stats['total_requests'] += 1
        stats['failed_requests'] += 1
        return None

def get_user_info():
    """获取用户信息 - 会产生数据库读取负载"""
    try:
        # 使用一个固定的UUID进行测试
        start_time = time.time()
        response = requests.get("{}/user/00000000-0000-0000-0000-000000000000/".format(BASE_URL), 
                               timeout=30)  # 增加超时时间
        end_time = time.time()
        
        stats['total_requests'] += 1
        stats['response_times'].append(end_time - start_time)
        
        if response.status_code in stats['status_codes']:
            stats['status_codes'][response.status_code] += 1
        else:
            stats['status_codes'][response.status_code] = 1
            
        if 200 <= response.status_code < 300 or response.status_code in [401, 403, 404]:
            stats['successful_requests'] += 1
            return True
        else:
            stats['failed_requests'] += 1
            return False
    except Exception as e:
        stats['total_requests'] += 1
        stats['failed_requests'] += 1
        return False

def health_check():
    """健康检查 - 轻量级请求"""
    try:
        start_time = time.time()
        response = requests.get("{}/user/me/".format(BASE_URL), timeout=30)
        end_time = time.time()
        
        stats['total_requests'] += 1
        stats['response_times'].append(end_time - start_time)
        
        if response.status_code in stats['status_codes']:
            stats['status_codes'][response.status_code] += 1
        else:
            stats['status_codes'][response.status_code] = 1
            
        if 200 <= response.status_code < 300 or response.status_code in [401, 403]:
            stats['successful_requests'] += 1
            return True
        else:
            stats['failed_requests'] += 1
            return False
    except Exception as e:
        stats['total_requests'] += 1
        stats['failed_requests'] += 1
        return False

def heavy_operation():
    """模拟重操作 - 多次调用API以增加负载"""
    # 执行多个操作以增加负载
    for _ in range(5):
        health_check()
        time.sleep(0.1)
        
    for _ in range(3):
        get_user_info()
        time.sleep(0.1)
        
    # 注册用户操作（成本较高）
    register_user()

def worker(stop_event):
    """工作线程函数"""
    while not stop_event.is_set():
        # 执行重操作以产生更多负载
        heavy_operation()
        
        # 控制请求频率
        time.sleep(1.0 / (REQUESTS_PER_SECOND / 10))

def print_stats():
    """打印统计信息"""
    log_print("\n=== HPA压力测试结果 ===")
    log_print("总请求数: {}".format(stats['total_requests']))
    log_print("成功请求数: {}".format(stats['successful_requests']))
    log_print("失败请求数: {}".format(stats['failed_requests']))
    log_print("成功率: {:.2f}%".format(stats['successful_requests']/float(stats['total_requests'])*100) if stats['total_requests'] > 0 else "成功率: 0%")
    
    if stats['response_times']:
        avg_response_time = sum(stats['response_times']) / len(stats['response_times'])
        min_response_time = min(stats['response_times'])
        max_response_time = max(stats['response_times'])
        log_print("平均响应时间: {:.3f} 秒".format(avg_response_time))
        log_print("最小响应时间: {:.3f} 秒".format(min_response_time))
        log_print("最大响应时间: {:.3f} 秒".format(max_response_time))
    
    log_print("状态码分布:")
    for status_code, count in stats['status_codes'].items():
        log_print("  {}: {}".format(status_code, count))
    
    log_print("\n=== HPA观察指南 ===")
    log_print("请在另一个终端中运行以下命令观察HPA效果:")
    log_print("  kubectl get hpa -w")
    log_print("  kubectl get pods -w")
    log_print("  kubectl top pods")

if __name__ == "__main__":
    import sys
    
    try:
        # 允许通过命令行参数指定基础URL
        if len(sys.argv) > 1:
            BASE_URL = sys.argv[1]
        
        log_print("开始HPA压力测试: {}".format(BASE_URL))
        log_print("测试持续时间: {} 秒".format(TEST_DURATION))
        log_print("并发线程数: {}".format(MAX_WORKERS))
        log_print("每秒请求数: {}".format(REQUESTS_PER_SECOND))
        log_print("\n请在另一个终端中运行以下命令观察HPA效果:")
        log_print("  kubectl get hpa -w")
        log_print("  kubectl get pods -w")
        log_print("  kubectl top pods")
        
        # 创建停止事件
        stop_event = threading.Event()
        
        # 创建线程池
        threads = []
        for i in range(MAX_WORKERS):
            t = threading.Thread(target=worker, args=(stop_event,))
            threads.append(t)
            t.start()
            
        # 运行指定时间后停止
        time.sleep(TEST_DURATION)
        stop_event.set()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 打印统计结果
        print_stats()
    finally:
        # 关闭日志文件
        log_file.close()