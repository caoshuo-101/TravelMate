# model/chat_model.py
import asyncio
from typing import Optional, Any, Dict, List, Iterator
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from utils.logger import get_logger
from model.factory import ModelFactory

logger = get_logger("chat_model")


class ChatModelWrapper:
    """对话模型封装：添加超时、重试、日志、流式功能"""

    def __init__(self, model_name: Optional[str] = None, timeout: int = 30, max_retries: int = 3):
        """
        初始化对话模型包装器

        Args:
            model_name: 模型名称
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
        """
        self.model = ModelFactory.get_chat_model(model_name=model_name)
        self.timeout = timeout
        self.max_retries = max_retries

    def _format_messages(self, messages: List[Dict[str, str]]) -> List:
        """
        格式化消息为LangChain格式

        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "..."}]

        Returns:
            LangChain消息对象列表
        """
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                formatted.append(SystemMessage(content=content))
            elif role == "assistant":
                formatted.append(AIMessage(content=content))
            else:
                formatted.append(HumanMessage(content=content))

        return formatted

    def invoke(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """
        同步调用模型（带重试机制）

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            **kwargs: 其他参数传递给模型

        Returns:
            模型生成的文本
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"LLM调用尝试 {attempt + 1}/{self.max_retries}")
                response = self.model.invoke(messages, **kwargs)
                logger.debug(f"LLM调用成功，响应长度: {len(response.content)}")
                return response.content
            except Exception as e:
                logger.warning(f"LLM调用失败（第{attempt + 1}次）: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"LLM调用最终失败: {e}")
                    raise
                import time
                time.sleep(2 ** attempt)  # 指数退避

        return "抱歉，模型调用失败，请稍后重试。"

    async def invoke_async(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """
        异步调用模型（带超时和重试机制）

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            **kwargs: 其他参数传递给模型

        Returns:
            模型生成的文本
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"异步LLM调用尝试 {attempt + 1}/{self.max_retries}")
                response = await asyncio.wait_for(
                    self.model.ainvoke(messages, **kwargs),
                    timeout=self.timeout
                )
                logger.debug(f"异步LLM调用成功，响应长度: {len(response.content)}")
                return response.content
            except asyncio.TimeoutError:
                logger.warning(f"LLM调用超时（第{attempt + 1}次）")
                if attempt == self.max_retries - 1:
                    raise TimeoutError(f"LLM调用超时超过{self.max_retries}次")
            except Exception as e:
                logger.warning(f"异步LLM调用失败（第{attempt + 1}次）: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        return "抱歉，模型调用失败，请稍后重试。"

    def stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Iterator[str]:
        """
        流式调用模型

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            **kwargs: 其他参数传递给模型

        Yields:
            生成的文本块
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            for chunk in self.model.stream(messages, **kwargs):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"流式调用失败: {e}")
            yield f"抱歉，生成过程出错: {e}"

    def stream_invoke(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Iterator[str]:
        """
        流式调用模型（别名方法）

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            **kwargs: 其他参数传递给模型

        Yields:
            生成的文本块
        """
        return self.stream(prompt, system_prompt, **kwargs)

    def chat_with_history(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        带历史记录的对话

        Args:
            messages: 完整对话历史
            **kwargs: 其他参数

        Returns:
            模型回复
        """
        formatted_messages = self._format_messages(messages)

        for attempt in range(self.max_retries):
            try:
                response = self.model.invoke(formatted_messages, **kwargs)
                return response.content
            except Exception as e:
                logger.warning(f"带历史的对话失败（第{attempt + 1}次）: {e}")
                if attempt == self.max_retries - 1:
                    raise

        return "抱歉，对话生成失败，请稍后重试。"

    def chat_with_history_stream(self, messages: List[Dict[str, str]], **kwargs) -> Iterator[str]:
        """
        带历史记录的流式对话

        Args:
            messages: 完整对话历史
            **kwargs: 其他参数

        Yields:
            生成的文本块
        """
        formatted_messages = self._format_messages(messages)

        try:
            for chunk in self.model.stream(formatted_messages, **kwargs):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"流式对话失败: {e}")
            yield f"抱歉，生成过程出错: {e}"


# 创建默认实例
default_chat_model = ChatModelWrapper()