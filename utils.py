import os
import sys
import json
from datetime import datetime
from logging_config import logger
from dataclasses import dataclass
from typing import List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

NEWS_JSON_FILE_NAME = "news_results.json"
NEWS_JSON_FILE_NAME_PROCESSED = "news_results_processed.json"
NEWS_FOLDER_NAME = "news"
FINAL_VIDEOS_FOLDER_NAME = "final_videos"
AUDIO_FILE_NAME = "summary_audio.mp3"
SUB_LIST_LENGTH = 7

RT = "rt"
ALJ = "rlj"
BBC = "bbc"
CHINADAILY_EN = "c_en"

PROXY = {
    'http': 'http://127.0.0.1:10809',
    'https': 'http://127.0.0.1:10809',
}

BACKGROUND_IMAGE_PATH = "videos/generated_background.png"
BACKGROUND_IMAGE_INNER_PATH = "videos/generated_background_inner.png"
GLOBAL_WIDTH = 1920
GLOBAL_HEIGHT = 1080
GAP = int(GLOBAL_WIDTH * 0.02)
INNER_WIDTH = GLOBAL_WIDTH - GAP
INNER_HEIGHT = GLOBAL_HEIGHT - GAP
W_H_RADIO = GLOBAL_WIDTH / GLOBAL_HEIGHT
W_H_RADIO = "{:.2f}".format(W_H_RADIO)
FPS = 65
MAIN_BG_COLOR = "#FF9900"
VIDEO_FILE_NAME = "final.mp4"

REWRITE = False

TIMES_TYPE = {
    0: '晨间全球快讯',
    1: '午间全球快讯',
    2: '晚间全球快讯',
    3: '深夜全球快讯'
}
import threading
lock = threading.RLock()
HINT_INFORMATION = """信息来源:[中国日报国际版] [中东半岛电视台] [英国广播公司] [今日俄罗斯电视台]"""
TAGS = """#新闻 #每日新闻 #热点新闻 #信息差"""


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
                 times: int = 0,
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
        self.times = times
        self.show = show

    def to_dict(self):
        return self.__dict__


def build_introduction_path(today=datetime.now().strftime("%Y%m%d"), time_tag: int = 0):
    return os.path.join(NEWS_FOLDER_NAME, today, str(time_tag) + "introduction.mp4")


def build_date_path(today=datetime.now().strftime("%Y%m%d")):
    return os.path.join(NEWS_FOLDER_NAME, today)


def build_end_path(time_tag):
    return os.path.join(NEWS_FOLDER_NAME, str(time_tag)+"end.mp4")


def build_daily_text_path(today=datetime.now().strftime("%Y%m%d")):
    return os.path.join(FINAL_VIDEOS_FOLDER_NAME, today + "all.text")


def build_introduction_audio_path(today=datetime.now().strftime("%Y%m%d"), time_tag: int = 0):
    return os.path.join(NEWS_FOLDER_NAME, today, str(time_tag) + "introduction.mp3")


def build_end_audio_path():
    return os.path.join(NEWS_FOLDER_NAME, "end.mp3")


def build_announcer_path(time_tag: int = 0):
    announcer_map = {
        0: 'lady_announcer.mp4',
        1: 'lady_announcer.mp4',
        2: 'lady_announcer.mp4',
        3: 'lady_announcer.mp4'
    }
    return os.path.join('videos', announcer_map[time_tag])


# 将 HEX 转换为 RGB 的小函数
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')  # 去掉 #
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def build_bg_color_hex(time_tag: int = 0):
    announcer_map = {
        0: '#FCFEFE',
        1: '#FCFEFE',
        2: '#FCFEFE',
        3: '#FCFEFE'
    }
    hex = announcer_map[time_tag]
    logger.info(f" {time_tag} build_bg_color_hex: {hex}")
    return hex


def build_bg_color_rgb(time_tag: int = 0):
    rgb = hex_to_rgb(build_bg_color_hex(time_tag))
    logger.info(f" {time_tag} build_bg_color_rgb: {rgb}")
    return rgb


def build_final_video_path(today=datetime.now().strftime("%Y%m%d"), time_tag: int = 0):
    return os.path.join(FINAL_VIDEOS_FOLDER_NAME, today + "_" + str(time_tag) + "_" + VIDEO_FILE_NAME)


def build_final_video_walk_path(today=datetime.now().strftime("%Y%m%d"), time_tag: int = 0):
    return os.path.join(FINAL_VIDEOS_FOLDER_NAME, today + "_" + str(time_tag) + "_walk_" + VIDEO_FILE_NAME)


def build_today_bg_music_path():
    return os.path.join(NEWS_FOLDER_NAME, "bg_music.mp4")


def build_articles_json_path(today=datetime.now().strftime("%Y%m%d"), time_tag=0):
    path = os.path.join(NEWS_FOLDER_NAME, today, 'new_articles_' + str(time_tag) + '.json')
    logger.info(f" new_articles_path = {path}")
    return path


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


def generate_audio(text: str, output_file: str = "audio.wav", rewrite=False, time_tag: int = 0) -> None:
    if os.path.exists(output_file) and not rewrite:
        logger.info(f"{output_file}已存在，跳过生成音频。")
        return
    with lock:
        logger.info(f"time_tag={time_tag} output_file={output_file} 开始生成音频: {text}")
        rate = 75
        announcer_map = {
            0: 'zh-CN-XiaoxiaoNeural',
            1: 'zh-CN-XiaoxiaoNeural',
            2: 'zh-CN-XiaoxiaoNeural',
            3: 'zh-CN-XiaoxiaoNeural'
        }
        sh = f'edge-tts --voice {announcer_map[time_tag]} --text "{text}" --write-media {output_file} --rate="+{rate}%"'
        logger.info(f"sh={sh}")
        os.system(sh)


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


def remove_outdated_documents():
    import shutil
    from datetime import datetime, timedelta

    # 获取当前日期和时间
    current_date = datetime.now()
    # 计算10天前的日期
    days_ago = current_date - timedelta(days=2)
    strftime = days_ago.strftime("%Y%m%d")
    logger.info(f'start to remove outdated documents:  {strftime} ')
    folder_path = build_date_path(strftime)

    try:
        shutil.rmtree(folder_path)
        logger.info(f"文件夹 '{folder_path}' 删除成功！")
    except FileNotFoundError:
        logger.info(f"文件夹 '{folder_path}' 不存在")
    except PermissionError:
        logger.info(f"无权限删除文件夹 '{folder_path}'")
    except Exception as e:
        logger.info(f"删除文件夹时发生错误: {e}")

    for filename in os.listdir(FINAL_VIDEOS_FOLDER_NAME):
        file_path = os.path.join(folder_path, filename)

        # 检查是否是文件且文件名以 'a' 开头
        if os.path.isfile(file_path) and filename.startswith(strftime):
            try:
                os.remove(file_path)
                print(f"已删除文件: {file_path}")
            except Exception as e:
                print(f"删除文件 {file_path} 失败: {e}")
