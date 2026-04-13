# utils/cache.py
from functools import lru_cache
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from collections import OrderedDict
import hashlib
import json

from utils.logger import get_logger

logger = get_logger("cache")


class TTLCache:
    """带过期时间的缓存"""

    def __init__(self, max_size: int = 100, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()

    def _make_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]
        if datetime.now() - timestamp > timedelta(seconds=self.ttl):
            del self.cache[key]
            return None

        self.cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any):
        """设置缓存"""
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)

        self.cache[key] = (value, datetime.now())

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("缓存已清空")


# 全局缓存实例
_query_cache = TTLCache(max_size=50, ttl=1800)  # 30分钟过期


def cached_query(func):
    """查询缓存装饰器"""

    def wrapper(*args, **kwargs):
        # 只缓存检索查询
        if args and "retrieve" in str(args[0]):
            key = _query_cache._make_key(*args, **kwargs)
            cached = _query_cache.get(key)
            if cached is not None:
                logger.debug(f"缓存命中: {key[:16]}...")
                return cached

            result = func(*args, **kwargs)
            _query_cache.set(key, result)
            return result

        return func(*args, **kwargs)

    return wrapper