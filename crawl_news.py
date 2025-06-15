import json

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
CN_NEWS_FOLDER_NAME = "news_p"
FINAL_VIDEOS_FOLDER_NAME = "final_videos"
TIMES_TAG: int = 0
CHINADAILY = 'chinadaily'
CHINADAILY_EN = 'chinadaily_en'
RT = 'rt'
ALJ = 'alj'
ALJ_UP = 'alj_up'
BBC = 'bbc'

AUDIO_FILE_NAME = "summary_audio.mp3"

SUB_COUNT = 15

PROXY = {
    'http': 'http://127.0.0.1:10809',
    'https': 'http://127.0.0.1:10809',
}


@dataclass
class NewsArticle:
    def __init__(self,
                 title: str = None,
                 title_en: str = None,
                 images: List[str] = None,
                 video: str = None,
                 audio: str = None,
                 image_urls: List[str] = None,
                 video_url: str = None,
                 content_cn: str = None,
                 content_en: str = None,
                 folder: str = None,
                 index_inner: int = None,
                 index_show: int = None,
                 url: str = None,
                 source: str = None,
                 news_type: str = None,
                 publish_time: str = None,
                 author: str = None,
                 tags: List[str] = None,
                 summary: str = None,
                 show: bool = None):
        self.title = title
        self.title_en = title_en
        self.images = images or []
        self.video = video
        self.audio = audio
        self.image_urls = image_urls or []
        self.video_url = video_url
        self.content_cn = content_cn
        self.content_en = content_en
        self.folder = folder
        self.index_inner = index_inner
        self.index_show = index_show
        self.url = url
        self.source = source
        self.news_type = news_type
        self.publish_time = publish_time
        self.author = author
        self.tags = tags or []
        self.summary = summary
        self.show = show

    def to_dict(self):
        return self.__dict__


