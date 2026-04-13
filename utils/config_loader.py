# utils/config_loader.py
import os
import yaml
from pathlib import Path
from typing import Any, Dict

class ConfigLoader:
    """配置加载器：加载YAML配置文件"""
    _config_cache: Dict[str, Dict] = {}

    @classmethod
    def _get_config_path(cls, config_name: str) -> Path:
        """获取配置文件的完整路径"""
        base_dir = Path(__file__).parent.parent
        return base_dir / "config" / config_name

    @classmethod
    def load_yaml(cls, config_name: str) -> Dict[str, Any]:
        """
        加载YAML配置文件
        Args:
            config_name: 配置文件名，如 'apis.yml'
        Returns:
            配置字典
        """
        # 检查缓存
        if config_name in cls._config_cache:
            return cls._config_cache[config_name]

        config_path = cls._get_config_path(config_name)
        if not config_path.exists():
            # 如果文件不存在，返回空字典并记录警告
            print(f"警告: 配置文件 {config_path} 不存在")
            return {}

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            cls._config_cache[config_name] = config
            return config

    @classmethod
    def get_api_key(cls, service: str, key_name: str) -> str:
        """
        获取指定服务的API密钥
        Args:
            service: 服务名称，如 'amap' 或 'qwen'
            key_name: 密钥字段名，如 'api_key'
        Returns:
            密钥值
        """
        config = cls.load_yaml("apis.yml")
        return config.get(service, {}).get(key_name, "")

    @classmethod
    def clear_cache(cls):
        """清除配置缓存（用于测试）"""
        cls._config_cache.clear()