# model/embedding_model.py
from typing import List, Optional, Dict, Any
from functools import lru_cache
from collections import OrderedDict
from utils.logger import get_logger
from model.factory import ModelFactory

logger = get_logger("embedding_model")


class LRUCache:
    """简单的LRU缓存实现"""

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key: str) -> Optional[List[float]]:
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: List[float]):
        if len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)
        self.cache[key] = value

    def clear(self):
        self.cache.clear()


class EmbeddingModelWrapper:
    """Embedding模型封装：批量处理、缓存"""

    def __init__(self, cache_size: int = 1000):
        """
        初始化Embedding模型包装器

        Args:
            cache_size: 缓存大小，默认1000条
        """
        self.model = ModelFactory.get_embedding_model()
        self.cache = LRUCache(cache_size)
        logger.info(f"Embedding模型初始化完成，缓存大小: {cache_size}")

    def embed_text(self, text: str) -> List[float]:
        """
        单个文本向量化（带缓存）

        Args:
            text: 输入文本

        Returns:
            向量列表
        """
        if not text or not isinstance(text, str):
            logger.warning(f"无效的输入文本: {type(text)}")
            return []

        # 生成缓存键（使用文本的哈希）
        cache_key = str(hash(text))

        # 检查缓存
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"缓存命中: {text[:50]}...")
            return cached

        try:
            logger.debug(f"生成向量: {text[:50]}...")
            # 兼容不同的模型接口
            if hasattr(self.model, 'embed_query'):
                vector = self.model.embed_query(text)
            elif hasattr(self.model, 'embed_documents'):
                vector = self.model.embed_documents([text])[0]
            else:
                # 尝试直接调用
                vector = self.model.embed(text)

            self.cache.put(cache_key, vector)
            return vector
        except Exception as e:
            logger.error(f"向量化失败: {e}")
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化

        Args:
            texts: 文本列表

        Returns:
            向量列表的列表
        """
        if not texts:
            logger.warning("空的文本列表")
            return []

        # 过滤空文本
        valid_texts = [t for t in texts if t and isinstance(t, str)]
        if not valid_texts:
            return []

        try:
            logger.debug(f"批量向量化 {len(valid_texts)} 个文档")
            if hasattr(self.model, 'embed_documents'):
                vectors = self.model.embed_documents(valid_texts)
            else:
                # 逐个调用
                vectors = [self.embed_text(t) for t in valid_texts]
            return vectors
        except Exception as e:
            logger.error(f"批量向量化失败: {e}")
            raise

    def embed_texts_with_progress(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """
        分批向量化大量文本

        Args:
            texts: 文本列表
            batch_size: 批次大小

        Returns:
            向量列表的列表
        """
        all_vectors = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"处理批次 {i // batch_size + 1}/{(total - 1) // batch_size + 1}")

            try:
                vectors = self.embed_documents(batch)
                all_vectors.extend(vectors)
            except Exception as e:
                logger.error(f"批次 {i // batch_size + 1} 处理失败: {e}")
                # 对失败的批次单独处理每个文档
                for text in batch:
                    try:
                        all_vectors.append(self.embed_text(text))
                    except Exception as single_e:
                        logger.error(f"单个文档向量化失败: {single_e}")
                        all_vectors.append([])

        return all_vectors

    def clear_cache(self):
        """清除缓存"""
        self.cache.clear()
        logger.info("Embedding缓存已清除")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_size": len(self.cache.cache),
            "capacity": self.cache.capacity
        }


# 创建默认实例
default_embedding_model = EmbeddingModelWrapper()