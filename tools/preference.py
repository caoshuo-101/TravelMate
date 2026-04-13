# tools/preference.py
from typing import Dict, Any, Optional
from langchain.tools import tool
from utils.logger import get_logger
from utils.validators import validate_preference

logger = get_logger("preference_tool")

# 全局偏好存储（会话级别）
_session_preferences: Dict[str, Dict] = {}


@tool
def update_user_preference(key: str, value: Any, session_id: str = "default") -> Dict:
    """
    更新用户偏好

    Args:
        key: 偏好键（diet/pacing/interests/budget/accompanied）
        value: 偏好值
        session_id: 会话ID

    Returns:
        更新后的偏好字典
    """
    logger.info(f"更新用户偏好: {key}={value}")

    # 初始化会话偏好
    if session_id not in _session_preferences:
        _session_preferences[session_id] = {
            "diet": "any",
            "pacing": "moderate",
            "interests": [],
            "budget": "moderate",
            "accompanied": "solo"
        }

    preferences = _session_preferences[session_id]

    # 更新偏好
    valid_keys = ["diet", "pacing", "interests", "budget", "accompanied"]
    if key in valid_keys:
        preferences[key] = value
        logger.info(f"偏好已更新: {key} -> {value}")
    else:
        logger.warning(f"无效的偏好键: {key}")

    return {
        "status": "success",
        "key": key,
        "value": value,
        "preferences": preferences
    }


@tool
def get_user_preference(key: Optional[str] = None, session_id: str = "default") -> Dict:
    """
    获取用户偏好

    Args:
        key: 偏好键，不传则返回全部
        session_id: 会话ID

    Returns:
        偏好信息字典
    """
    # 获取会话偏好
    preferences = _session_preferences.get(session_id, {
        "diet": "any",
        "pacing": "moderate",
        "interests": [],
        "budget": "moderate",
        "accompanied": "solo"
    })

    if key:
        value = preferences.get(key)
        return {
            "status": "success",
            "key": key,
            "value": value
        }
    else:
        return {
            "status": "success",
            "preferences": preferences
        }


@tool
def clear_user_preference(session_id: str = "default") -> Dict:
    """
    清除用户偏好

    Args:
        session_id: 会话ID

    Returns:
        操作结果
    """
    if session_id in _session_preferences:
        _session_preferences[session_id] = {
            "diet": "any",
            "pacing": "moderate",
            "interests": [],
            "budget": "moderate",
            "accompanied": "solo"
        }
        logger.info(f"已清除会话 {session_id} 的偏好")

    return {"status": "success", "message": "偏好已重置"}


def format_preferences(preferences: Dict) -> str:
    """格式化偏好信息"""
    pacing_map = {"relaxed": "悠闲", "moderate": "适中", "intensive": "紧凑"}
    budget_map = {"budget": "经济", "moderate": "适中", "luxury": "豪华"}
    diet_map = {"local": "当地特色", "vegetarian": "素食", "halal": "清真", "any": "不限制"}
    interests_map = {
        "history": "历史", "nature": "自然", "art": "艺术",
        "food": "美食", "shopping": "购物"
    }

    result = "**当前偏好设置**\n\n"
    result += f"🍽️ 饮食偏好: {diet_map.get(preferences.get('diet', 'any'), '不限制')}\n"
    result += f"🏃 旅行节奏: {pacing_map.get(preferences.get('pacing', 'moderate'), '适中')}\n"
    result += f"💰 预算: {budget_map.get(preferences.get('budget', 'moderate'), '适中')}\n"

    interests = preferences.get('interests', [])
    if interests:
        interest_texts = [interests_map.get(i, i) for i in interests]
        result += f"🎯 兴趣偏好: {', '.join(interest_texts)}\n"

    return result