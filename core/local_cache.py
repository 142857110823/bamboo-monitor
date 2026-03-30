"""
本地缓存模块
实现对静态资源的本地缓存，减少外部网络依赖
"""
import os
import json
import pickle
import logging
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class LocalCache:
    """本地缓存类"""
    
    def __init__(self, cache_dir=None):
        """
        初始化本地缓存
        Args:
            cache_dir: 缓存目录路径
        """
        if cache_dir is None:
            # 默认缓存目录
            self.cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
        else:
            self.cache_dir = cache_dir
        
        # 确保缓存目录存在
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 缓存元数据文件
        self.metadata_file = os.path.join(self.cache_dir, "metadata.json")
        self.metadata = self._load_metadata()
    
    def _load_metadata(self):
        """
        加载缓存元数据
        Returns:
            dict: 缓存元数据
        """
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载缓存元数据失败: {e}")
        return {}
    
    def _save_metadata(self):
        """
        保存缓存元数据
        """
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存元数据失败: {e}")
    
    def _get_cache_key(self, url):
        """
        生成缓存键
        Args:
            url: 资源URL
        Returns:
            str: 缓存键
        """
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache_file(self, key):
        """
        获取缓存文件路径
        Args:
            key: 缓存键
        Returns:
            str: 缓存文件路径
        """
        return os.path.join(self.cache_dir, key)
    
    def get(self, url, ttl=86400):
        """
        获取本地缓存
        Args:
            url: 资源URL
            ttl: 缓存过期时间（秒）
        Returns:
            缓存数据或None
        """
        key = self._get_cache_key(url)
        cache_file = self._get_cache_file(key)
        
        # 检查缓存是否存在
        if not os.path.exists(cache_file):
            return None
        
        # 检查缓存是否过期
        if key in self.metadata:
            created_at = datetime.fromisoformat(self.metadata[key]['created_at'])
            if (datetime.now() - created_at).total_seconds() > ttl:
                # 缓存过期，删除
                self.remove(url)
                return None
        
        # 读取缓存数据
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"读取缓存失败: {e}")
            self.remove(url)
            return None
    
    def set(self, url, data):
        """
        设置本地缓存
        Args:
            url: 资源URL
            data: 缓存数据
        """
        key = self._get_cache_key(url)
        cache_file = self._get_cache_file(key)
        
        # 写入缓存数据
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            
            # 更新元数据
            self.metadata[key] = {
                'url': url,
                'created_at': datetime.now().isoformat(),
                'size': os.path.getsize(cache_file)
            }
            self._save_metadata()
            return True
        except Exception as e:
            logger.error(f"写入缓存失败: {e}")
            return False
    
    def remove(self, url):
        """
        移除本地缓存
        Args:
            url: 资源URL
        """
        key = self._get_cache_key(url)
        cache_file = self._get_cache_file(key)
        
        # 删除缓存文件
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except Exception as e:
                logger.error(f"删除缓存文件失败: {e}")
        
        # 更新元数据
        if key in self.metadata:
            del self.metadata[key]
            self._save_metadata()
    
    def clear(self, older_than=None):
        """
        清空本地缓存
        Args:
            older_than: 清理超过指定时间的缓存（秒）
        """
        if older_than is None:
            # 清空所有缓存
            for key in list(self.metadata.keys()):
                self.remove(self.metadata[key]['url'])
        else:
            # 清理过期缓存
            now = datetime.now()
            for key in list(self.metadata.keys()):
                created_at = datetime.fromisoformat(self.metadata[key]['created_at'])
                if (now - created_at).total_seconds() > older_than:
                    self.remove(self.metadata[key]['url'])
    
    def get_stats(self):
        """
        获取缓存统计信息
        Returns:
            dict: 缓存统计信息
        """
        total_size = 0
        total_count = len(self.metadata)
        
        for key, info in self.metadata.items():
            total_size += info.get('size', 0)
        
        return {
            'count': total_count,
            'size': total_size,
            'directory': self.cache_dir
        }
    
    def list_caches(self):
        """
        列出所有缓存
        Returns:
            list: 缓存列表
        """
        return list(self.metadata.values())

# 全局本地缓存实例
local_cache = LocalCache()

# 本地缓存工具函数
def get_local_cache(url, ttl=86400):
    """
    获取本地缓存
    Args:
        url: 资源URL
        ttl: 缓存过期时间（秒）
    Returns:
        缓存数据或None
    """
    return local_cache.get(url, ttl)

def set_local_cache(url, data):
    """
    设置本地缓存
    Args:
        url: 资源URL
        data: 缓存数据
    Returns:
        bool: 是否成功
    """
    return local_cache.set(url, data)

def remove_local_cache(url):
    """
    移除本地缓存
    Args:
        url: 资源URL
    """
    local_cache.remove(url)

def clear_local_cache(older_than=None):
    """
    清空本地缓存
    Args:
        older_than: 清理超过指定时间的缓存（秒）
    """
    local_cache.clear(older_than)

def get_local_cache_stats():
    """
    获取本地缓存统计信息
    Returns:
        dict: 缓存统计信息
    """
    return local_cache.get_stats()
