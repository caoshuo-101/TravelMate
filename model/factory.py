# model/factory.py
from langchain_community.chat_models import ChatTongyi

# 修复：TongyiEmbeddings的正确导入路径
try:
    # 尝试新的导入路径
    from langchain_community.embeddings import TongyiEmbeddings
except ImportError:
    try:
        # 备选导入路径
        from langchain_community.embeddings.dashscope import DashScopeEmbeddings as TongyiEmbeddings
    except ImportError:
        # 如果都不行，使用dashscope直接调用
        TongyiEmbeddings = None
        print("警告: 无法导入TongyiEmbeddings，将使用备用方案")

from typing import Optional, Dict, Any
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("model_factory")


class ModelFactory:
    """模型工厂：统一创建和管理模型实例"""

    _instances: Dict[str, Any] = {}

    @classmethod
    def get_chat_model(cls, model_name: Optional[str] = None, temperature: Optional[float] = None):
        """
        获取对话模型实例（单例模式）

        Args:
            model_name: 模型名称，不传则使用配置中的默认值
            temperature: 温度参数，控制输出随机性，范围0-1

        Returns:
            ChatTongyi实例
        """
        # 使用配置中的默认值
        if model_name is None:
            model_name = settings.QWEN_MODEL_NAME
        if temperature is None:
            temperature = settings.AGENT_TEMPERATURE

        # 生成缓存键
        cache_key = f"chat_{model_name}_{temperature}"

        if cache_key not in cls._instances:
            api_key = settings.QWEN_API_KEY
            if not api_key:
                logger.error("千问API密钥未配置，请在config/apis.yml中设置qwen.api_key")
                raise ValueError("千问API密钥未配置")

            logger.info(f"创建对话模型实例: {model_name}, temperature={temperature}")
            cls._instances[cache_key] = ChatTongyi(
                model=model_name,
                temperature=temperature,
                api_key=api_key
            )

        return cls._instances[cache_key]

    @classmethod
    def get_embedding_model(cls):
        """
        获取Embedding模型实例（单例模式）

        Returns:
            Embedding模型实例
        """
        if "embedding" not in cls._instances:
            api_key = settings.QWEN_API_KEY
            embedding_model = settings.QWEN_EMBEDDING_MODEL

            if not api_key:
                logger.error("千问API密钥未配置，请在config/apis.yml中设置qwen.api_key")
                raise ValueError("千问API密钥未配置")

            logger.info(f"创建Embedding模型实例: {embedding_model}")

            # 尝试不同的导入方式
            if TongyiEmbeddings is not None:
                try:
                    cls._instances["embedding"] = TongyiEmbeddings(
                        model=embedding_model,
                        dashscope_api_key=api_key
                    )
                except Exception as e:
                    logger.warning(f"使用TongyiEmbeddings失败: {e}，尝试备用方案")
                    cls._instances["embedding"] = cls._create_embedding_fallback(api_key, embedding_model)
            else:
                cls._instances["embedding"] = cls._create_embedding_fallback(api_key, embedding_model)

        return cls._instances["embedding"]

    @classmethod
    def _create_embedding_fallback(cls, api_key: str, model_name: str):
        """
        创建备用Embedding模型（使用dashscope直接调用）

        Args:
            api_key: API密钥
            model_name: 模型名称

        Returns:
            Embedding模型实例
        """
        from langchain_community.embeddings import DashScopeEmbeddings

        return DashScopeEmbeddings(
            model=model_name,
            dashscope_api_key=api_key
        )

    @classmethod
    def clear_cache(cls):
        """清除模型缓存（用于测试）"""
        cls._instances.clear()
        logger.info("模型缓存已清除")