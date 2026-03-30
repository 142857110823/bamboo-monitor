"""
系统监控模块
提供性能监控和警报机制
"""
import threading
import time
import logging
from datetime import datetime

from core.resource_monitor import get_resource_health
from core.network_utils import get_network_status

logger = logging.getLogger(__name__)


class SystemMonitor:
    """
    系统监控类
    """
    
    def __init__(self, check_interval=60):
        """
        初始化系统监控
        
        Args:
            check_interval: 检查间隔（秒）
        """
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.alerts = []
        self.metrics = []
    
    def start(self):
        """
        启动监控线程
        """
        if self.running:
            logger.warning("监控线程已经在运行")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("系统监控已启动")
    
    def stop(self):
        """
        停止监控线程
        """
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("系统监控已停止")
    
    def _monitor_loop(self):
        """
        监控循环
        """
        while self.running:
            try:
                self._check_system()
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
            time.sleep(self.check_interval)
    
    def _check_system(self):
        """
        检查系统状态
        """
        # 检查资源状态
        resource_health = get_resource_health()
        
        # 检查网络状态
        network_status = get_network_status()
        
        # 记录指标
        metric = {
            "timestamp": time.time(),
            "resource_health": resource_health,
            "network_status": network_status
        }
        self.metrics.append(metric)
        
        # 限制指标数量
        if len(self.metrics) > 100:
            self.metrics = self.metrics[-100:]
        
        # 检查是否需要生成警报
        self._check_alerts(resource_health, network_status)
    
    def _check_alerts(self, resource_health, network_status):
        """
        检查是否需要生成警报
        
        Args:
            resource_health: 资源健康状态
            network_status: 网络状态
        """
        # 检查资源状态警报
        if resource_health.get("overall") == "危险":
            alert = {
                "timestamp": time.time(),
                "level": "严重",
                "type": "资源警告",
                "message": f"系统资源状态危险: CPU={resource_health.get('cpu')}, 内存={resource_health.get('memory')}, 磁盘={resource_health.get('disk')}"
            }
            self.alerts.append(alert)
            logger.warning(alert["message"])
        
        # 检查网络状态警报
        if not network_status.get("internet_connected"):
            alert = {
                "timestamp": time.time(),
                "level": "警告",
                "type": "网络警告",
                "message": "网络连接失败，可能影响部分功能"
            }
            self.alerts.append(alert)
            logger.warning(alert["message"])
        
        # 限制警报数量
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]
    
    def get_metrics(self, limit=10):
        """
        获取系统指标
        
        Args:
            limit: 返回指标数量限制
            
        Returns:
            list: 系统指标列表
        """
        return self.metrics[-limit:]
    
    def get_alerts(self, limit=10):
        """
        获取警报信息
        
        Args:
            limit: 返回警报数量限制
            
        Returns:
            list: 警报信息列表
        """
        return self.alerts[-limit:]
    
    def clear_alerts(self):
        """
        清除所有警报
        """
        self.alerts = []
        logger.info("警报已清除")


# 全局监控实例
_system_monitor = None


def get_system_monitor():
    """
    获取系统监控实例
    
    Returns:
        SystemMonitor: 系统监控实例
    """
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


def start_monitoring():
    """
    启动系统监控
    """
    monitor = get_system_monitor()
    monitor.start()


def stop_monitoring():
    """
    停止系统监控
    """
    monitor = get_system_monitor()
    monitor.stop()


def get_monitoring_status():
    """
    获取监控状态
    
    Returns:
        dict: 监控状态
    """
    monitor = get_system_monitor()
    return {
        "running": monitor.running,
        "check_interval": monitor.check_interval,
        "metrics_count": len(monitor.metrics),
        "alerts_count": len(monitor.alerts)
    }


def get_recent_metrics(limit=10):
    """
    获取最近的系统指标
    
    Args:
        limit: 返回指标数量限制
        
    Returns:
        list: 系统指标列表
    """
    monitor = get_system_monitor()
    return monitor.get_metrics(limit)


def get_recent_alerts(limit=10):
    """
    获取最近的警报
    
    Args:
        limit: 返回警报数量限制
        
    Returns:
        list: 警报信息列表
    """
    monitor = get_system_monitor()
    return monitor.get_alerts(limit)


def clear_alerts():
    """
    清除所有警报
    """
    monitor = get_system_monitor()
    monitor.clear_alerts()