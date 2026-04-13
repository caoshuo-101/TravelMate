# agent/state.py
from typing import TypedDict, List, Dict, Optional, Any, Annotated
from enum import Enum
from datetime import datetime
import operator


class ConversationMode(Enum):
    """对话模式枚举"""
    PLANNING = "planning"
    MODIFYING = "modifying"
    QA = "qa"
    UNKNOWN_CITY = "unknown_city"


# 自定义 reducer 函数
def overwrite_reducer(current: Any, new: Any) -> Any:
    """覆盖模式：用新值替换旧值"""
    return new


def list_append_reducer(current: List, new: List) -> List:
    """列表追加模式"""
    if current is None:
        return new or []
    return (current or []) + (new or [])


def dict_merge_reducer(current: Dict, new: Dict) -> Dict:
    """字典合并模式"""
    if current is None:
        return new or {}
    result = (current or {}).copy()
    result.update(new or {})
    return result


class TravelState(TypedDict):
    """旅行规划状态数据结构"""

    # 对话基础信息
    messages: Annotated[List[Dict[str, str]], list_append_reducer]  # 对话历史，追加模式
    current_mode: Annotated[str, overwrite_reducer]  # 当前模式，覆盖模式
    user_input: str  # 当前用户输入（单节点写入）

    # 旅行规划数据
    city: Optional[str]
    days: Optional[int]
    current_itinerary: Optional[Dict]
    itinerary_history: Annotated[List[Dict], list_append_reducer]  # 历史记录，追加模式

    # 用户数据
    user_preferences: Annotated[Dict[str, Any], dict_merge_reducer]  # 用户偏好，合并模式
    user_id: Optional[str]

    # 检索与工具结果
    retrieved_docs: Annotated[List[Dict], list_append_reducer]  # 检索结果，追加模式
    tool_results: Annotated[Dict[str, Any], dict_merge_reducer]  # 工具结果，合并模式
    tool_calls: List[Dict]

    # 系统状态
    error_count: int
    next_action: Annotated[str, overwrite_reducer]  # 下一个动作，覆盖模式
    need_human_input: bool
    response: Annotated[str, overwrite_reducer]  # 响应内容，覆盖模式

    # 元数据
    timestamp: str
    iteration: int


def create_initial_state(user_input: str = "") -> TravelState:
    """创建初始状态"""
    return {
        "messages": [],
        "current_mode": ConversationMode.PLANNING.value,
        "user_input": user_input,
        "city": None,
        "days": None,
        "current_itinerary": None,
        "itinerary_history": [],
        "user_preferences": {
            "pacing": "moderate",
            "budget": "moderate",
            "interests": [],
            "diet": "any"
        },
        "user_id": None,
        "retrieved_docs": [],
        "tool_results": {},
        "tool_calls": [],
        "error_count": 0,
        "next_action": "",
        "need_human_input": False,
        "response": "",
        "timestamp": datetime.now().isoformat(),
        "iteration": 0
    }