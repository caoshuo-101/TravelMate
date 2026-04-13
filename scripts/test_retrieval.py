#!/usr/bin/env python3
"""测试检索功能"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.retriever import RetrievalService
from rag.vector_store import VectorStoreManager


def test_retrieval():
    print("=" * 50)
    print("测试检索功能")
    print("=" * 50)

    # 查看向量库中的内容
    vs = VectorStoreManager()
    print(f"\n向量库文档总数: {vs.collection.count()}")

    # 获取所有文档
    all_docs = vs.collection.get()
    if all_docs['ids']:
        print(f"\n文档列表:")
        for i, doc_id in enumerate(all_docs['ids']):
            print(f"  {i + 1}. ID: {doc_id}")
            print(f"     metadata: {all_docs['metadatas'][i]}")
            print(f"     content: {all_docs['documents'][i][:100]}...")

    # 测试检索
    retriever = RetrievalService()

    test_queries = [
        ("长沙", "长沙"),
        ("长沙景点", "长沙"),
        ("美食", "长沙"),
    ]

    print("\n" + "=" * 50)
    print("检索测试")
    print("=" * 50)

    for query, city in test_queries:
        print(f"\n查询: '{query}', 城市: {city}")
        results = retriever.retrieve(query, city=city, top_k=3)
        print(f"结果数: {len(results)}")
        for r in results:
            print(f"  - 相似度: {r.get('similarity', 0):.3f}")
            print(f"    内容: {r.get('content', '')[:100]}...")


if __name__ == "__main__":
    test_retrieval()