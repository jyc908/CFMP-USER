from config.nacos_heartbeat import client
import random
import httpx


def call_service(service_name, target_path, payload):
    """
    调用指定的服务接口
    
    Args:
        service_name (str): 服务名称
        target_path (str): 目标接口路径
        payload (dict): 请求参数字典
        
    Returns:
        dict: 包含调用结果的字典
              成功时返回目标服务的响应数据
              失败时返回错误信息
    """
    # 验证必需的参数
    if not service_name or not target_path or not payload:
        return {
            "error": "Missing required parameters: service_name, target_path, and payload are required.",
            "success": False
        }

    try:
        instances = client.list_naming_instance(service_name=service_name)
    except Exception as e:
        return {
            "error": f"Failed to get service instances: {str(e)}",
            "success": False
        }

    # 筛选健康实例
    healthy_instances = [
        instance for instance in instances.get('hosts', [])
        if instance.get('healthy', False)
    ]

    if not healthy_instances:
        return {
            "error": "No healthy instances found.",
            "success": False
        }

    # 随机选择一个健康实例
    target = random.choice(healthy_instances)

    # 构建目标URL
    ip = target.get('ip', '')
    port = target.get('port', '')
    if not ip or not port:
        return {
            "error": "Selected instance missing IP or port",
            "success": False
        }

    url = f"http://{ip}:{port}/{target_path.lstrip('/')}"

    # 发起HTTP请求
    try:
        response = httpx.get(url, params=payload, timeout=30)
        response.raise_for_status()
        return {
            "data": response.json(),
            "success": True
        }
    except httpx.RequestError as e:
        return {
            "error": f"Request failed: {str(e)}",
            "success": False
        }
    except httpx.HTTPStatusError as e:
        return {
            "error": f"HTTP error {e.response.status_code}: {e.response.text}",
            "success": False
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "success": False
        }