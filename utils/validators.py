# utils/validators.py
import re
from typing import Any, Dict, List, Optional


def validate_city_name(city: str) -> bool:
    """
    校验城市名称
    Args:
        city: 城市名称字符串
    Returns:
        是否有效
    """
    if not city or not isinstance(city, str):
        return False
    # 只允许中文、英文、空格、点号（如"Bali"、"New York"、"中国·北京"）
    pattern = r'^[\u4e00-\u9fa5a-zA-Z\s·.]+$'
    city = city.strip()
    return bool(re.match(pattern, city)) and 1 <= len(city) <= 30


def validate_days(days: Any) -> bool:
    """
    校验旅行天数
    Args:
        days: 天数数值
    Returns:
        是否有效（1-30之间的整数）
    """
    if not isinstance(days, int):
        try:
            days = int(days)
        except (ValueError, TypeError):
            return False
    return 1 <= days <= 30


def sanitize_user_input(text: str) -> str:
    """
    清洗用户输入，移除潜在危险字符
    Args:
        text: 原始用户输入
    Returns:
        清洗后的文本
    """
    if not isinstance(text, str):
        return ""

    # 移除危险字符
    dangerous_chars = ['<', '>', '{', '}', '[', ']', '\\', ';', '`', '|', '&', '$', '#', '(', ')']
    for char in dangerous_chars:
        text = text.replace(char, '')

    # 限制最大长度，防止过长输入
    max_length = 2000
    if len(text) > max_length:
        text = text[:max_length]

    return text.strip()


def validate_preference(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """
    校验并标准化用户偏好
    Args:
        preferences: 原始偏好字典
    Returns:
        标准化后的偏好字典
    """
    valid_preferences = {}

    # 定义有效的偏好键和值范围
    valid_keys = {
        "diet": ["local", "vegetarian", "halal", "any"],
        "pacing": ["relaxed", "moderate", "intensive"],
        "interests": ["history", "nature", "art", "food", "shopping"],
        "budget": ["budget", "moderate", "luxury"],
        "accompanied": ["solo", "couple", "family", "friends"]
    }

    for key, valid_values in valid_keys.items():
        if key in preferences:
            value = preferences[key]
            if isinstance(value, str) and value.lower() in valid_values:
                valid_preferences[key] = value.lower()
            elif isinstance(value, list):
                # 处理列表类型的偏好（如兴趣）
                filtered = [v for v in value if v.lower() in valid_values]
                if filtered:
                    valid_preferences[key] = filtered

    return valid_preferences


def validate_api_config(config: Dict[str, Any]) -> Dict[str, bool]:
    """
    校验API配置是否完整
    Args:
        config: 加载的apis.yml配置
    Returns:
        各服务的校验结果
    """
    results = {}

    # 校验千问配置
    qwen = config.get("qwen", {})
    results["qwen_api_key"] = bool(qwen.get("api_key") and qwen["api_key"] != "your_qwen_api_key")
    results["qwen_model"] = bool(qwen.get("model_name"))

    # 校验高德配置
    amap = config.get("amap", {})
    results["amap_weather_key"] = bool(
        amap.get("weather_api_key") and amap["weather_api_key"] != "your_amap_weather_key")
    results["amap_map_key"] = bool(amap.get("map_api_key") and amap["map_api_key"] != "your_amap_map_key")

    return results