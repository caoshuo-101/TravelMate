# utils/history_manager.py
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from utils.logger import get_logger

logger = get_logger("history_manager")

HISTORY_DIR = Path("chat_history")
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def save_conversation(messages: List[Dict], session_id: Optional[str] = None) -> str:
    """保存对话历史"""
    if not session_id:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    file_path = HISTORY_DIR / f"{session_id}.json"

    data = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "messages": messages,
        "message_count": len(messages)
    }

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"对话已保存: {file_path}")
    return session_id


def load_conversation(session_id: str) -> Optional[List[Dict]]:
    """加载对话历史"""
    file_path = HISTORY_DIR / f"{session_id}.json"

    if not file_path.exists():
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"对话已加载: {session_id}")
    return data.get("messages", [])


def list_conversations() -> List[Dict]:
    """列出所有保存的对话"""
    conversations = []

    for file_path in HISTORY_DIR.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                conversations.append({
                    "session_id": data.get("session_id"),
                    "created_at": data.get("created_at"),
                    "message_count": data.get("message_count", 0)
                })
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")

    return sorted(conversations, key=lambda x: x.get("created_at", ""), reverse=True)