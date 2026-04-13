# utils/map_visualizer.py
import json
from typing import List, Dict, Optional
from utils.logger import get_logger

logger = get_logger("map_visualizer")


def generate_map_html(attractions: List[Dict], city: str) -> str:
    """
    生成包含景点标记的地图HTML

    Args:
        attractions: 景点列表，每个包含name, description
        city: 城市名称

    Returns:
        HTML字符串
    """
    # 简化的地图实现（实际应调用高德地图API）
    markers = []
    for i, attr in enumerate(attractions[:5]):
        markers.append({
            "id": i,
            "name": attr.get("name", "未知"),
            "description": attr.get("description", "")[:100]
        })

    html = f"""
    <div style="background: #f0f0f0; padding: 20px; border-radius: 10px; text-align: center;">
        <p>🗺️ <strong>{city}景点地图</strong></p>
        <p>（实际地图需要配置高德地图API）</p>
        <ul style="text-align: left;">
    """

    for marker in markers:
        html += f"<li><strong>{marker['name']}</strong>: {marker['description']}...</li>"

    html += """
        </ul>
        <p style="color: #666; font-size: 12px;">💡 提示：配置高德地图API后可显示交互式地图</p>
    </div>
    """

    return html


def extract_attractions_from_itinerary(itinerary: Dict) -> List[Dict]:
    """从行程中提取景点列表"""
    attractions = []
    content = itinerary.get("content", "")

    # 简单提取（实际应用需要更智能的解析）
    lines = content.split('\n')
    for line in lines:
        if '**' in line and ('景点' in line or '景区' in line):
            # 提取景点名称
            import re
            match = re.search(r'\*\*([^*]+)\*\*', line)
            if match:
                attractions.append({
                    "name": match.group(1),
                    "description": line[:100]
                })

    return attractions