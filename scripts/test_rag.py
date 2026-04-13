#!/usr/bin/env python3
# scripts/test_rag.py
"""
RAG模块测试脚本
用于测试向量存储和检索功能
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.logger import setup_logger
from rag.vector_store import VectorStoreManager
from rag.knowledge_base import KnowledgeBaseManager
from rag.retriever import RetrievalService

logger = setup_logger("test_rag")


def test_vector_store():
    """测试向量存储"""
    logger.info("=" * 50)
    logger.info("测试向量存储")
    logger.info("=" * 50)

    try:
        # 初始化向量存储
        vs = VectorStoreManager()
        logger.info(f"向量存储初始化成功，当前文档数: {vs.collection.count()}")

        # 获取统计信息
        stats = vs.get_stats()
        logger.info(f"统计信息: {stats}")

        return True
    except Exception as e:
        logger.error(f"向量存储测试失败: {e}")
        return False


def test_knowledge_base():
    """测试知识库管理"""
    logger.info("=" * 50)
    logger.info("测试知识库管理")
    logger.info("=" * 50)

    try:
        kb = KnowledgeBaseManager()

        # 列出城市
        cities = kb.list_cities()
        logger.info(f"已加载的城市: {cities}")

        # 测试加载北京文档
        if "北京" in cities:
            docs = kb.load_city_documents("北京")
            logger.info(f"北京文档加载完成，共 {len(docs)} 个文档块")
            if docs:
                logger.info(f"第一个文档块预览: {docs[0]['content'][:100]}...")

        # 测试添加文档
        test_content = """
        测试景点：示例公园
        这是一个用于测试的示例景点。
        开放时间：全天
        门票：免费
        """
        success = kb.add_document("测试城市", test_content, doc_type="attraction", source="test")
        logger.info(f"添加测试文档: {'成功' if success else '失败'}")

        return True
    except Exception as e:
        logger.error(f"知识库测试失败: {e}")
        return False


def test_retrieval():
    """测试检索服务"""
    logger.info("=" * 50)
    logger.info("测试检索服务")
    logger.info("=" * 50)

    try:
        retriever = RetrievalService()

        # 测试基本检索
        query = "故宫"
        results = retriever.retrieve(query, city="北京")
        logger.info(f"检索 '{query}' 返回 {len(results)} 条结果")

        if results:
            logger.info(f"第一条结果: {results[0].get('content', '')[:100]}...")
            logger.info(f"相似度: {results[0].get('similarity', 0)}")

        # 测试格式化上下文
        context = retriever.retrieve_with_context(query, city="北京")
        logger.info(f"格式化上下文长度: {len(context)} 字符")

        # 测试混合检索
        hybrid_results = retriever.hybrid_search(query, keywords=["故宫", "门票"], city="北京")
        logger.info(f"混合检索返回 {len(hybrid_results)} 条结果")

        return True
    except Exception as e:
        logger.error(f"检索测试失败: {e}")
        return False


def test_embedding():
    """测试Embedding功能"""
    logger.info("=" * 50)
    logger.info("测试Embedding功能")
    logger.info("=" * 50)

    try:
        from model.embedding_model import default_embedding_model

        # 测试单个文本向量化
        text = "北京故宫是中国明清两代的皇家宫殿"
        vector = default_embedding_model.embed_text(text)
        logger.info(f"文本向量化成功，向量维度: {len(vector)}")

        # 测试批量向量化
        texts = ["故宫", "长城", "颐和园"]
        vectors = default_embedding_model.embed_documents(texts)
        logger.info(f"批量向量化成功，返回 {len(vectors)} 个向量")

        # 测试缓存
        cached_vector = default_embedding_model.embed_text(text)
        logger.info(f"缓存测试成功")

        return True
    except Exception as e:
        logger.error(f"Embedding测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("旅途智伴 RAG模块测试")
    print("=" * 60 + "\n")

    tests = [
        ("Embedding功能", test_embedding),
        ("向量存储", test_vector_store),
        ("知识库管理", test_knowledge_base),
        ("检索服务", test_retrieval),
    ]

    results = {}
    for test_name, test_func in tests:
        print(f"\n>>> 运行测试: {test_name}")
        results[test_name] = test_func()

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️ 部分测试失败，请检查日志")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())