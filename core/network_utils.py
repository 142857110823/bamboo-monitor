"""
网络工具模块
提供网络连接检测、自动重试和安全请求功能
"""
import time
import socket
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def check_internet_connection(timeout=5):
    """
    检查网络连接状态
    
    Args:
        timeout: 超时时间（秒）
        
    Returns:
        bool: 网络连接状态
    """
    try:
        # 尝试连接到Google DNS服务器
        socket.create_connection(('8.8.8.8', 53), timeout=timeout)
        return True
    except (socket.timeout, socket.error):
        return False


def retry_on_network_error(max_retries=3, delay=2):
    """
    网络操作自动重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (socket.timeout, socket.error) as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"网络操作失败，已达到最大重试次数: {e}")
                        raise
                    logger.warning(f"网络操作失败，{delay}秒后重试 ({retries}/{max_retries}): {e}")
                    time.sleep(delay)
        return wrapper
    return decorator


def get_network_status():
    """
    获取网络状态
    
    Returns:
        dict: 网络状态信息
    """
    status = {
        "internet_connected": check_internet_connection(),
        "timestamp": time.time()
    }
    
    # 检查关键服务可用性
    services = {
        "google": "8.8.8.8",
        "baidu": "114.114.114.114"
    }
    
    service_status = {}
    for name, host in services.items():
        try:
            socket.create_connection((host, 53), timeout=3)
            service_status[name] = True
        except:
            service_status[name] = False
    
    status["services"] = service_status
    return status


def safe_request(url, **kwargs):
    """
    安全的网络请求
    
    Args:
        url: 请求URL
        **kwargs: 其他请求参数
        
    Returns:
        响应对象或None
    """
    import requests
    
    try:
        response = requests.get(url, **kwargs)
        response.raise_for_status()
        return response
    except Exception as e:
        logger.error(f"网络请求失败: {e}")
        return None