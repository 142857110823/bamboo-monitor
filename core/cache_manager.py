"""
缓存管理模块
提供高效的缓存策略，避免缓存溢出和资源浪费
"""
import logging
import time
from functools import lru_cache, wraps
from collections import OrderedDict
import gc

logger = logging.getLogger(__name__)

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, max_size=100, ttl=3600):
        """
        初始化缓存管理器
        Args:
            max_size: 缓存最大容量
            ttl: 缓存过期时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.access_times = {}
    
    def get(self, key):
        """
        获取缓存
        Args:
            key: 缓存键
        Returns:
            缓存值或None
        """
        if key not in self.cache:
            return None
        
        # 检查是否过期
        if time.time() - self.access_times[key] > self.ttl:
            self.remove(key)
            return None
        
        # 更新访问时间并移到末尾（LRU机制）
        self.access_times[key] = time.time()
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def set(self, key, value):
        """
        设置缓存
        Args:
            key: 缓存键
            value: 缓存值
        """
        # 如果缓存已满，移除最久未使用的项
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            self.remove(oldest_key)
        
        # 设置缓存和访问时间
        self.cache[key] = value
        self.access_times[key] = time.time()
    
    def remove(self, key):
        """
        移除缓存
        Args:
            key: 缓存键
        """
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
    
    def clear(self):
        """
        清空缓存
        """
        self.cache.clear()
        self.access_times.clear()
        # 触发垃圾回收
        gc.collect()
    
    def size(self):
        """
        获取缓存大小
        Returns:
            int: 缓存大小
        """
        return len(self.cache)
    
    def contains(self, key):
        """
        检查缓存是否包含指定键
        Args:
            key: 缓存键
        Returns:
            bool: 是否包含
        """
        return key in self.cache
    
    def get_stats(self):
        """
        获取缓存统计信息
        Returns:
            dict: 缓存统计信息
        """
        return {
            'size': self.size(),
            'max_size': self.max_size,
            'ttl': self.ttl,
            'keys': list(self.cache.keys())
        }

# 全局缓存管理器实例
cache_manager = CacheManager(max_size=100, ttl=3600)

# 缓存装饰器
def cached(max_size=128, ttl=3600):
    """
    缓存装饰器
    Args:
        max_size: 缓存最大容量
        ttl: 缓存过期时间（秒）
    Returns:
        function: 装饰后的函数
    """
    def decorator(func):
        # 使用OrderedDict实现LRU缓存
        cache = OrderedDict()
        access_times = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key = str(args) + str(sorted(kwargs.items()))
            
            # 检查缓存
            if key in cache:
                # 检查是否过期
                if time.time() - access_times[key] <= ttl:
                    # 更新访问时间并移到末尾
                    access_times[key] = time.time()
                    cache.move_to_end(key)
                    return cache[key]
                else:
                    # 移除过期缓存
                    del cache[key]
                    del access_times[key]
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 如果缓存已满，移除最久未使用的项
            if len(cache) >= max_size:
                oldest_key = next(iter(cache))
                del cache[oldest_key]
                del access_times[oldest_key]
            
            # 存入缓存
            cache[key] = result
            access_times[key] = time.time()
            
            return result
        
        # 添加缓存管理方法
        wrapper.clear_cache = lambda: (cache.clear(), access_times.clear())
        wrapper.cache_size = lambda: len(cache)
        wrapper.cache_keys = lambda: list(cache.keys())
        
        return wrapper
    
    return decorator

# 缓存工具函数
def get_cached(key, default=None):
    """
    获取缓存
    Args:
        key: 缓存键
        default: 默认值
    Returns:
        缓存值或默认值
    """
    return cache_manager.get(key) or default

def set_cached(key, value):
    """
    设置缓存
    Args:
        key: 缓存键
        value: 缓存值
    """
    cache_manager.set(key, value)

def clear_cache(key=None):
    """
    清除缓存
    Args:
        key: 缓存键（None表示清空所有）
    """
    if key:
        cache_manager.remove(key)
    else:
        cache_manager.clear()

def get_cache_stats():
    """
    获取缓存统计信息
    Returns:
        dict: 缓存统计信息
    """
    return cache_manager.get_stats()
