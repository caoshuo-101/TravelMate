# tools/traffic.py
import requests
from typing import Dict, Optional
from langchain.tools import tool
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("traffic_tool")


@tool
def calculate_travel_time(origin: str, destination: str, city: Optional[str] = None) -> Dict:
    """
    计算两地之间的交通方式和耗时

    Args:
        origin: 起点名称
        destination: 终点名称
        city: 所在城市（可选，用于同城交通）

    Returns:
        交通信息字典
    """
    logger.info(f"计算交通耗时: {origin} -> {destination}")

    api_key = settings.AMAP_MAP_KEY
    if not api_key or api_key == "your_amap_map_key":
        logger.warning("高德地图API密钥未配置")
        return {
            "origin": origin,
            "destination": destination,
            "error": "地图API密钥未配置",
            "message": "请配置高德API密钥以获取交通信息"
        }

    try:
        # 先地理编码获取坐标
        geo_url = "https://restapi.amap.com/v3/geocode/geo"
        geo_params = {"key": api_key, "address": origin}

        if city:
            geo_params["city"] = city

        geo_response = requests.get(geo_url, params=geo_params, timeout=10)
        geo_data = geo_response.json()

        if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
            return {"error": f"无法定位起点: {origin}"}

        origin_location = geo_data["geocodes"][0]["location"]

        # 编码终点
        geo_params["address"] = destination
        geo_response = requests.get(geo_url, params=geo_params, timeout=10)
        geo_data = geo_response.json()

        if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
            return {"error": f"无法定位终点: {destination}"}

        dest_location = geo_data["geocodes"][0]["location"]

        # 计算距离和时间
        distance_url = "https://restapi.amap.com/v3/distance"
        distance_params = {
            "key": api_key,
            "origins": origin_location,
            "destination": dest_location,
            "type": "1"  # 直线距离
        }

        distance_response = requests.get(distance_url, params=distance_params, timeout=10)
        distance_data = distance_response.json()

        if distance_data.get("status") == "1" and distance_data.get("results"):
            result = distance_data["results"][0]
            distance_m = int(result.get("distance", 0))
            distance_km = distance_m / 1000

            # 估算交通时间
            driving_time_min = int(distance_m / 500)  # 假设时速30km/h
            walking_time_min = int(distance_m / 80)  # 假设时速4.8km/h
            transit_time_min = int(distance_m / 250)  # 假设时速15km/h

            return {
                "origin": origin,
                "destination": destination,
                "distance": f"{distance_km:.1f}km" if distance_km >= 1 else f"{distance_m}m",
                "distance_meters": distance_m,
                "methods": [
                    {"type": "驾车", "duration": f"{driving_time_min}分钟", "minutes": driving_time_min},
                    {"type": "公共交通", "duration": f"{transit_time_min}分钟", "minutes": transit_time_min},
                    {"type": "步行", "duration": f"{walking_time_min}分钟", "minutes": walking_time_min}
                ],
                "suggestion": self._get_travel_suggestion(distance_m)
            }

        return {"error": "无法计算距离"}

    except Exception as e:
        logger.error(f"交通计算异常: {e}")
        return {"error": f"计算异常: {str(e)}"}


def _get_travel_suggestion(distance_meters: int) -> str:
    """根据距离给出交通建议"""
    if distance_meters < 1000:
        return "距离较近，建议步行或骑行"
    elif distance_meters < 5000:
        return "距离适中，建议打车或公交"
    elif distance_meters < 15000:
        return "距离较远，建议驾车或地铁"
    else:
        return "距离很远，建议驾车或乘坐长途交通"


def format_traffic_info(traffic_data: Dict) -> str:
    """格式化交通信息为可读文本"""
    if "error" in traffic_data:
        return f"⚠️ {traffic_data['error']}"

    result = f"**{traffic_data['origin']} → {traffic_data['destination']}**\n\n"
    result += f"📏 距离: {traffic_data['distance']}\n\n"
    result += "**交通方式建议:**\n"

    for method in traffic_data.get("methods", []):
        result += f"• {method['type']}: {method['duration']}\n"

    if "suggestion" in traffic_data:
        result += f"\n💡 建议: {traffic_data['suggestion']}"

    return result