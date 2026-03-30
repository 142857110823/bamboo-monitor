"""
错误处理模块
提供统一的错误处理和异常捕获机制
"""
import logging
import traceback
from functools import wraps

logger = logging.getLogger(__name__)


def error_handler(func):
    """
    通用错误处理装饰器
    
    Args:
        func: 被装饰的函数
        
    Returns:
        包装后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {e}")
            logger.error(traceback.format_exc())
            # 可以根据需要返回默认值或重新抛出异常
            return None
    return wrapper


def database_error_handler(func):
    """
    数据库操作错误处理装饰器
    
    Args:
        func: 被装饰的函数
        
    Returns:
        包装后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"数据库操作 {func.__name__} 执行失败: {e}")
            logger.error(traceback.format_exc())
            # 数据库操作失败时的处理逻辑
            return None
    return wrapper


def model_error_handler(func):
    """
    模型操作错误处理装饰器
    
    Args:
        func: 被装饰的函数
        
    Returns:
        包装后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"模型操作 {func.__name__} 执行失败: {e}")
            logger.error(traceback.format_exc())
            # 模型操作失败时的处理逻辑
            return None
    return wrapper


def image_processing_error_handler(func):
    """
    图像处理错误处理装饰器
    
    Args:
        func: 被装饰的函数
        
    Returns:
        包装后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"图像处理 {func.__name__} 执行失败: {e}")
            logger.error(traceback.format_exc())
            # 图像处理失败时的处理逻辑
            return None
    return wrapper


def safe_execution(default=None):
    """
    安全执行装饰器，执行失败时返回默认值
    
    Args:
        default: 执行失败时返回的默认值
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"安全执行 {func.__name__} 失败: {e}")
                logger.error(traceback.format_exc())
                return default
        return wrapper
    return decorator


def handle_exception(exception, context=""):
    """
    处理异常的通用函数
    
    Args:
        exception: 捕获的异常
        context: 异常发生的上下文
        
    Returns:
        dict: 错误信息
    """
    error_info = {
        "error": str(exception),
        "context": context,
        "traceback": traceback.format_exc()
    }
    
    logger.error(f"异常处理 - {context}: {exception}")
    logger.error(traceback.format_exc())
    
    return error_info


def get_error_message(exception):
    """
    获取友好的错误信息
    
    Args:
        exception: 捕获的异常
        
    Returns:
        str: 友好的错误信息
    """
    error_map = {
        "FileNotFoundError": "文件不存在，请检查文件路径",
        "PermissionError": "权限不足，请检查文件或目录权限",
        "ValueError": "参数错误，请检查输入值",
        "TypeError": "类型错误，请检查参数类型",
        "ConnectionError": "连接错误，请检查网络连接",
        "TimeoutError": "超时错误，请检查网络连接或服务状态",
        "MemoryError": "内存不足，请关闭其他应用程序或增加内存",
        "ZeroDivisionError": "除零错误，请检查计算逻辑",
    }
    
    error_type = type(exception).__name__
    return error_map.get(error_type, f"发生错误: {str(exception)}")