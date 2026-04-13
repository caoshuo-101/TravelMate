# tools/itinerary.py (完整版)
import json
import uuid
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from langchain.tools import tool
from utils.logger import get_logger

logger = get_logger("itinerary_tool")

# 保存目录
SAVE_DIR = Path("saved_itineraries")
SAVE_DIR.mkdir(parents=True, exist_ok=True)


def save_itinerary_func(itinerary: Dict, name: Optional[str] = None, session_id: str = "default") -> Dict:
    """保存行程的实际逻辑"""
    itinerary_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not name:
        # 从行程内容中提取名称
        city = itinerary.get("city", "未知目的地")
        days = itinerary.get("days", 3)
        name = f"{city}{days}日游_{timestamp}"

    save_data = {
        "id": itinerary_id,
        "name": name,
        "session_id": session_id,
        "created_at": timestamp,
        "itinerary": itinerary,
        "export_count": 0
    }

    filename = f"{itinerary_id}_{name}.json"
    filepath = SAVE_DIR / filename

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        logger.info(f"行程已保存: {filename}")

        return {
            "status": "success",
            "itinerary_id": itinerary_id,
            "name": name,
            "save_path": str(filepath),
            "message": f"✅ 行程「{name}」已保存成功！\n保存路径：{filepath}"
        }
    except Exception as e:
        logger.error(f"保存行程失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "❌ 保存失败，请重试"
        }


@tool
def save_itinerary(itinerary: Dict, name: Optional[str] = None) -> str:
    """保存当前行程规划"""
    result = save_itinerary_func(itinerary, name)
    return result.get("message", "保存失败")


def export_itinerary_func(itinerary_id: str, format: str = "markdown") -> Dict:
    """导出行程的实际逻辑"""
    # 查找文件
    files = list(SAVE_DIR.glob(f"{itinerary_id}*.json"))
    if not files:
        return {"status": "error", "message": f"❌ 未找到行程ID: {itinerary_id}"}

    with open(files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 更新导出计数
    data["export_count"] = data.get("export_count", 0) + 1
    with open(files[0], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if format == "markdown":
        content = _format_itinerary_to_markdown(data)
        output_path = SAVE_DIR / f"{itinerary_id}_report.md"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {
            "status": "success",
            "format": format,
            "content": content,
            "file_path": str(output_path),
            "message": f"✅ 行程报告已导出：{output_path}"
        }
    else:
        return {"status": "error", "message": f"❌ 不支持的格式: {format}"}


@tool
def export_itinerary(itinerary_id: str, format: str = "markdown") -> str:
    """导出行程报告（Markdown格式）"""
    result = export_itinerary_func(itinerary_id, format)
    return result.get("message", "导出失败")


def list_saved_itineraries_func(session_id: Optional[str] = None) -> List[Dict]:
    """列出所有已保存的行程"""
    files = list(SAVE_DIR.glob("*.json"))
    itineraries = []

    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if session_id and data.get("session_id") != session_id:
                    continue
                itineraries.append({
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "created_at": data.get("created_at"),
                    "export_count": data.get("export_count", 0)
                })
        except Exception:
            continue

    return itineraries


@tool
def list_itineraries() -> str:
    """列出所有已保存的行程"""
    itineraries = list_saved_itineraries_func()
    if not itineraries:
        return "📭 暂无已保存的行程"

    result = "📋 **已保存的行程列表**\n\n"
    for i, it in enumerate(itineraries, 1):
        result += f"{i}. **{it['name']}**\n"
        result += f"   - ID: `{it['id']}`\n"
        result += f"   - 创建时间: {it['created_at']}\n"
        result += f"   - 导出次数: {it['export_count']}\n\n"

    return result


def _format_itinerary_to_markdown(data: Dict) -> str:
    """格式化为精美的Markdown报告"""
    itinerary = data.get("itinerary", {})
    name = data.get("name", "旅行行程")
    created_at = data.get("created_at", "")
    export_count = data.get("export_count", 0)

    md = f"""# ✈️ {name}

---
**创建时间**：{created_at}
**导出次数**：{export_count}
**行程版本**：v{itinerary.get('version', 1)}
---

"""

    # 基本信息
    if "city" in itinerary:
        md += f"## 📍 目的地：{itinerary['city']}\n\n"
    if "days" in itinerary:
        md += f"**行程天数**：{itinerary['days']}天\n\n"

    # 偏好信息
    preferences = itinerary.get("preferences", {})
    if preferences:
        pacing_map = {"relaxed": "悠闲", "moderate": "适中", "intensive": "紧凑"}
        budget_map = {"budget": "经济", "moderate": "适中", "luxury": "豪华"}
        md += "## 🎯 偏好设置\n\n"
        md += f"- 旅行节奏：{pacing_map.get(preferences.get('pacing', 'moderate'), '适中')}\n"
        md += f"- 预算：{budget_map.get(preferences.get('budget', 'moderate'), '适中')}\n"
        if preferences.get("interests"):
            md += f"- 兴趣：{', '.join(preferences.get('interests', []))}\n"
        md += "\n"

    # 详细行程内容
    content = itinerary.get("content", "")
    if content:
        md += "## 📅 详细行程\n\n"
        md += content

    # 修改历史
    modification_history = itinerary.get("modification_history", [])
    if modification_history:
        md += "\n---\n## 📝 修改历史\n\n"
        for i, mod in enumerate(modification_history, 1):
            md += f"{i}. **{mod.get('timestamp', '未知时间')}**\n"
            md += f"   - 修改类型：{mod.get('modification_type', 'general')}\n"
            md += f"   - 修改内容：{mod.get('modification', '')}\n\n"

    md += "\n---\n"
    md += "*本行程由旅途智伴 TravelMate 生成*\n"

    return md