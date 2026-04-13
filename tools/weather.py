# tools/weather.py (修复版)
import requests
from typing import Dict, Optional
from langchain.tools import tool
from config.settings import settings
from utils.logger import get_logger
from utils.validators import validate_city_name

logger = get_logger("weather_tool")


# 定义工具函数
def query_weather_func(city: str, forecast_days: int = 3) -> Dict:
    """
    查询目标城市的天气信息

    Args:
        city: 城市名称，如"北京"
        forecast_days: 预报天数，默认3天（1-7）

    Returns:
        天气信息字典
    """
    logger.info(f"查询天气: {city}, 预报天数: {forecast_days}")

    # 输入校验
    if not validate_city_name(city):
        return {"error": f"无效的城市名称: {city}"}

    if not 1 <= forecast_days <= 7:
        forecast_days = 3

    api_key = settings.AMAP_WEATHER_KEY
    if not api_key or api_key == "your_amap_weather_key":
        logger.warning("高德天气API密钥未配置")
        return {
            "city": city,
            "error": "天气API密钥未配置",
            "message": f"请配置高德API密钥以获取{city}的天气信息"
        }

    try:
        # 高德天气API
        url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "key": api_key,
            "city": city,
            "extensions": "all" if forecast_days > 1 else "base"
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("status") == "1":
            result = {
                "city": city,
                "forecast_days": forecast_days,
                "live": data.get("lives", [{}])[0] if data.get("lives") else {}
            }

            # 添加预报信息
            if "forecasts" in data and data["forecasts"]:
                forecast = data["forecasts"][0]
                result["forecast"] = {
                    "city": forecast.get("city"),
                    "casts": forecast.get("casts", [])[:forecast_days]
                }

            logger.info(f"天气查询成功: {city}")
            return result
        else:
            logger.error(f"天气查询失败: {data.get('info')}")
            return {
                "city": city,
                "error": f"查询失败: {data.get('info', '未知错误')}"
            }

    except requests.Timeout:
        logger.error(f"天气API超时: {city}")
        return {"city": city, "error": "请求超时，请稍后重试"}
    except Exception as e:
        logger.error(f"天气查询异常: {e}")
        return {"city": city, "error": f"查询异常: {str(e)}"}


# 创建 LangChain 工具（供 Agent 使用）
@tool
def query_weather(city: str, forecast_days: int = 3) -> str:
    """查询目标城市的天气信息"""
    result = query_weather_func(city, forecast_days)
    return format_weather_info(result)


def format_weather_info(weather_data: Dict) -> str:
    """格式化天气信息为可读文本"""
    if "error" in weather_data:
        return f"⚠️ {weather_data['error']}"

    city = weather_data.get("city", "未知城市")
    live = weather_data.get("live", {})

    result = f"**{city}天气信息**\n\n"

    # 实时天气
    if live:
        result += f"🌡️ 实时温度: {live.get('temperature', 'N/A')}°C\n"
        result += f"☁️ 天气: {live.get('weather', 'N/A')}\n"
        result += f"💨 风向: {live.get('winddirection', 'N/A')}\n"
        result += f"🌀 风力: {live.get('windpower', 'N/A')}级\n"
        result += f"💧 湿度: {live.get('humidity', 'N/A')}%\n"

    # 预报信息
    forecast = weather_data.get("forecast", {})
    casts = forecast.get("casts", [])
    if casts:
        result += "\n**未来天气预报:**\n"
        for cast in casts[:weather_data.get("forecast_days", 3)]:
            result += f"\n📅 {cast.get('date')}:\n"
            result += f"   日间: {cast.get('dayweather')} {cast.get('daytemp')}°C\n"
            result += f"   夜间: {cast.get('nightweather')} {cast.get('nighttemp')}°C\n"

    return result

# 导出实际函数供节点调用
__all__ = ['query_weather', 'query_weather_func', 'format_weather_info']