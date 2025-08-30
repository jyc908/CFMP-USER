# nacos_heartbeat.py
import nacos
import socket
import threading
import time
import os
import sys
import random

SERVER_ADDRESSES = "123.57.145.79:8848"
NAMESPACE = "public"  # 或者你的 namespace ID
USERNAME = "nacos"
PASSWORD = "no5groupnacos"
SERVICE_NAME = "UserService"


def get_port_from_args(default=8000):
    for arg in sys.argv:
        if ":" in arg:
            try:
                return int(arg.split(":")[1])
            except ValueError:
                pass
    return default

PORT = os.getenv("NODE_PORT", 30009)

client = nacos.NacosClient(
    SERVER_ADDRESSES,
    namespace=NAMESPACE,
    username=USERNAME,
    password=PASSWORD
)


IP = os.getenv("NODE_IP", random.randint(30000,32767))


def register_service():
    # 注册实例
    client.add_naming_instance(
        service_name=SERVICE_NAME,
        ip=IP,
        port=PORT,
        cluster_name="DEFAULT"
    )
    print(f"已注册到 Nacos: {SERVICE_NAME} {IP}:{PORT}")

def send_heartbeat():
    while True:
        try:
            client.send_heartbeat(
                service_name=SERVICE_NAME,
                ip=IP,
                port=PORT,
                cluster_name="DEFAULT"
            )
            # 心跳周期建议小于 Nacos 配置的超时（默认 5s-10s 一次）
            time.sleep(5)
        except Exception as e:
            print(f"心跳发送失败: {e}")
            time.sleep(5)

def start_nacos_heartbeat():
    register_service()
    # 开一个后台线程发心跳
    t = threading.Thread(target=send_heartbeat, daemon=True)
    t.start()
