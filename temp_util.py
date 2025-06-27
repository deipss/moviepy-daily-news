import json

from moviepy import VideoFileClip
from moviepy.video.fx import Loop

from ollama_client import OllamaClient
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from abc import abstractmethod
from dataclasses import dataclass
from typing import List
import re
import sys
import os
import requests
from datetime import datetime
from logging_config import logger
from fake_useragent import UserAgent
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

NEWS_JSON_FILE_NAME = "news_results.json"
PROCESSED_NEWS_JSON_FILE_NAME = "news_results_processed.json"
CN_NEWS_FOLDER_NAME = "news"
FINAL_VIDEOS_FOLDER_NAME = "final_videos"
EVENING_TAG = "_E"
EVENING = False
CHINADAILY = 'cn_daily'
CHINADAILY_EN = 'cn_daily_en'
CHINADAILY_HK = 'cn_daily_hk'
ALJ = 'alj'
CFR = 'cfr'
BBC = 'bbc'

AUDIO_FILE_NAME = "summary_audio.mp3"

SUB_COUNT = 15

proxies = {
    'http': 'http://127.0.0.1:10809',
    'https': 'http://127.0.0.1:10809',
}


def generate_audio(text: str, output_file: str = "audio.wav", name='zh-CN-XiaoxiaoNeural', rewrite=False) -> None:
    logger.info(f"{output_file}开始生成音频: {text}")
    rate = 70
    sh = f'edge-tts --voice {name} --text "{text}" --write-media {output_file} --rate="+{rate}%"'
    os.system(sh)


def voice_verify():
    for i in ['zh-CN-XiaoxiaoNeural', 'zh-CN-XiaoyiNeural', 'zh-TW-HsiaoChenNeural', 'zh-TW-HsiaoYuNeural',
              'zh-CN-liaoning-XiaobeiNeural', 'zh-CN-shaanxi-XiaoniNeural']:
        generate_audio("你好，这一个清澈见底工的测试", output_file=f"temp/{i}audio.wav", name=i)


def proxy_verify():
    # url = 'https://www.aljazeera.com/'
    url = 'https://www.bbc.com'
    try:
        print(url)
        ua = UserAgent()

        ua_random = ua.random
        headers = {"User-Agent": ua_random,
                   "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
                   "Connection": "keep-alive",
                   "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                   "Upgrade-Insecure-Requests": "1"
                   }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        print(response.text)
    except requests.RequestException as e:
        print(f"fetch_page请求失败: {url} 错误信息： {e}")


def _generate_text_silicon(prompt):
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

    response = requests.request("POST", url, json=payload, headers=headers)
    if response.status_code == 200:
        content = response.json()['choices'][0]['message']['content']
        return {'response': content.replace("\n", "").replace(" ", "")}

    logger.error(f"ollama请求失败，状态码: {response.status_code}, 响应内容: {response.text}")
    return {"error": f"请求失败，状态码: {response.status_code}"}


def _silicon_t():
    max_tokens = 150,
    text = """Tech giant rejects ‘false reports’ after Iranian state media urges citizens to delete messaging app. US tech giant Meta has expressed concern that Iran may block WhatsApp after state media claimed the messaging service is being used for snooping by Israel. “We’re concerned these false reports will be an excuse for our services to be blocked at a time when people need them the most,” Meta, the parent company of Facebook, WhatsApp and Instagram, said in a statement on Tuesday. “All of the messages you send to family and friends on WhatsApp are end-to-end encrypted meaning no-one except the sender and recipient has access to those messages, not even WhatsApp.” Meta added that it does not track users’ precise location or maintain logs of who is messaging whom. “We do not provide bulk information to any government,” the California-based tech firm said. “For over a decade, Meta has provided consistent transparency reports that include the limited circumstances when WhatsApp information has been requested.” Meta’s statement came after the  Islamic Republic News Agency (IRNA) urged citizens to deactivate or delete their WhatsApp accounts because the “Zionist regime is using citizens’ information to harm us”. “This is extremely important because they are using the information on your phone, your location and the content you share, which is likely private but still accessible,” an IRNA host said, according to a subtitled clip shared by Iraqi media outlet Rudaw. “Many of us have friends and relatives living nearby, and some of them could be nuclear scientists or beloved figures, don’t forget.” End-to-end encryption makes it technically impossible for third parties, including tech companies, to access the contents of messages while they are en route from a sender to a recipient. However, Meta and other tech platforms do collect so-called metadata, such as contacts and device information, which they can share with authorities when requested. Iran added WhatsApp and Instagram to its list of prohibited apps in September 2022 amid protests over the death of Mahsa Amini, a 22-year-old Iranian Kurd, in custody. Iranian authorities voted to lift the ban two months later as part of reforms to enhance internet freedom promised by President Masoud Pezeshkian."""
    prompt = f"""1.请从以下新闻主题，提取出影响力最高的5个，这5个主题每个主题再精简到10个字左右，
    2.同时请排除一些未成年内容,
    3.如果发生死亡事件，需要用罹难等词汇替换，
    4.只需返回按序号排列5个主题,每行一个：
    {text}"""
    a = _generate_text_silicon(prompt)
    print(a)


if __name__ == '__main__':
    v = VideoFileClip('videos/man_announcer_1.mp4')
    a = v.duration
    # v.subclipped(start_time=a * 0.3, end_time=a * 0.75).with_effects([Loop(duration=15)]).preview()

    v.subclipped(start_time=a * 0.3, end_time=a * 0.75).write_videofile('videos/man_announcer_1.mp4', fps=24)
