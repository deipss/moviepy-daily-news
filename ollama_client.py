import os

import requests
from typing import Dict, Any
from logging_config import logger
import time
from functools import wraps
from dotenv import load_dotenv

MODEL_NAME = "deepseek-r1:8b"
# MODEL_NAME = "qwen3:8b"
def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        logger.info(f" AI 函数 {func.__name__} 耗时 {elapsed_time:.4f} 秒")
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

    def _generate_text_silicon(self, prompt, model):
        load_dotenv()
        token = os.getenv('SILICON_API_KEY')
        url = "https://api.siliconflow.cn/v1/chat/completions"

        payload = {
            "model": "Qwen/Qwen3-8B",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        headers = {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json"
        }
        try:
            response = requests.request("POST", url, json=payload, headers=headers)
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                return {'response': content.replace("\n", "").replace(" ", "")}
            else:
                logger.error(f"ollama请求失败，状态码: {response.status_code}, 响应内容: {response.text}")
                return {"error": f"请求失败"}
        except Exception as e:
            logger.error(f'silicon调用异常 {e}', exc_info=True)
            return {"error": f"请求异常"}

    def _generate_text_local(self, prompt: str, model: str = MODEL_NAME, options: Dict[str, Any] = None) -> Dict[
        str, Any]:
        """
        使用Ollama服务生成文本。

        :param prompt: 输入的提示文本
        :param model: 使用的模型名称，默认为MODEL_NAME
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

    def generate_summary(self, text: str, model: str = MODEL_NAME, max_tokens: int = 200) -> str:
        """
        生成中文文本的摘要。

        :param text: 输入的中文文本
        :param model: 使用的模型名称，默认为MODEL_NAME
        :param max_tokens: 摘要的最大token数，默认为50
        :return: 生成的摘要文本
        """
        prompt = f"请为以下文本生成一份不超过{max_tokens}个字的中文新闻摘要，只返回摘要内容：\n{text}"
        cnt = 3
        response = self._generate_text_local(prompt, model)
        while cnt > 0:
            if "error" in response:
                response = self._generate_text_local(prompt, model)
                logger.error(f"生成摘要失败,last time is {cnt}: {response['error']},text={text}")
            cnt -= 1
        summary = response.get("response", "")
        summary = self._extract_think(summary)

        if len(summary) > max_tokens:
            logger.info(f"当前摘要={summary} {len(summary)}>{max_tokens}个字 再次生成摘要")
            prompt = f"请为以下文本生成一份不超过{max_tokens}个字的中文新闻摘要，只返回摘要内容：\n{summary}"
            response = self._generate_text_local(prompt, model)
            summary = response.get("response", "")
            summary = self._extract_think(summary)

        return summary

    def generate_summary_cn(self, text: str, model: str = MODEL_NAME, max_tokens: int = 200) -> str:
        """
        生成中文文本的摘要。

        :param text: 输入的中文文本
        :param model: 使用的模型名称，默认为MODEL_NAME
        :param max_tokens: 摘要的最大token数，默认为50
        :return: 生成的摘要文本
        """

        # 如果文本过长，截断为最大长度
        max_length = 3000  # 假设 API 支持的最大长度为 5000 字符
        if len(text) > max_length:
            # 找到最后一个英文句号的位置
            last_period_index = text.rfind('.', 0, max_length)
            logger.info(f"当前文本过长，当前长度={len(text)},截取到{last_period_index}")
            if last_period_index != -1:
                text = text[:last_period_index + 1]
            else:
                text = text[:max_length]

        prompt = f"请为以下文本生成一份不超过{max_tokens}个字的中文新闻摘要，只返回摘要内容：\n{text}"
        cnt = 3
        response = self._generate_text_local(prompt, model)
        while cnt > 0:
            if "error" in response:
                response = self._generate_text_local(prompt, model)
                logger.error(f"生成摘要失败,last time is {cnt}: {response['error']},text={text}")
            cnt -= 1
        summary = response.get("response", "")
        summary = self._extract_think(summary)

        if len(summary) > max_tokens:
            logger.info(f"当前摘要={summary} {len(summary)}>{max_tokens}个字 再次生成摘要")
            prompt = f"请为以下文本生成一份不超过{max_tokens}个字的中文新闻摘要，只返回摘要内容：\n{summary}"
            response = self._generate_text_local(prompt, model)
            summary = response.get("response", "")
            summary = self._extract_think(summary)

        return summary

    def optimize_summary_cn(self, text: str, model: str = MODEL_NAME, max_tokens: int = 200) -> str:
        """
        生成中文文本的摘要。

        :param text: 输入的中文文本
        :param model: 使用的模型名称，默认为MODEL_NAME
        :param max_tokens: 摘要的最大token数，默认为50
        :return: 生成的摘要文本
        """
        prompt = f"以下文字是英文翻译后的中文新闻摘要，请优化下内容，以便更适合中文的语境：\n{text}"
        cnt = 3
        response = self._generate_text_local(prompt, model)
        while cnt > 0:
            if "error" in response:
                response = self._generate_text_local(prompt, model)
                logger.error(f"优化摘要失败,last time is {cnt}: {response['error']},text={text}")
            cnt -= 1
        summary = response.get("response", "")
        summary = self._extract_think(summary)

        if len(summary) > max_tokens:
            logger.info(f"当前摘要={summary} {len(summary)}>{max_tokens}个字 再次优化摘要")
            prompt = f"以下文字是英文翻译后的中文新闻摘要，请优化下内容，以更适合中文的语境，尽量不超过个{max_tokens}字：\n{summary}"
            response = self._generate_text_local(prompt, model)
            summary = response.get("response", "")
            summary = self._extract_think(summary)
        return summary

    def generate_top_topic(self, text: str, model: str = MODEL_NAME, max_tokens: int = 66) -> str:

        prompt = f"""1.请从以下新闻主题，提取出影响力最高的5个，这5个主题每个主题再精简到17个字左右，
2.同时请排除一些未成年内容,
3.同时请排除一些死亡事件，
4.只需返回按序号排列5个主题：
{text}"""
        response = self._generate_text_local(prompt, model)
        summary = response.get("response", "")
        summary = self._extract_think(summary, is_replace_line=False)
        if len(summary) > max_tokens:
            logger.info(f"当前主题={summary},{len(summary)} > {max_tokens}个字，再次生成主题")
            prompt = f"""1.请从以下新闻主题，提取出影响力最高的5个，这5个主题每个主题必须精简到15个字以内，
2.同时请排除一些未成年内容,
3.同时请排除一些死亡事件，
4.只需返回按序号排列5个主题：
{summary}"""
            response = self._generate_text_local(prompt, model)
            summary = response.get("response", "")
            summary = self._extract_think(summary, is_replace_line=False)
        summary = summary.replace("**", "")
        return summary.replace('死亡', '罹难')

    def generate_top_title(self, text: str, model: str = MODEL_NAME,
                           max_tokens: int = 80, count: int = 15) -> str:
        prompt = f"请从以下带有序号的新闻主题，提取出影响力最高的{count}个，过滤一些区县市的新闻，最终返回影响力最高的新闻的原始序号（用英文逗号隔开）：\n{text}"
        response = self._generate_text_local(prompt, model)
        summary = response.get("response", "")
        summary = self._extract_think(summary, is_replace_line=False)
        summary = summary.replace("**", "")
        return summary

    def generate_top_news_summary(self, text: str, model: str = MODEL_NAME,
                                  max_tokens: int = 80, count: int = 15) -> str:
        prompt = f"请从以下标题信息，生成一从在{max_tokens}左右的新闻稿：\n{text}"
        response = self._generate_text_local(prompt, model)
        summary = response.get("response", "")
        summary = self._extract_think(summary, is_replace_line=False)
        summary = summary.replace("**", "")
        return summary

    def translate_to_chinese(self, text: str, model: str = MODEL_NAME) -> str:

        prompt = f"请将以下英文文本翻译成中文,只返回中文：\n{text}"
        response = self._generate_text_local(prompt, model)
        return self._extract_think(response.get("response", ""))

    def translate_to_english(self, text: str, model: str = MODEL_NAME) -> str:

        prompt = f"请将以下英文文本翻译成英文，只返回英文：\n{text}"
        response = self._generate_text_local(prompt, model)
        return self._extract_think(response.get("response", ""))


if __name__ == '__main__':
    client = OllamaClient()
    a = client.generate_summary_cn("""
    Thousands of people have poured into Worthy Farm after the gates officially opened for the 2025 Glastonbury Festival. Co-founder Sir Michael Eavis and his daughter Emily Eavis, who now runs the festival, led the countdown shortly before 08:00 BST in front of many who slept outside the gate on Tuesday night. More than 200,000 people are set to descend on the site in the coming days ahead of the main festival programme launching on Friday. Speaking shortly before the gates opened, Ms Eavis told the BBC: \"It's been such a build-up this year, it's been an amazing amount of excitement.\" Ms Eavis said: \"We're all so looking forward to opening the gates and to be able to do it with my dad has been amazing. \"It's the best moment to let them all in and it's just such a joyful city, the most joyful city in the UK for the next five days.\" Hundreds of people arrived on Tuesday night, sleeping under the stars in queues in a bid to be the first on site. Among them were James Trusson, 31, from Ash, Somerset, Grace Ball, 29, from Bournemouth and Dan Mortimore, from Compton Dundon, Somerset, who made it to the front of the line for the second year in a row. Having put themselves in prime position for a top camping spot, Ms Ball said their plans for the rest of the day were to go \"back to the car for snacks, and then sleep\". \"I'll crack a beer I think,\" added Mr Trusson. Hundreds of people have got in touch with the BBC with photos and stories of travelling to the festival - whether that's a train into Castle Cary, a long coach journey or bybike. A coach full of Glastonbury-goers was sat on the hard shoulder of the M6 with a blown tyre, and Bobby told us he had broken down next to the A303 on his way to the festival. Many heading to the festival for the first time shared their excitement, while others said returning for the 13th time was \"pretty awesome\". We also spoke to Laurence, who saidhe quit his job to attend Glastonbury Festival because his leave request was denied. Apart from the expected traffic on the A361 between Glastonbury and Worthy Farm, the main travel routes to the festival have remained relatively clear throughout the day. While the main acts might not start performing until Friday, there is plenty for revellers to enjoy away from the music. There are performances at the circus and theatre fields, seaside entertainment on offer at \"Glastonbury-on-Sea\" and plenty of food and drink stalls. Follow BBC Somerset onFacebookandX. Send your story ideas to us on email or viaWhatsApp on 0800 313 4630. The Indian megastar stands by Sardaar Ji 3 as political tensions threaten to overshadow its release. U2 bassist Adam Clayton delivered a reading at the funeral of Lord Henry Mount Charles in Slane. The Working Class Hero exhibition opened at Birmingham's Museum and Art Gallery on Wednesday. The refurb of University of Wolverhampton at the Halls is shortlisted in the Acoustic Awards 2025. Dafydd Iwan, one of Wales' best known folk singers, says the situation is \"very worrying\". Copyright 2025 BBC. All rights reserved.TheBBCisnot responsible for the content of external sites.Read about our approach to external linking.
    """)
    print(a)
