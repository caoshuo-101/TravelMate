# rag/vector_store.py
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from config.settings import settings
from utils.logger import get_logger
from model.embedding_model import default_embedding_model

logger = get_logger("vector_store")


class VectorStoreManager:
    """Chroma向量存储管理器 - 新版实现"""

    def __init__(self, persist_dir: Optional[str] = None, collection_name: Optional[str] = None):
        """
        初始化向量存储管理器

        Args:
            persist_dir: 持久化目录
            collection_name: 集合名称
        """
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME

        logger.info(f"初始化Chroma向量存储: {self.persist_dir}, 集合: {self.collection_name}")

        # 新版 Chroma 客户端初始化方式
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )

        logger.info(f"向量存储初始化完成，当前文档数: {self.collection.count()}")

    def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]) -> bool:
        """
        批量添加文档到向量库

        Args:
            documents: 文档内容列表
            metadatas: 元数据列表
            ids: 文档ID列表

        Returns:
            是否成功
        """
        if not documents:
            logger.warning("添加空文档列表")
            return False

        try:
            # 生成向量
            logger.info(f"生成 {len(documents)} 个文档的向量")
            embeddings = default_embedding_model.embed_documents(documents)

            # 过滤掉向量生成失败的文档
            valid_indices = [i for i, emb in enumerate(embeddings) if emb]
            if not valid_indices:
                logger.error("所有文档向量化失败")
                return False

            valid_docs = [documents[i] for i in valid_indices]
            valid_metadatas = [metadatas[i] for i in valid_indices]
            valid_ids = [ids[i] for i in valid_indices]
            valid_embeddings = [embeddings[i] for i in valid_indices]

            # 添加到Chroma
            self.collection.add(
                documents=valid_docs,
                metadatas=valid_metadatas,
                ids=valid_ids,
                embeddings=valid_embeddings
            )

            logger.info(f"成功添加 {len(valid_docs)} 个文档到向量库")
            return True

        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False

    def similarity_search(self, query: str, k: int = 5, where: Optional[Dict] = None) -> List[Dict]:
        """
        相似度检索

        Args:
            query: 查询文本
            k: 返回结果数量
            where: 过滤条件，如 {"city": "北京"}

        Returns:
            检索结果列表，每个结果包含id, content, metadata, distance
        """
        try:
            # 生成查询向量
            query_embedding = default_embedding_model.embed_text(query)
            if not query_embedding:
                logger.error("查询向量化失败")
                return []

            # 执行检索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            # 格式化结果
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    formatted_results.append({
                        "id": doc_id,
                        "content": results['documents'][0][i] if results['documents'] else "",
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 1.0
                    })

            logger.debug(f"检索完成，查询: {query[:50]}..., 返回 {len(formatted_results)} 条结果")
            return formatted_results

        except Exception as e:
            logger.error(f"相似度检索失败: {e}")
            return []

    def search_by_text(self, query: str, k: int = 5, where: Optional[Dict] = None) -> List[Dict]:
        """
        基于文本的检索（自动向量化）

        Args:
            query: 查询文本
            k: 返回结果数量
            where: 过滤条件

        Returns:
            检索结果列表
        """
        return self.similarity_search(query, k, where)

    def delete_by_ids(self, ids: List[str]) -> bool:
        """
        按ID删除文档

        Args:
            ids: 文档ID列表

        Returns:
            是否成功
        """
        try:
            self.collection.delete(ids=ids)
            logger.info(f"成功删除 {len(ids)} 个文档")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    def delete_by_city(self, city: str) -> bool:
        """
        按城市删除文档

        Args:
            city: 城市名称

        Returns:
            是否成功
        """
        try:
            # 先查询该城市的所有文档
            results = self.collection.get(where={"city": city})
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"成功删除城市 {city} 的 {len(results['ids'])} 个文档")
            return True
        except Exception as e:
            logger.error(f"按城市删除失败: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取向量库统计信息

        Returns:
            统计信息字典
        """
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_dir": self.persist_dir
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"error": str(e)}

    def clear_collection(self) -> bool:
        """
        清空集合

        Returns:
            是否成功
        """
        try:
            # 删除并重新创建集合
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"集合 {self.collection_name} 已清空")
            return True
        except Exception as e:
            logger.error(f"清空集合失败: {e}")
            return False