class NewsScraper:

    def __init__(self, source_url: str, source: str, news_type: str, sleep_time: int = 0):
        self.source_url = source_url
        self.source = source
        self.news_type = news_type
        self.sleep_time = sleep_time

    def do_crawl_news(self, today: datetime.now().strftime("%Y%m%d")):
        today_source_path = os.path.join(CN_NEWS_FOLDER_NAME, today, self.source)
        if not os.path.exists(today_source_path):
            self.crawling_news_meta(today)
        else:
            logger.info(f" {today_source_path} today_source_path had exists. ")
        logger.info(f"{self.source} 爬取完成。")

    @abstractmethod
    def extract_all_not_visit_urls(self, today: str):
        pass

    @abstractmethod
    def extract_news_content(self, today: str):
        pass

    def crawling_news_meta(self, today):
        folder_path = self.create_folder(today)
        today_source_path = os.path.join(CN_NEWS_FOLDER_NAME, today, self.source)
        urls = self.extract_all_not_visit_urls(today)
        month_urls = load_month_urls(today[:6])
        results = []
        if urls is None:
            logger.info(f" {self.source}无法获取初始页面内容，程序退出。")
            return results
        logger.info(f"{self.source} has  {len(urls)}  urls,now extract first {SUB_COUNT}")
        for idx, url in enumerate(urls[:SUB_COUNT]):
            if url in month_urls:
                logger.info(f" {self.source} 跳过本月已访问过的新闻: {url}")
                continue
            article = self.extract_news_content(url)
            if not article:
                logger.warning(f"无法获取新闻内容: {url}")
                continue
            article.folder = "{:04d}".format(idx)
            article.index_inner = idx
            article.index_show = idx
            if len(article.images) == 0:
                logger.warning(f"{article.source} 未找到图片: {url}")
                continue
            if article.title and self.is_sensitive_word_cn(article.title):
                logger.warning(f"{article.source} 标题包含敏感词: {url}")
                continue
            if article.content_cn and self.is_sensitive_word_cn(article.content_cn):
                logger.warning(f"{article.source} 中文内容包含敏感词: {url}")
                continue
            if article.title_en and self.is_sensitive_word_en(article.title_en):
                logger.warning(f"{article.title_en} 标题包含敏感词: {url}")
                continue
            if article.content_en and self.is_sensitive_word_en(article.content_en):
                logger.warning(f"{article.source} 英文内容包含敏感词: {url}")
                continue
            if article.content_cn and len(article.content_cn) < 8:
                logger.warning(f"{article.source} 内容过短: {url}")
                continue
            if not do_download_images(article, today_source_path):
                logger.info(f"图片下载失败: {url}")
                continue
            article.folder = "{:04d}".format(idx)
            results.append(article)
        logger.info(f"{self.source} ，脱敏，过滤后，共发现 {len(results)} 条新闻。")
        json_path = os.path.join(folder_path, NEWS_JSON_FILE_NAME)
        json_results = [i.to_dict() for i in results[:SUB_COUNT]]
        with open(json_path, "w", encoding="utf-8") as json_file:
            json.dump(json_results, json_file, ensure_ascii=False, indent=4)
        return results

    @abstractmethod
    def origin_url(self):
        pass

    def is_sensitive_word_cn(self, word) -> bool:
        cnt = 0
        sensitive_words = ["平", "%%%", "习", "县", "杀", "总书记", "近"]  # 去除了重复项
        for sensitive_word in sensitive_words:
            if sensitive_word in word:
                cnt += 1
        return cnt > 1

    def is_sensitive_word_en(self, word) -> bool:
        return "Jinping" in word

    def create_folder(self, today=datetime.now().strftime("%Y%m%d")) -> str:
        folder_path = os.path.join(CN_NEWS_FOLDER_NAME, today, self.source)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def fetch_page(self, url):
        try:
            if self.sleep_time > 0:
                randint = random.randint(self.sleep_time // 2, self.sleep_time)
                logger.info(f"{self.source} {url} sleep {randint} seconds start")
                time.sleep(randint)
                logger.info(f"{self.source} {url} sleep {randint} seconds done")
            ua = UserAgent()

            ua_random = ua.random
            headers = {"User-Agent": ua_random,
                       "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
                       "Connection": "keep-alive",
                       "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                       "Upgrade-Insecure-Requests": "1"
                       }

            response = requests.get(url, headers=headers, timeout=10, proxies=PROXY)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"fetch_page请求失败: {url} 错误信息： {e}")
            return None


