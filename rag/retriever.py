# rag/retriever.py
from typing import List, Dict, Any, Optional
from config.settings import settings
from utils.logger import get_logger
from rag.vector_store import VectorStoreManager

logger = get_logger("retriever")


class RetrievalService:
    """检索服务：封装检索逻辑"""

    def __init__(self, vector_store: Optional[VectorStoreManager] = None):
        """
        初始化检索服务

        Args:
            vector_store: 向量存储实例
        """
        self.vector_store = vector_store or VectorStoreManager()
        self.top_k = settings.RETRIEVAL_TOP_K
        self.score_threshold = settings.RETRIEVAL_SCORE_THRESHOLD

    def retrieve(self, query: str, city: Optional[str] = None, top_k: Optional[int] = None) -> List[Dict]:
        """
        检索相关信息（改进版）
        """
        # 构建过滤条件
        where_filter = {"city": city} if city else None

        k = top_k or self.top_k

        # 执行检索
        results = self.vector_store.similarity_search(query, k=k * 2, where=where_filter)  # 获取更多结果

        # 过滤和排序
        filtered_results = []
        for result in results:
            similarity = 1 - result.get("distance", 1.0)

            # 对于短查询（<=3字符），使用更低的阈值
            short_query_threshold = 0.2 if len(query) <= 3 else self.score_threshold

            if similarity >= short_query_threshold:
                result["similarity"] = similarity
                filtered_results.append(result)

        # 按相似度排序
        filtered_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        # 如果没有结果且查询词较短，尝试扩展查询
        if not filtered_results and len(query) <= 3:
            logger.info(f"短查询无结果，尝试扩展: {query}")
            expanded_query = f"{query} 旅行 景点 推荐"
            return self.retrieve(expanded_query, city, top_k)

        logger.info(f"检索完成: query={query[:50]}..., city={city}, 返回{len(filtered_results)}条结果")
        return filtered_results[:k]  # 限制返回数量

    def retrieve_with_context(self, query: str, city: Optional[str] = None, top_k: Optional[int] = None) -> str:
        """
        检索并格式化为上下文文本

        Args:
            query: 查询文本
            city: 城市过滤
            top_k: 返回结果数量

        Returns:
            格式化的上下文字符串
        """
        results = self.retrieve(query, city, top_k)

        if not results:
            return "未找到相关信息。"

        context_parts = []
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            source = metadata.get("source", "未知来源")
            doc_type = metadata.get("type", "general")

            context_parts.append(f"[{i}] ({doc_type}) 来自 {source}:\n{content}\n")

        return "\n".join(context_parts)

    def hybrid_search(self, query: str, keywords: Optional[List[str]] = None, city: Optional[str] = None) -> List[Dict]:
        """
        混合检索：向量 + 关键词

        Args:
            query: 查询文本
            keywords: 关键词列表
            city: 城市过滤

        Returns:
            检索结果列表
        """
        # 先执行向量检索
        vector_results = self.retrieve(query, city, top_k=self.top_k * 2)

        if not keywords:
            return vector_results[:self.top_k]

        # 关键词过滤和加权
        for result in vector_results:
            content = result.get("content", "").lower()
            keyword_score = 0
            for keyword in keywords:
                if keyword.lower() in content:
                    keyword_score += 1

            # 调整相似度分数（加权平均）
            original_similarity = result.get("similarity", 0)
            combined_score = original_similarity * 0.7 + (keyword_score / len(keywords)) * 0.3
            result["similarity"] = combined_score

        # 重新排序
        vector_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        return vector_results[:self.top_k]


def search_by_intent(self, query: str, intent: str, city: Optional[str] = None) -> List[Dict]:
    """
    根据意图检索

    Args:
        query: 查询文本
        intent: 意图类型（attraction/restaurant/guide）
        city: 城市过滤

    Returns:
        检索结果列表
    """
    # 构建过滤条件
    where_filter = {}
    if city:
        where_filter["city"] = city
    if intent:
        where_filter["type"] = intent

    # 执行检索
    results = self.vector_store.similarity_search(query, k=self.top_k, where=where_filter)

    # 过滤和排序
    filtered_results = []
    for result in results:
        similarity = 1 - result.get("distance", 1.0)
        if similarity >= self.score_threshold:
            result["similarity"] = similarity
            filtered_results.append(result)

    filtered_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)

    logger.info(f"意图检索完成: intent={intent}, 返回{len(filtered_results)}条结果")
    return filtered_results


def get_relevant_cities(self, query: str) -> List[str]:
    """
    获取查询相关的城市列表

    Args:
        query: 查询文本

    Returns:
        相关城市列表
    """
    results = self.retrieve(query, top_k=10)
    cities = set()

    for result in results:
        metadata = result.get("metadata", {})
        city = metadata.get("city")
        if city:
            cities.add(city)

    return list(cities)


def retrieve_with_fallback(self, query: str, city: Optional[str] = None,
                           top_k: int = 5, llm_fallback: bool = True) -> tuple:
    """
    带回退机制的检索

    Args:
        query: 查询文本
        city: 城市过滤
        top_k: 返回结果数量
        llm_fallback: 是否使用LLM回退

    Returns:
        (results, is_fallback): 检索结果和是否使用了回退
    """
    # 1. 正常检索
    results = self.retrieve(query, city=city, top_k=top_k)

    # 2. 如果有结果，直接返回
    if results:
        return results, False

    # 3. 没有结果且启用LLM回退
    if llm_fallback and city:
        logger.info(f"未找到{city}相关信息，使用LLM生成")

        from model.chat_model import ChatModelWrapper
        chat = ChatModelWrapper()

        fallback_prompt = f"""请提供关于{city}的以下旅行信息：
1. 城市简介
2. 必去景点（3-5个）
3. 特色美食
4. 最佳旅行季节
5. 建议游玩天数

请简洁回答。"""

        try:
            fallback_content = chat.invoke(fallback_prompt)

            # 构造伪检索结果
            fallback_result = [{
                "id": "fallback",
                "content": fallback_content,
                "metadata": {"city": city, "type": "fallback", "source": "llm_generated"},
                "distance": 0.5,
                "similarity": 0.5,
                "is_fallback": True
            }]

            return fallback_result, True
        except Exception as e:
            logger.error(f"LLM回退失败: {e}")

    return [], False


def is_city_in_knowledge_base(self, city: str) -> bool:
    """
    检查城市是否在知识库中

    Args:
        city: 城市名称

    Returns:
        是否存在
    """
    results = self.retrieve(city, city=city, top_k=1)
    return len(results) > 0


# 创建默认实例
default_retriever = RetrievalService()