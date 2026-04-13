# config/settings.py
import os
from pathlib import Path
from typing import Dict, Any, Optional
from utils.config_loader import ConfigLoader


class Settings:
    """统一配置管理类"""

    def __init__(self):
        self._apis_config: Optional[Dict] = None

    @property
    def apis(self) -> Dict[str, Any]:
        """获取API配置"""
        if self._apis_config is None:
            self._apis_config = ConfigLoader.load_yaml("apis.yml")
        return self._apis_config

    # ========== Agent 配置 ==========
    AGENT_MAX_ITERATIONS: int = 10
    AGENT_TIMEOUT: int = 60
    AGENT_TEMPERATURE: float = 0.7

    # RAG 配置
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "travel_knowledge"
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_SCORE_THRESHOLD: float = 0.3  # 从 0.7 降低到 0.3

    # ========== 模型配置 ==========
    @property
    def QWEN_MODEL_NAME(self) -> str:
        return self.apis.get("qwen", {}).get("model_name", "qwen-turbo")

    @property
    def QWEN_EMBEDDING_MODEL(self) -> str:
        return self.apis.get("qwen", {}).get("embedding_model", "text-embedding-v1")

    @property
    def QWEN_API_KEY(self) -> str:
        return self.apis.get("qwen", {}).get("api_key", "")

    # ========== 高德API配置 ==========
    @property
    def AMAP_WEATHER_KEY(self) -> str:
        return self.apis.get("amap", {}).get("weather_api_key", "")

    @property
    def AMAP_MAP_KEY(self) -> str:
        return self.apis.get("amap", {}).get("map_api_key", "")

    # ========== 路径配置 ==========
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    CHROMA_DIR: Path = BASE_DIR / CHROMA_PERSIST_DIR

    # ========== 日志配置 ==========
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"

    # ========== 其他配置 ==========
    MAX_HISTORY_LENGTH: int = 20
    DEFAULT_CITY: str = "北京"
    DEFAULT_TRAVEL_DAYS: int = 3

    # 缓存配置
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600  # 缓存过期时间（秒）
    CACHE_MAX_SIZE: int = 100  # 最大缓存条目数

    def get_qwen_config(self) -> Dict[str, str]:
        """获取千问模型配置字典"""
        return {
            "api_key": self.QWEN_API_KEY,
            "model_name": self.QWEN_MODEL_NAME,
            "embedding_model": self.QWEN_EMBEDDING_MODEL
        }

    def get_amap_config(self) -> Dict[str, str]:
        """获取高德API配置字典"""
        return {
            "weather_key": self.AMAP_WEATHER_KEY,
            "map_key": self.AMAP_MAP_KEY
        }

    def get_agent_config(self) -> Dict[str, Any]:
        """获取Agent配置字典"""
        return {
            "max_iterations": self.AGENT_MAX_ITERATIONS,
            "timeout": self.AGENT_TIMEOUT,
            "temperature": self.AGENT_TEMPERATURE
        }

    def get_chroma_config(self) -> Dict[str, Any]:
        """获取Chroma配置字典"""
        return {
            "persist_dir": self.CHROMA_PERSIST_DIR,
            "collection_name": self.CHROMA_COLLECTION_NAME
        }

    def validate(self) -> Dict[str, bool]:
        """验证所有必要配置是否有效"""
        from utils.validators import validate_api_config

        api_valid = validate_api_config(self.apis)

        # 检查目录是否存在
        dirs_valid = {
            "data_dir": self.DATA_DIR.exists() or self.DATA_DIR.mkdir(parents=True, exist_ok=True),
            "logs_dir": self.LOGS_DIR.exists() or self.LOGS_DIR.mkdir(parents=True, exist_ok=True),
        }

        return {**api_valid, **dirs_valid}


# 创建全局配置实例
settings = Settings()