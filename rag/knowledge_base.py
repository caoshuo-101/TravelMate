# rag/knowledge_base.py
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from config.settings import settings
from utils.logger import get_logger
from rag.vector_store import VectorStoreManager

logger = get_logger("knowledge_base")


class KnowledgeBaseManager:
    """知识库管理器：负责文档的增删改查"""

    def __init__(self, data_dir: Optional[str] = None, vector_store: Optional[VectorStoreManager] = None):
        """
        初始化知识库管理器

        Args:
            data_dir: 数据目录路径
            vector_store: 向量存储实例
        """
        self.data_dir = Path(data_dir or settings.DATA_DIR)
        self.vector_store = vector_store or VectorStoreManager()

        # 确保数据目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"知识库管理器初始化完成，数据目录: {self.data_dir}")

    def _read_file(self, file_path: Path) -> str:
        """
        读取文件内容

        Args:
            file_path: 文件路径

        Returns:
            文件内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            return ""

    def _classify_file(self, filename: str) -> str:
        """
        根据文件名分类文档类型

        Args:
            filename: 文件名

        Returns:
            文档类型: attraction/restaurant/guide
        """
        filename_lower = filename.lower()
        if 'attraction' in filename_lower or '景点' in filename_lower:
            return "attraction"
        elif 'restaurant' in filename_lower or '美食' in filename_lower or '餐厅' in filename_lower:
            return "restaurant"
        else:
            return "guide"

    def _chunk_text(self, text: str, max_length: int = 1000) -> List[str]:
        """
        将长文本分块

        Args:
            text: 原始文本
            max_length: 每块最大长度

        Returns:
            文本块列表
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        # 按段落分割
        paragraphs = text.split('\n\n')
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_length:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # 如果单个段落太长，进一步分割
                if len(para) > max_length:
                    # 按句子分割
                    sentences = para.replace('。', '。\n').replace('！', '！\n').replace('？', '？\n')
                    for sentence in sentences.split('\n'):
                        if sentence.strip():
                            if len(sentence) > max_length:
                                # 最后手段：按长度切割
                                for i in range(0, len(sentence), max_length):
                                    chunks.append(sentence[i:i + max_length])
                            else:
                                chunks.append(sentence)
                    current_chunk = ""
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def load_city_documents(self, city: str) -> List[Dict[str, Any]]:
        """
        加载指定城市的所有文档

        Args:
            city: 城市名称

        Returns:
            文档列表，每个文档包含content和metadata
        """
        city_dir = self.data_dir / city
        if not city_dir.exists():
            logger.warning(f"城市目录不存在: {city_dir}")
            return []

        documents = []
        doc_id_counter = 0

        for file_path in city_dir.iterdir():
            if file_path.suffix.lower() in ['.txt', '.md', '.json']:
                content = self._read_file(file_path)
                if content:
                    # 分块处理长文档
                    chunks = self._chunk_text(content)
                    doc_type = self._classify_file(file_path.name)

                    for i, chunk in enumerate(chunks):
                        documents.append({
                            "content": chunk,
                            "metadata": {
                                "city": city,
                                "source": file_path.name,
                                "type": doc_type,
                                "chunk_index": i,
                                "total_chunks": len(chunks)
                            },
                            "id": f"{city}_{file_path.stem}_{i}"
                        })
                        doc_id_counter += 1

        logger.info(f"加载城市 {city} 的文档，共 {len(documents)} 个文档块")
        return documents

    def add_document(self, city: str, content: str, doc_type: str = "guide", source: str = "user_input") -> bool:
        """
        添加单个文档到知识库

        Args:
            city: 城市名称
            content: 文档内容
            doc_type: 文档类型
            source: 来源标识

        Returns:
            是否成功
        """
        try:
            # 分块处理
            chunks = self._chunk_text(content)
            documents = []
            metadatas = []
            ids = []

            import hashlib
            base_id = hashlib.md5(f"{city}_{source}".encode()).hexdigest()[:8]

            for i, chunk in enumerate(chunks):
                doc_id = f"{city}_{base_id}_{i}"
                documents.append(chunk)
                metadatas.append({
                    "city": city,
                    "source": source,
                    "type": doc_type,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "timestamp": str(Path.cwd())  # 简化版，实际应使用datetime
                })
                ids.append(doc_id)

            # 添加到向量库
            success = self.vector_store.add_documents(documents, metadatas, ids)

            if success:
                logger.info(f"成功添加文档到城市 {city}，共 {len(documents)} 个块")
            return success

        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False

    def update_document(self, doc_id: str, content: str) -> bool:
        """
        更新文档

        Args:
            doc_id: 文档ID
            content: 新内容

        Returns:
            是否成功
        """
        try:
            # 先删除旧文档
            self.vector_store.delete_by_ids([doc_id])

            # 添加新文档（简化：使用原ID）
            # 注意：实际使用中需要保留原metadata
            success = self.vector_store.add_documents(
                [content],
                [{"updated": True}],
                [doc_id]
            )

            if success:
                logger.info(f"成功更新文档 {doc_id}")
            return success

        except Exception as e:
            logger.error(f"更新文档失败: {e}")
            return False

    def delete_city(self, city: str) -> bool:
        """
        删除整个城市的知识库

        Args:
            city: 城市名称

        Returns:
            是否成功
        """
        try:
            # 从向量库删除
            success = self.vector_store.delete_by_city(city)

            # 可选：也删除原始文件
            city_dir = self.data_dir / city
            if city_dir.exists():
                import shutil
                shutil.rmtree(city_dir)
                logger.info(f"删除城市目录: {city_dir}")

            if success:
                logger.info(f"成功删除城市 {city} 的知识库")
            return success

        except Exception as e:
            logger.error(f"删除城市知识库失败: {e}")
            return False

    def list_cities(self) -> List[str]:
        """
        列出所有已加载的城市

        Returns:
            城市名称列表
        """
        cities = []
        for item in self.data_dir.iterdir():
            if item.is_dir():
                cities.append(item.name)
        return cities

    def get_city_stats(self, city: str) -> Dict[str, Any]:
        """
        获取城市知识库统计信息

        Args:
            city: 城市名称

        Returns:
            统计信息字典
        """
        city_dir = self.data_dir / city
        if not city_dir.exists():
            return {"city": city, "exists": False}

        files = list(city_dir.glob("*"))
        return {
            "city": city,
            "exists": True,
            "file_count": len(files),
            "files": [f.name for f in files]
        }

    def rebuild_from_files(self, city: Optional[str] = None) -> bool:
        """
        从文件重建知识库

        Args:
            city: 指定城市，不传则重建所有

        Returns:
            是否成功
        """
        try:
            if city:
                cities = [city]
            else:
                cities = self.list_cities()

            total_docs = 0
            for city_name in cities:
                # 删除旧数据
                self.vector_store.delete_by_city(city_name)

                # 重新加载
                docs = self.load_city_documents(city_name)
                if docs:
                    documents = [d["content"] for d in docs]
                    metadatas = [d["metadata"] for d in docs]
                    ids = [d["id"] for d in docs]

                    success = self.vector_store.add_documents(documents, metadatas, ids)
                    if success:
                        total_docs += len(docs)
                        logger.info(f"重建城市 {city_name} 完成，{len(docs)} 个文档")

            logger.info(f"知识库重建完成，共 {total_docs} 个文档")
            return True

        except Exception as e:
            logger.error(f"重建知识库失败: {e}")
            return False