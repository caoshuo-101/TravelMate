# rag/background_learner.py - 修复工作线程

import threading
import json
import hashlib
from queue import Queue, Empty
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from utils.logger import get_logger
from model.chat_model import ChatModelWrapper
from rag.vector_store import VectorStoreManager
from config.settings import settings

logger = get_logger("background_learner")


class BackgroundLearner:
    """
    后台学习模块
    当用户询问未录入城市时，自动学习并补充到知识库
    """

    def __init__(self, vector_store: Optional[VectorStoreManager] = None):
        """
        初始化后台学习器

        Args:
            vector_store: 向量存储实例
        """
        self.vector_store = vector_store or VectorStoreManager()
        self.chat_model = ChatModelWrapper()
        self.learning_queue = Queue()
        self.learned_cities = set()
        self._stop_flag = False
        self._worker_thread = None
        self._start_worker()
        logger.info("后台学习模块已启动")

    def _start_worker(self):
        """启动后台工作线程"""

        def worker():
            logger.info("后台学习工作线程开始运行")
            while not self._stop_flag:
                try:
                    # 使用较短的超时，以便检查停止标志
                    task = self.learning_queue.get(timeout=1)
                    if task is None:
                        continue
                    logger.info(f"工作线程获取到任务: {task.get('city')}")
                    self._process_learning_task(task)
                except Empty:
                    # 队列为空，继续循环
                    continue
                except Exception as e:
                    logger.error(f"工作线程异常: {e}", exc_info=True)
                    continue
            logger.info("后台学习工作线程已停止")

        self._worker_thread = threading.Thread(target=worker, daemon=True)
        self._worker_thread.start()
        logger.info("后台学习工作线程已启动")

    def stop(self):
        """停止后台学习线程"""
        self._stop_flag = True
        logger.info("正在停止后台学习线程")

    def submit_learning_task(self, city: str, user_query: str = ""):
        """
        提交学习任务到队列

        Args:
            city: 城市名称
            user_query: 用户原始查询（可选）
        """
        # 清理城市名（去除可能的虚词）
        if city.endswith("的"):
            city = city[:-1]

        # 检查是否已学习过
        if city in self.learned_cities:
            logger.info(f"城市 {city} 已学习过，跳过")
            return

        # 检查是否已在队列中
        for item in list(self.learning_queue.queue):
            if item.get("city") == city:
                logger.info(f"城市 {city} 已在学习队列中，跳过")
                return

        task = {
            "city": city,
            "user_query": user_query,
            "timestamp": datetime.now().isoformat()
        }
        self.learning_queue.put(task)
        logger.info(f"已提交学习任务: {city}, 当前队列大小: {self.learning_queue.qsize()}")

    def _process_learning_task(self, task: Dict):
        """
        处理学习任务：生成城市信息并存入知识库

        Args:
            task: 学习任务
        """
        city = task["city"]
        user_query = task.get("user_query", "")

        # 再次清理城市名
        if city.endswith("的"):
            city = city[:-1]

        logger.info(f"开始学习城市: {city}")

        try:
            # 1. 使用千问生成城市信息
            logger.info(f"正在生成{city}的旅行信息...")
            city_info = self._generate_city_info(city, user_query)

            if not city_info:
                logger.error(f"生成{city}信息失败：返回空内容")
                return

            logger.info(f"生成{city}信息成功，长度: {len(city_info)}字符")

            # 2. 将信息分块并向量化
            logger.info(f"正在保存{city}到知识库...")
            self._save_to_knowledge_base(city, city_info)

            # 3. 记录已学习
            self.learned_cities.add(city)

            logger.info(f"城市 {city} 学习完成！")

        except Exception as e:
            logger.error(f"学习任务处理失败 {city}: {e}", exc_info=True)

    def _generate_city_info(self, city: str, user_query: str = "") -> str:
        """
        使用千问生成城市旅行信息

        Args:
            city: 城市名称
            user_query: 用户原始查询

        Returns:
            生成的城市信息文本
        """
        prompt = f"""请为旅行者生成关于【{city}】的详细旅行信息。

## 输出要求（请严格按照以下格式）

# {city}旅行指南

## 📍 城市简介
（介绍城市的基本情况、特色、文化氛围等，150-200字）

## 🏛️ 必去景点（5-7个）
1. **景点名称**：简短描述、建议游玩时间、门票参考
2. ...

## 🍜 特色美食（3-5个）
1. **美食名称**：简介、推荐餐厅
2. ...

## 🌸 最佳旅行季节
（说明各季节特点，推荐最佳时间）

## 📅 建议游玩天数
（根据城市大小给出建议，如2-3天）

## 💡 实用小贴士
- 交通建议
- 住宿区域推荐
- 注意事项

{f"用户特别询问：{user_query}" if user_query else ""}

请确保信息准确、实用，适合旅行者参考。
"""

        try:
            response = self.chat_model.invoke(prompt, timeout=60)
            if response and len(response) > 100:
                return response
            else:
                logger.warning(f"生成{city}信息内容过短: {len(response) if response else 0}")
                return ""
        except Exception as e:
            logger.error(f"生成{city}信息失败: {e}")
            return ""

    def _save_to_knowledge_base(self, city: str, content: str):
        """
        将生成的内容保存到知识库

        Args:
            city: 城市名称
            content: 内容文本
        """
        try:
            # 确保数据目录存在
            data_dir = Path(settings.DATA_DIR) / city
            data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"数据目录已创建: {data_dir}")

            # 保存原始文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = data_dir / f"auto_generated_{timestamp}.md"

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {city}旅行指南\n\n")
                f.write(f"*自动生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write(content)

            logger.info(f"已保存原始文件: {file_path}")

            # 分块处理
            chunks = self._chunk_text(content, max_length=800)
            logger.info(f"文档分块完成，共 {len(chunks)} 块")

            # 添加到向量库
            documents = []
            metadatas = []
            ids = []

            for i, chunk in enumerate(chunks):
                import hashlib
                doc_id = hashlib.md5(f"{city}_auto_{timestamp}_{i}".encode()).hexdigest()[:16]
                documents.append(chunk)
                metadatas.append({
                    "city": city,
                    "source": f"auto_generated_{timestamp}.md",
                    "type": "auto_generated",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "generated_at": timestamp
                })
                ids.append(doc_id)

            if documents:
                logger.info(f"正在添加 {len(documents)} 个文档块到向量库...")
                success = self.vector_store.add_documents(documents, metadatas, ids)
                if success:
                    logger.info(f"成功添加 {len(documents)} 个文档块到向量库")
                else:
                    logger.error(f"添加文档块失败")
            else:
                logger.warning("没有文档块需要添加")

        except Exception as e:
            logger.error(f"保存到知识库失败: {e}", exc_info=True)

    def _chunk_text(self, text: str, max_length: int = 800) -> List[str]:
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
        # 按标题分块
        import re
        sections = re.split(r'(?=^##\s+)', text, flags=re.MULTILINE)

        current_chunk = ""
        for section in sections:
            if len(current_chunk) + len(section) <= max_length:
                current_chunk += section
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = section

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def get_learned_cities(self) -> List[str]:
        """获取已学习的城市列表"""
        return list(self.learned_cities)

    def is_learning(self, city: str) -> bool:
        """检查城市是否正在学习中"""
        for item in list(self.learning_queue.queue):
            if item.get("city") == city:
                return True
        return False


# 全局实例
_default_learner = None


def get_background_learner() -> BackgroundLearner:
    """获取后台学习器单例"""
    global _default_learner
    if _default_learner is None:
        _default_learner = BackgroundLearner()
    return _default_learner