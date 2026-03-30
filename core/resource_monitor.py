"""
资源监控模块
提供系统资源使用监控和评估功能
"""
import psutil
import logging
import time

logger = logging.getLogger(__name__)


def get_system_resources():
    """
    获取系统资源使用情况
    
    Returns:
        dict: 系统资源使用信息
    """
    try:
        # CPU使用情况
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        memory_total = memory.total / (1024 * 1024)
        memory_available = memory.available / (1024 * 1024)
        memory_used_percent = memory.percent
        
        # 磁盘使用情况
        disk_usage = psutil.disk_usage('/')
        disk_total = disk_usage.total / (1024 * 1024 * 1024)
        disk_used = disk_usage.used / (1024 * 1024 * 1024)
        disk_free = disk_usage.free / (1024 * 1024 * 1024)
        disk_used_percent = disk_usage.percent
        
        # 网络使用情况
        net_io = psutil.net_io_counters()
        net_sent = net_io.bytes_sent / (1024 * 1024)
        net_recv = net_io.bytes_recv / (1024 * 1024)
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count
            },
            "memory": {
                "total_mb": round(memory_total, 2),
                "available_mb": round(memory_available, 2),
                "used_percent": memory_used_percent
            },
            "disk": {
                "total_gb": round(disk_total, 2),
                "used_gb": round(disk_used, 2),
                "free_gb": round(disk_free, 2),
                "used_percent": disk_used_percent
            },
            "network": {
                "sent_mb": round(net_sent, 2),
                "recv_mb": round(net_recv, 2)
            },
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"获取系统资源失败: {e}")
        return {
            "error": str(e),
            "timestamp": time.time()
        }


def get_resource_health():
    """
    评估系统资源健康状态
    
    Returns:
        dict: 资源健康状态
    """
    resources = get_system_resources()
    
    if "error" in resources:
        return {
            "status": "error",
            "message": resources["error"]
        }
    
    # 评估CPU状态
    cpu_percent = resources["cpu"]["percent"]
    if cpu_percent < 50:
        cpu_status = "良好"
    elif cpu_percent < 80:
        cpu_status = "警告"
    else:
        cpu_status = "危险"
    
    # 评估内存状态
    memory_percent = resources["memory"]["used_percent"]
    if memory_percent < 60:
        memory_status = "良好"
    elif memory_percent < 85:
        memory_status = "警告"
    else:
        memory_status = "危险"
    
    # 评估磁盘状态
    disk_percent = resources["disk"]["used_percent"]
    if disk_percent < 70:
        disk_status = "良好"
    elif disk_percent < 90:
        disk_status = "警告"
    else:
        disk_status = "危险"
    
    # 总体健康状态
    if cpu_status == "危险" or memory_status == "危险" or disk_status == "危险":
        overall_status = "危险"
    elif cpu_status == "警告" or memory_status == "警告" or disk_status == "警告":
        overall_status = "警告"
    else:
        overall_status = "良好"
    
    return {
        "overall": overall_status,
        "cpu": cpu_status,
        "memory": memory_status,
        "disk": disk_status,
        "resources": resources
    }


def get_resource_suggestions():
    """
    根据资源使用情况提供建议
    
    Returns:
        list: 建议列表
    """
    health = get_resource_health()
    suggestions = []
    
    if health["cpu"] == "危险":
        suggestions.append("CPU使用率过高，建议关闭不必要的应用程序或升级硬件")
    
    if health["memory"] == "危险":
        suggestions.append("内存使用过高，建议关闭不必要的应用程序或增加内存")
    
    if health["disk"] == "危险":
        suggestions.append("磁盘空间不足，建议清理磁盘或增加存储空间")
    
    if not suggestions:
        suggestions.append("系统资源使用正常，无需特殊处理")
    
    return suggestions