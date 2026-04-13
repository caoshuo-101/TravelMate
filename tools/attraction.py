# tools/attraction.py (完整修复版)
from typing import List, Dict, Optional
from langchain.tools import tool
from rag.retriever import RetrievalService
from utils.logger import get_logger
from utils.validators import validate_city_name

logger = get_logger("attraction_tool")

_retriever = None


def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = RetrievalService()
    return _retriever


def search_attractions_func(city: str, keyword: str = "", category: str = "") -> List[Dict]:
    """实际的景点搜索逻辑"""
    logger.info(f"搜索景点: city={city}, keyword={keyword}, category={category}")

    if not validate_city_name(city):
        logger.warning(f"无效的城市名称: {city}")
        return []

    retriever = get_retriever()

    if keyword:
        query = f"{city} {keyword}"
    else:
        query = f"{city} 景点推荐"

    results = retriever.retrieve(query, city=city, top_k=5)

    formatted_results = []
    for result in results:
        metadata = result.get("metadata", {})
        formatted_results.append({
            "name": metadata.get("source", "未知").replace(".md", "").replace(".txt", ""),
            "content": result.get("content", ""),
            "type": metadata.get("type", "general"),
            "similarity": result.get("similarity", 0)
        })

    return formatted_results


@tool
def search_attractions(city: str, keyword: str = "", category: str = "") -> str:
    """从知识库中搜索景点信息"""
    results = search_attractions_func(city, keyword, category)
    return format_attractions(results, city)


def format_attractions(attractions: List[Dict], city: str) -> str:
    """格式化景点信息"""
    if not attractions:
        return f"抱歉，未找到关于{city}的相关景点信息。"

    result = f"**{city}景点推荐**\n\n"
    for i, attr in enumerate(attractions[:5], 1):
        result += f"{i}. **{attr['name']}**\n"
        content = attr['content'][:150]
        result += f"   {content}"
        if len(attr['content']) > 150:
            result += "..."
        result += "\n\n"

    return result