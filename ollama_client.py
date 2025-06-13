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
        elapsed_time = time.time() - start_time
        logger.info(f" 函数 {func.__name__} 耗时 {elapsed_time:.4f} 秒")
        return result

    return wrapper


def timeit_methods(cls):
    for name, value in vars(cls).items():
        if callable(value) and not name.startswith("_"):  # 忽略私有方法
            setattr(cls, name, timeit(value))
    return cls


@timeit_methods
class OllamaClient:

    def __init__(self, base_url: str = "http://47.120.48.245:11434"):
        self.base_url = base_url

    def _extract_think(self, text, is_replace_line=True):
        think_end = text.find('</think>')
        if think_end != -1:
            text = text[think_end + len('</think>'):].strip()
        else:
            text = text.strip()
        if is_replace_line:
            text = text.replace("\n", "")
        return text

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
                logger.error(f"ollama JSON 解析失败: {e}", exc_info=True)
                return {"error": "无法解析响应内容"}
        else:
            # 记录错误信息
            logger.error(f"ollama请求失败，状态码: {response.status_code}, 响应内容: {response.text}")
            return {"error": f"请求失败，状态码: {response.status_code}"}

    def get_models(self) -> Dict[str, Any]:
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
                logger.error(f"生成摘要失败,last time is {cnt}: {response['error']},text={text}")
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

    def generate_summary_cn(self, text: str, model: str = "deepseek-r1:8b", max_tokens: int = 200) -> str:
        """
        生成中文文本的摘要。

        :param text: 输入的中文文本
        :param model: 使用的模型名称，默认为"deepseek-r1:8b"
        :param max_tokens: 摘要的最大token数，默认为50
        :return: 生成的摘要文本
        """

        # 如果文本过长，截断为最大长度
        max_length = 5000  # 假设 API 支持的最大长度为 5000 字符
        if len(text) > max_length:
            # 找到最后一个英文句号的位置
            last_period_index = text.rfind('.', 0, max_length)
            logger.info(f"当前文本过长，当前长度={len(text)},截取到{last_period_index}")
            if last_period_index != -1:
                text = text[:last_period_index + 1]
            else:
                text = text[:max_length]

        prompt = f"请为以下文本生成一个简洁的中文摘要（不超过{max_tokens}个字）：\n{text}"
        cnt = 3
        response = self._generate_text(prompt, model, {"max_tokens": max_tokens})
        while cnt > 0:
            if "error" in response:
                response = self._generate_text(prompt, model, {"max_tokens": max_tokens})
                logger.error(f"生成摘要失败,last time is {cnt}: {response['error']},text={text}")
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
            prompt = f"请从以下新闻主题，提取出影响力最高的4个，这4个主题每个主题再精简到8个字左右，同时请排除一些未成年内容，只需返回按序号排列4个主题：：\n{summary}"
            response = self._generate_text(prompt, model, {"max_tokens": max_tokens // 10 * 9})
            summary = response.get("response", "")
            summary = self._extract_think(summary, is_replace_line=False)
            summary = summary.replace("**", "")
        return summary

    def generate_top_title(self, text: str, model: str = "deepseek-r1:8b",
                           max_tokens: int = 80, count: int = 15) -> str:
        prompt = f"请从以下带有序号的新闻主题，提取出影响力最高的{count}个，过滤一些区县市的新闻，最终返回影响力最高的新闻的原始序号（用英文逗号隔开）：\n{text}"
        response = self._generate_text(prompt, model, {"max_tokens": max_tokens})
        summary = response.get("response", "")
        summary = self._extract_think(summary, is_replace_line=False)
        summary = summary.replace("**", "")
        return summary

    def translate_to_chinese(self, text: str, model: str = "deepseek-r1:8b") -> str:

        prompt = f"请将以下英文文本翻译成中文,只返回中文：\n{text}"
        response = self._generate_text(prompt, model)
        return self._extract_think(response.get("response", ""))

    def translate_to_english(self, text: str, model: str = "deepseek-r1:8b") -> str:

        prompt = f"请将以下英文文本翻译成英文，只返回英文：\n{text}"
        response = self._generate_text(prompt, model)
        return self._extract_think(response.get("response", ""))


if __name__ == '__main__':
    client = OllamaClient()
    print(client.generate_summary_cn(
        """
        At least 26 people were killed in Israeli drone strikes while waiting for basic aid distributed by the Gaza Humanitarian Foundation. Israeli attacks have killed at least 42 people across Gaza since dawn, medical sources told Al Jazeera, as the United Nations General Assembly prepares for a vote urging an unconditional ceasefire in the besieged enclave. Sources told Al Jazeera that at least 26 of the people killed on Thursday died in Israeli drone attacks while waiting for food and basic supplies being distributed by the controversial United States and Israel-backedGaza Humanitarian Foundation (GHF). Gaza civil defence official Mohammed el-Mougher told AFP news agency that al-Awda Hospital received at least 10 bodies and about 200 others who were wounded “after Israeli drones dropped multiple bombs on gatherings of civilians near an aid distribution point around the Netzarim checkpoint in central Gaza”. El-Mougher said that Gaza City’s al-Shifa Hospital also received six bodies after Israeli attacks on aid queues near Netzarim and in the as-Sudaniya area in northwestern Gaza. Since the GHF began its operation in Gaza in late May,dozens of Palestinians have been killedwhile trying to reach the aid distribution points, according to Gaza’s civil defence agency. The previously unknown GHF has come under intense criticism from the United Nations, which says its distribution model is deeply flawed. “This model will not address the deepening hunger. The dystopian ‘Hunger Games’ cannot become the new reality,” Philippe Lazzarini, the chief of the UN Palestinian refugee agency (UNRWA), wrote on X. “The UN including @UNRWA has the knowledge, expertise & community trust to provide dignified & safe assistance. Just let the humanitarians do their jobs,” he added. Separately, a medical source at al-Shifa Hospital told Al Jazeera that two Palestinians were killed as a result of Israeli shelling targeting the Bir an-Naaja area west of Jabalia refugee camp in northern Gaza. Meanwhile, Hamas condemned on Thursday the decision of Israel to cut off communication lines in Gaza, describing it as “a new aggressive step” in the country’s “war of extermination”. “We call on the international community to assume its responsibility to stop the aggression and ensure the protection of civilians and humanitarian and civilian facilities.” The disruption of communications has resulted in theUNRWAlosing contact with its colleagues in the agency in Gaza, the UN’s main humanitarian provider in Gaza said. The latest developments come as the UN General Assembly is set to vote on a draft resolution that demands an immediate, unconditional and permanent ceasefire in the war in Gaza. The 193-member General Assembly is likely to adopt the text with overwhelming support, diplomats say, despite Israel lobbying countries this week against taking part in what it called a “politically motivated, counterproductive charade”. Last week, the United States vetoed a similar effort in the Security Council.
        """
    ))