class ChinaDailyScraper(NewsScraper):

    def origin_url(self) -> list[str]:
        return [
            'https://cn.chinadaily.com.cn/',
            'https://china.chinadaily.com.cn/',
            'https://world.chinadaily.com.cn/'
        ]

    def truncate_by_pos(self, text: str, end_pos: 700) -> str:
        if len(text) <= end_pos:
            return text
        last_period = text.find('。', end_pos)

        if last_period != -1:
            return text[:last_period + 1]
        else:
            return text

    def extract_news_content(self, url) -> NewsArticle | None:
        try:

            # 获取页面内容
            html = self.fetch_page(url)
            if not html:
                logger.warning(f'{url} not crawl anything', source={self.source})
                return None

            soup = BeautifulSoup(html, "html.parser")

            # 提取标题
            title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "无标题"
            # 提取正文图片
            image_urls = []
            article_div = soup.find("div", class_="Artical_Content")
            if article_div:
                for img in article_div.select("img"):
                    img_url = img.get("src")
                    if img_url and not img_url.startswith("data:"):
                        image_urls.append(urljoin(url, img_url))

            # 提取正文文本
            content = ""
            for p in soup.select("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 10:  # 过滤短文本
                    content += text + " "
            content = self.truncate_by_pos(content, 700)
            article = NewsArticle(source=self.source, news_type=self.news_type, show=True)
            article.title = title
            article.content_cn = content.strip()
            article.url = url
            article.image_urls = image_urls
            article.images = [os.path.basename(i) for i in image_urls]
            return article

        except Exception as e:
            logger.error(f"{url} {self.source} 提取新闻内容出错 : {e}", exc_info=True)
            return None

    def extract_links(self, html, visited_urls, today) -> set[str]:
        soup = BeautifulSoup(html, "html.parser")
        if today is None:
            today = datetime.now().strftime("%Y%m/%d")
        else:
            today = datetime.strptime(today, "%Y%m%d").strftime("%Y%m/%d")
        urls = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if today in href and href not in visited_urls:
                visited_urls.add(href)
                urls.add(href)
        return urls

    def extract_all_not_visit_urls(self, today):
        visited_urls = set()
        full_urls = []
        for base_url in self.origin_url():

            html = self.fetch_page(base_url)
            if not html:
                logger.info("无法获取初始页面内容，程序退出。")
                continue

            # 提取所有链接
            urls = self.extract_links(html, visited_urls, today)
            logger.info(f"{base_url} 共发现 {len(urls)} 个链接。")

        for url in visited_urls:
            if url.startswith("//"):
                full_urls.append("https:" + url)
            else:
                full_urls.append(url)
        logger.info(f"去重共发现 {len(visited_urls)} 个链接。")
        return full_urls


class ChinaDailyENScraper(ChinaDailyScraper):
    def origin_url(self) -> list[str]:
        return [
            'https://www.chinadaily.com.cn',
            'https://www.chinadaily.com.cn/world',
            'https://www.chinadaily.com.cn/business'
        ]

    def truncate_by_pos(self, text: str, end_pos: 4000) -> str:
        if len(text) <= end_pos:
            return text
        last_period = text.find('.', end_pos)

        if last_period != -1:
            return text[:last_period + 1]
        else:
            return text

    def extract_news_content(self, url) -> NewsArticle | None:
        try:

            # 获取页面内容
            html = self.fetch_page(url)
            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")

            # 提取标题
            title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "无标题"
            # 提取正文图片
            image_urls = []
            article_div = soup.select_one("div#Content")
            if article_div:
                for img in article_div.select("img"):
                    img_url = img.get("src")
                    if img_url and not img_url.startswith("data:"):
                        image_urls.append(urljoin(url, img_url))

            # 提取正文文本
            content = ""
            for p in soup.select("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 10:  # 过滤短文本
                    content += text + " "
            content = self.truncate_by_pos(content, 4000)
            article = NewsArticle(source=self.source, news_type=self.news_type, show=True)
            article.title_en = title
            article.content_en = content.strip()
            article.url = url
            article.image_urls = image_urls
            article.images = [os.path.basename(i) for i in image_urls]
            return article

        except Exception as e:
            logger.error(f"{self.source} {self.source} 提取新闻内容出错 : {e}", exc_info=True)
            return None


class BbcScraper(NewsScraper):

    def origin_url(self) -> list[str]:
        return [
            'https://www.bbc.com/news',
            'https://www.bbc.com/business',
            'https://www.bbc.com/innovation',
            'https://www.bbc.com/future-planet',
            'https://www.bbc.com'
        ]

    def extract_news_content(self, url) -> NewsArticle | None:
        try:
            # 获取页面内容
            html = self.fetch_page(url)
            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")

            # 提取标题
            title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "无标题"
            image_urls = []
            article_div_list = soup.find_all("div", attrs={'data-component': 'image-block'})
            if article_div_list:
                for article_div in article_div_list:
                    for img in article_div.select("img"):
                        srcset = img.get("srcset")
                        if not srcset:
                            continue
                        # 解析 srcset 并提取 (url, width) 元组
                        entries = srcset.strip().split(',')
                        image_data = []
                        for entry in entries:
                            entry = entry.strip()
                            # 正则匹配：提取 URL 和宽度（例如："url.webp 1024w" 提取为 ("url.webp", 1024)）
                            match = re.match(r'^(https?://[^ ]+) +(\d+)w$', entry)
                            if match:
                                img_url = match.group(1)
                                width = int(match.group(2))
                                image_data.append((img_url, width))
                        # 找到宽度最大的条目
                        if image_data:
                            max_width_entry = max(image_data, key=lambda x: x[1])
                            highest_res_url = max_width_entry[0]
                            image_urls.append(highest_res_url)
                        else:
                            logger.warning("未找到有效图片 URL")

            # 提取正文文本
            content = ""
            for p in soup.select("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 10:  # 过滤短文本
                    content += text + " "
            article = NewsArticle(source=self.source, news_type=self.news_type, show=True)
            article.title_en = title
            article.content_en = content.strip()
            article.url = url
            article.image_urls = image_urls
            article.images = [os.path.basename(i).replace(".webp", "") for i in image_urls]
            logger.info(f"{self.source} {title} 新闻内容提取找到了{len(article.images)}图片")
            return article

        except Exception as e:
            logger.error(f" {self.source} 提取新闻内容出错 : {e}", exc_info=True)
            return None

    def extract_links(self, html, visited_urls, today) -> set[str]:
        """解析 HTML，提取所有链接"""
        soup = BeautifulSoup(html, "html.parser")
        urls = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href not in visited_urls and '/live/' not in href and '/articles/' in href:
                visited_urls.add(href)
                urls.add(href)
        return urls

    def extract_all_not_visit_urls(self, today):
        # 初始爬取目标页面
        visited_urls = set()
        full_urls = []
        for base_url in self.origin_url():
            logger.info(f"正在{self.source}爬取 {base_url}")
            html = self.fetch_page(base_url)
            if not html:
                logger.info(f"无法获取初始{base_url}页面内容，切换。")
                continue

            # 提取所有链接
            urls = self.extract_links(html, visited_urls, today)
            logger.info(f"{base_url} 共发现 {len(urls)} 个链接。")

        for url in visited_urls:
            if "/articles" in url:
                full_urls.append("https://www.bbc.com" + url)
        logger.info(f" {self.source} 去重,拼接后共发现 {len(full_urls)} 个链接。")
        return full_urls


class ALJScraper(NewsScraper):

    def origin_url(self) -> list[str]:
        return [
            'https://www.aljazeera.com/',
            'https://www.aljazeera.com/us-canada/',
            'https://www.aljazeera.com/asia-pacific/',
        ]

    def extract_news_content(self, url) -> NewsArticle | None:
        try:
            # 获取页面内容
            html = self.fetch_page(url)
            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")

            # 提取标题
            title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "无标题"
            # 提取正文图片
            image_urls = []
            main = soup.find("main", attrs={'id': 'main-content-area'})
            if main:
                for img in main.select("img"):
                    src_set = img.get("srcset")
                    if not src_set:
                        continue
                    entries = src_set.strip().split(',')
                    img_url = entries[-1].split(' ')[1]
                    image_urls.append(urljoin(url, img_url))

            # 提取正文文本
            content = ""
            for p in main.select("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 10:  # 过滤短文本
                    content += text + " "
            article = NewsArticle(source=self.source, news_type=self.news_type, show=True)
            article.title_en = title
            article.content_en = content.strip()
            article.url = url
            article.image_urls = image_urls
            article.images = [os.path.basename(i).split('?')[0] for i in image_urls]
            return article

        except Exception as e:
            logger.error(f" {self.source} 提取新闻内容出错 : {e}", exc_info=True)
            return None

    def extract_links(self, html, visited_urls, today) -> set[str]:
        soup = BeautifulSoup(html, "html.parser")
        if today is None:
            today = datetime.now().strftime("%Y%m/%d")
        else:
            today = datetime.strptime(today, "%Y%m%d").strftime("%Y/%-m/%-d")
        urls = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if today in href and href not in visited_urls:
                visited_urls.add(href)
                urls.add(href)
        return urls

    def extract_all_not_visit_urls(self, today):
        # 初始爬取目标页面
        visited_urls = set()
        full_urls = []
        for base_url in self.origin_url():
            logger.info(f"正在{self.source}爬取 {base_url}")
            html = self.fetch_page(base_url)
            if not html:
                logger.info(f"无法获取初始{base_url}页面内容，切换。")
                continue

            # 提取所有链接
            urls = self.extract_links(html, visited_urls, today)
            logger.info(f"{base_url} 共发现 {len(urls)} 个链接。")

        for url in visited_urls:
            if '/liveblog' not in url:
                full_urls.append("https://www.aljazeera.com" + url)
        logger.info(f" {self.source} 去重,拼接后共发现 {len(full_urls)} 个链接。")
        return full_urls


def do_download_images(article, today_path):
    folder = article.folder
    img_folder_path = os.path.join(today_path, folder)
    os.makedirs(img_folder_path, exist_ok=True)
    cnt = 0
    for image_name, image_url in zip(article.images, article.image_urls):
        image_path = os.path.join(img_folder_path, image_name)
        if not os.path.exists(image_path):
            try:
                ua = UserAgent()
                ua_random = ua.random
                headers = {"User-Agent": ua_random,
                           "Accept-Language": "en-US,en;q=0.9", "DNT": "1",
                           "Connection": "keep-alive",
                           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                           "Upgrade-Insecure-Requests": "1"
                           }
                response = requests.get(image_url, headers=headers, timeout=7, proxies=PROXY)
                response.raise_for_status()
                with open(image_path, "wb") as image_file:
                    image_file.write(response.content)
                cnt += 1
            except requests.RequestException as e:
                logger.error(f"下载图片失败: {image_url} - {e}")
    images_done = cnt == len(article.images)
    if not images_done:
        logger.info(f'应该下载{len(article.images)}，实际下载了 {cnt} 张图片')
    return images_done


class RTScraper(NewsScraper):

    def origin_url(self) -> list[str]:
        return [
            'https://www.rt.com/',
            'https://www.rt.com/news/'
        ]

    def extract_news_content(self, url) -> NewsArticle | None:
        try:
            # 获取页面内容
            html = self.fetch_page(url)
            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")

            # 提取标题
            title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "无标题"
            # 提取正文图片
            image_urls = []
            main = soup.find("div", attrs={'class': 'article'})
            if main:
                src_set = main.select('picture')[0].select('source')[1].get('data-srcset').split(',')[-1]
                if src_set:
                    strip = src_set.strip()
                    image_urls.append(urljoin(url, strip.split(' ')[0]))
            # 提取正文文本
            content = ""
            for p in main.select("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 10:  # 过滤短文本
                    content += text + " "
            article = NewsArticle(source=self.source, news_type=self.news_type, show=True)
            article.title_en = title
            article.content_en = content.strip()
            article.url = url
            article.image_urls = image_urls
            article.images = [os.path.basename(i).split('?')[0] for i in image_urls]
            return article

        except Exception as e:
            logger.error(f" {self.source} 提取新闻{url}内容出错 : {e}", exc_info=True)
            return None

    def extract_links(self, html, visited_urls, today) -> set[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href not in visited_urls and ('/news/' in href or '/russia/' in href):
                visited_urls.add(href)
                urls.add(href)
        return urls

    def extract_all_not_visit_urls(self, today):
        # 初始爬取目标页面
        visited_urls = set()
        full_urls = []
        for base_url in self.origin_url():
            logger.info(f"正在{self.source}爬取 {base_url}")
            html = self.fetch_page(base_url)
            if not html:
                logger.info(f"无法获取初始{base_url}页面内容，切换。")
                continue

            # 提取所有链接
            urls = self.extract_links(html, visited_urls, today)
            logger.info(f"{base_url} 共发现 {len(urls)} 个链接。")

        for url in visited_urls:
            if 'http' in url:
                full_urls.append(url)
            else:
                full_urls.append("https://www.rt.com" + url)
        logger.info(f" {self.source} 去重,拼接后共发现 {len(full_urls)} 个链接。")
        return full_urls


def is_english_char(char):
    # 判断字符是否为英文字母
    return char.isalpha() and (char.lower() in 'abcdefghijklmnopqrstuvwxyz')


def check_english_percentage(text):
    total_chars = len(text)
    if total_chars == 0:
        return 0  # 避免除以零的情况
    english_count = sum(1 for char in text if is_english_char(char))
    return (english_count / total_chars) > 0.4


def load_and_summarize_news(json_file_path: str) -> List[NewsArticle]:
    """
    加载新闻数据，提取中文摘要，并翻译英文内容为中文。
    :param json_file_path: JSON 文件路径
    :return: 包含摘要和翻译后内容的 NewsArticle 列表
    """

    # 初始化 Ollama 客户端
    ollama_client = OllamaClient()

    # 加载 JSON 文件
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        news_data = json.load(json_file)

    # 处理每条新闻
    processed_news = []
    for news_item in news_data:
        article = NewsArticle(**news_item)

        if article.title_en:
            article.title = ollama_client.translate_to_chinese(text=article.title_en)
        # if article.title and not article.title_en:
        #     article.title_en = ollama_client.translate_to_english(text=article.title)

        # 提取中文摘要
        if article.content_cn:
            article.summary = ollama_client.generate_summary(article.content_cn, max_tokens=150)
        if article.content_en:
            article.summary = ollama_client.generate_summary_cn(article.content_en, max_tokens=150)
        if check_english_percentage(article.summary):
            article.show = False
            logger.warning(f"{article.url} - {article.title} - all is english")
        if '版权声明' in article.summary and '授权' in article.summary:
            article.show = False
            logger.warning(f"{article.url} - {article.title} - not crawl full content")
        logger.info(f"{article.url} - {article.title} - 补充完成")
        processed_news.append(article)
    return processed_news


def load_json_by_source(source, today):
    folder_path = os.path.join(CN_NEWS_FOLDER_NAME, today, source)
    json_file_path = os.path.join(folder_path, PROCESSED_NEWS_JSON_FILE_NAME)
    if not os.path.exists(json_file_path):
        logger.info(f"{source}新闻json文件不存在,path={json_file_path}")
        return json_file_path, None
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        news_data = json.load(json_file)
    logger.info(f"{source}新闻json文{json_file_path}件加载成功,news_data={len(news_data)}")
    return json_file_path, news_data


def process_news_results(source: str, today: str = datetime.now().strftime("%Y%m%d")) -> List[NewsArticle]:
    """
    处理指定日期的新闻结果文件，提取摘要并翻译内容。

    :param today: 日期字符串，格式为 YYYYMMDD
    """
    logger.info(f"开始处理 {source} 的新闻结果文件...")
    folder_path = os.path.join(CN_NEWS_FOLDER_NAME, today, source)
    json_file_path = os.path.join(folder_path, NEWS_JSON_FILE_NAME)
    if os.path.exists(json_file_path):
        processed_json_path = os.path.join(folder_path, PROCESSED_NEWS_JSON_FILE_NAME)
        if os.path.exists(processed_json_path):
            logger.info(f"{processed_json_path}已存在处理后的新闻结果文件，跳过处理,直接返回")
            _, data = load_json_by_source(source, today)
            return [NewsArticle(**i) for i in data]
        processed_news = load_and_summarize_news(json_file_path)

        with open(processed_json_path, 'w', encoding='utf-8') as json_file:
            json.dump([article.to_dict() for article in processed_news], json_file, ensure_ascii=False, indent=4)

        logger.info(f"处理完成，已保存到 {processed_json_path}")
        return processed_news
    else:
        logger.info(f"未找到新闻结果文件: {json_file_path}")
    logger.info(f"处理 {source} 的新闻结果文件完成")


def generate_all_news_audio(source: str, today: str = datetime.now().strftime("%Y%m%d")) -> None:
    folder_path = os.path.join(CN_NEWS_FOLDER_NAME, today, source)
    json_file_path = os.path.join(folder_path, PROCESSED_NEWS_JSON_FILE_NAME)
    if not os.path.exists(json_file_path):
        logger.warning(f"{json_file_path}不存在，跳过生成音频。")
        return
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        news_data = json.load(json_file)

    for news_item in news_data:
        article = NewsArticle(**news_item)

        # 新增逻辑：将摘要转换为音频并保存
        folder_path = os.path.dirname(json_file_path)  # 获取新闻图片所在的文件夹路径
        audio_output_path = os.path.join(folder_path, article.folder, "%s" % AUDIO_FILE_NAME)
        generate_audio(article.summary, output_file=audio_output_path)


def generate_audio(text: str, output_file: str = "audio.wav", rewrite=False) -> None:
    if os.path.exists(output_file) and not rewrite:
        logger.info(f"{output_file}已存在，跳过生成音频。")
        return
    logger.info(f"{output_file}开始生成音频: {text}")
    rate = 70
    sh = f'edge-tts --voice zh-CN-XiaoxiaoNeural --text "{text}" --write-media {output_file} --rate="+{rate}%"'
    os.system(sh)


import time


def auto_download_daily(today=datetime.now().strftime("%Y%m%d")):
    logger.info("开始爬取新闻")
    start = time.time()
    rt = RTScraper(source_url='https://www.rt.com/', source=RT, news_type='今日俄罗斯',
                   sleep_time=4)
    en = ChinaDailyENScraper(source_url='https://www.chinadaily.com.cn', source=CHINADAILY_EN, news_type='中国日报',
                             sleep_time=4)
    al = ALJScraper(source_url='https://www.aljazeera.com/', source=ALJ, news_type='中东半岛新闻',
                    sleep_time=20)
    bbc = BbcScraper(source_url='https://www.bbc.com', source=BBC, news_type='BBC',
                     sleep_time=20)

    bbc.do_crawl_news(today)
    al.do_crawl_news(today)
    rt.do_crawl_news(today)
    en.do_crawl_news(today)
    end = time.time()
    logger.info(f"爬取新闻耗时: {end - start:.2f} 秒")

    logger.info("开始AI生成摘要")
    start = time.time()
    bbc_articles = process_news_results(source=BBC, today=today)
    rt_articles = process_news_results(source=RT, today=today)
    en_articles = process_news_results(source=CHINADAILY_EN, today=today)
    al_articles = process_news_results(source=ALJ, today=today)
    end = time.time()
    logger.info(f"AI生成摘要耗时: {end - start:.2f} 秒")
    build_new_articles_json(today, rt_articles, al_articles, bbc_articles, en_articles)

    logger.info("开始生成音频")
    start = time.time()
    for i in [BBC, ALJ, RT, CHINADAILY_EN]:
        generate_all_news_audio(source=i, today=today)
    end = time.time()
    logger.info(f"生成音频耗时: {end - start:.2f} 秒")


def build_new_articles_path(today=datetime.now().strftime("%Y%m%d"), times_tag=0):
    path = os.path.join(CN_NEWS_FOLDER_NAME, today, 'new_articles' + str(times_tag) + '.json')
    logger.info(f" new_articles_path = {path}")
    return path


def build_new_articles_uploaded_path(today=datetime.now().strftime("%Y%m%d"), times_tag=1):
    path = os.path.join(CN_NEWS_FOLDER_NAME, today, 'new_articles_uploaded' + str(times_tag) + '.json')
    logger.info(f" new_articles_path_uploaded = {path}")
    return path


def build_new_articles_json(today, rt_articles, al_articles, bbc_articles, en_articles):
    def reset_article_attributes(article):
        article.content_en = ''
        article.content_cn = ''

    new_articles = []
    idx = 1
    for article in rt_articles:
        reset_article_attributes(article)
        article.index_inner = idx
        idx += 1
        new_articles.append(article)
    for article in bbc_articles:
        reset_article_attributes(article)
        article.index_inner = idx
        idx += 1
        new_articles.append(article)
    for article in al_articles:
        reset_article_attributes(article)
        article.index_inner = idx
        idx += 1
        new_articles.append(article)
    for article in en_articles:
        reset_article_attributes(article)
        article.index_inner = idx
        idx += 1
        new_articles.append(article)
    path = build_new_articles_path(today,TIMES_TAG)
    with open(path, 'w', encoding='utf-8') as json_file:
        json.dump([article.to_dict() for article in new_articles], json_file, ensure_ascii=False, indent=4)
    logger.info(f"生成new_articles.json{TIMES_TAG}成功,path={path}")


def build_today_json_path(today=datetime.now().strftime("%Y%m%d")):
    return os.path.join(CN_NEWS_FOLDER_NAME, today, "all.json")


def get_today_morning_urls(today=datetime.now().strftime("%Y%m%d")):
    json_path = build_today_json_path(today=today)
    if not os.path.exists(json_path):
        logger.warning(f"{json_path}不存在，请先执行爬取新闻任务")
        return []
    json_data = json.load(open(json_path, 'r', encoding='utf-8'))
    return json_data['urls']


def load_month_urls(year_month: str) -> set:
    """
    加载指定年月的已访问 URL 集合，并在追加新 URL 时写回文件。

    :param year_month: 年月字符串，格式为 YYYYMM
    :return: 包含已访问 URL 的集合
    """
    json_file_path = f"{year_month}_visited_urls.json"
    urls_set = set()

    # 尝试加载已存在的 JSON 文件
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            urls_set = set(json.load(json_file))
    logger.info(f"已加载 {year_month} 的已访问 URL{len(urls_set)}个")
    return urls_set


def append_and_save_month_urls(year_month: str, new_urls: set) -> None:
    """
    向指定年月的已访问 URL 集合中追加新 URL，并保存到 JSON 文件。

    :param year_month: 年月字符串，格式为 YYYYMM
    :param new_urls: 要追加的新 URL 集合
    """
    json_file_path = f"{year_month}_visited_urls.json"
    existing_urls = load_month_urls(year_month)
    updated_urls = existing_urls.union(new_urls)

    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(list(updated_urls), json_file, ensure_ascii=False, indent=4)
    logger.info(f"已保存 {year_month} 的已访问URL {len(new_urls)} 个到 {json_file_path}")


def test_alj():
    cs = RTScraper(source_url='https://www.rt.com/', source=RT, news_type='国际新闻',
                   sleep_time=0)
    cs.do_crawl_news(today="20250601")

    logger.info("============")




import argparse

if __name__ == "__main__":
    logger.info('========================start crawl==============================')
    start = time.time()
    parser = argparse.ArgumentParser(description="新闻爬取和处理工具")
    parser.add_argument("--today", type=str, default=datetime.now().strftime("%Y%m%d"), help="指定日期")
    parser.add_argument("--times", type=int, default=0, help="执行次数")
    parser.add_argument("--rewrite", type=bool, default=False, help="是否重写")
    args = parser.parse_args()
    logger.info(f"新闻爬取和处理工具 args={args}")
    TIMES_TAG = args.times
    logger.info(f"新闻爬取和处理工具 运行第{TIMES_TAG}次")
    CHINADAILY_EN = CHINADAILY_EN + str(TIMES_TAG)
    CHINADAILY = CHINADAILY + str(TIMES_TAG)
    ALJ = ALJ + str(TIMES_TAG)
    BBC = BBC + str(TIMES_TAG)
    RT = RT + str(TIMES_TAG)
    try:
        auto_download_daily(today=args.today)
    except  Exception as e:
        logger.error(f"auto_download_daily error:{e}")
    logger.info(f"========================end crawl==========time spend = {time.time() - start:.2f} second")
