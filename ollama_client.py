import requests
from typing import Dict, Any
from logging_config import logger

import time
from functools import wraps


def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"函数 {func.__name__} 耗时 {elapsed_time:.4f} 秒")
        return result

    return wrapper


def timeit_methods(cls):
    for name, value in vars(cls).items():
        if callable(value) and not name.startswith("_"):  # 忽略私有方法
            setattr(cls, name, timeit(value))
    return cls


@timeit_methods
class OllamaClient:
    """
    用于与Ollama服务进行交互的客户端类。
    """

    def __init__(self, base_url: str = "http://47.120.48.245:11434"):
        """
        初始化Ollama客户端。

        :param base_url: Ollama服务的基础URL，默认为"http://47.120.48.245:11434"
        """
        self.base_url = base_url

    def _extract_think(self, summary, is_replace_line=True):
        # 直接找到 </think> 的位置进行截断，并清理前后空格和换行符
        think_end = summary.find('</think>')
        if think_end != -1:
            summary = summary[think_end + len('</think>'):].strip()
        else:
            summary = summary.strip()
        if is_replace_line:
            summary = summary.replace("\n", "")
        return summary

    def _generate_text(self, prompt: str, model: str = "deepseek-r1:8b", options: Dict[str, Any] = None) -> Dict[
        str, Any]:
        """
        使用Ollama服务生成文本。

        :param prompt: 输入的提示文本
        :param model: 使用的模型名称，默认为"deepseek-r1:8b"
        :param options: 其他选项，如max_tokens等
        :return: 包含生成文本的字典
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "options": options or {},
            "stream": False
        }
        response = requests.post(url, json=payload)

        # 检查 HTTP 状态码是否为 200 (OK)
        if response.status_code == 200:
            try:
                # 尝试解析 JSON 数据
                return response.json()
            except ValueError as e:
                # 处理 JSON 解析失败的情况
                logger.error(f"JSON 解析失败: {e}")
                return {"error": "无法解析响应内容"}
        else:
            # 记录错误信息
            logger.error(f"请求失败，状态码: {response.status_code}, 响应内容: {response.text}")
            return {"error": f"请求失败，状态码: {response.status_code}"}

    def get_models(self) -> Dict[str, Any]:
        """
        获取可用的模型列表。

        :return: 包含模型信息的字典
        """
        url = f"{self.base_url}/api/tags"
        response = requests.get(url)
        return response.json()

    def generate_summary(self, text: str, model: str = "deepseek-r1:8b", max_tokens: int = 200) -> str:
        """
        生成中文文本的摘要。

        :param text: 输入的中文文本
        :param model: 使用的模型名称，默认为"deepseek-r1:8b"
        :param max_tokens: 摘要的最大token数，默认为50
        :return: 生成的摘要文本
        """
        prompt = f"请为以下文本生成一个简洁的中文摘要（不超过{max_tokens}个字）：\n{text}"
        cnt = 3
        response = self._generate_text(prompt, model, {"max_tokens": max_tokens})
        while cnt > 0:
            if "error" in response:
                response = self._generate_text(prompt, model, {"max_tokens": max_tokens})
                logger.error(f"生成摘要失败: {response['error']},text={text}")
            cnt -= 1
        summary = response.get("response", "")
        summary = self._extract_think(summary)

        if len(summary) > max_tokens:
            logger.info(f"当前摘要={summary}")
            logger.info(f"当前摘要={len(summary)},摘要超过{max_tokens}个字，再次生成摘要")
            prompt = f"请为以下文本生成一个简洁的中文摘要（不超过{max_tokens}个字）：\n{summary}"
            response = self._generate_text(prompt, model, {"max_tokens": max_tokens})
            summary = response.get("response", "")
            summary = self._extract_think(summary)

        return summary

    def generate_top_topic(self, text: str, model: str = "deepseek-r1:8b", max_tokens: int = 50) -> str:
        prompt = f"请从以下新闻主题，提取出影响力最高的4个，这4个主题每个主题再精简到10个字左右，同时请排除一些未成年内容,只需返回按序号排列4个主题：\n{text}"
        response = self._generate_text(prompt, model, {"max_tokens": max_tokens})
        summary = response.get("response", "")
        summary = self._extract_think(summary, is_replace_line=False)
        summary = summary.replace("**", "")
        if len(summary) > max_tokens:
            logger.info(f"当前主题={summary}")
            logger.info(f"当前主题={len(summary)},主题超过{max_tokens}个字，再次生成主题")
            prompt = f"请从以下新闻主题，提取出影响力最高的4个，这4个主题每个主题再精简到10个字左右，同时请排除一些未成年内容，只需返回按序号排列4个主题：：\n{summary}"
            response = self._generate_text(prompt, model, {"max_tokens": max_tokens})
            summary = response.get("response", "")
            summary = self._extract_think(summary, is_replace_line=False)
            summary = summary.replace("**", "")
        return summary

    def translate_to_chinese(self, text: str, model: str = "deepseek-r1:8b") -> str:
        """
        将英文文本翻译成中文。

        :param text: 输入的英文文本
        :param model: 使用的模型名称，默认为"deepseek-r1:8b"
        :return: 翻译后的中文文本
        """
        prompt = f"请将以下英文文本翻译成中文：\n{text}"
        response = self._generate_text(prompt, model)
        return self._extract_think(response.get("response", ""))

    def translate_to_english(self, text: str, model: str = "deepseek-r1:8b") -> str:
        """
        将英文文本翻译成中文。

        :param text: 输入的英文文本
        :param model: 使用的模型名称，默认为"deepseek-r1:8b"
        :return: 翻译后的中文文本
        """
        prompt = f"请将以下英文文本翻译成英文：\n{text}"
        response = self._generate_text(prompt, model)
        return self._extract_think(response.get("response", ""))
