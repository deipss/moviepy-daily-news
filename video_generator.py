from moviepy import *
from PIL import ImageDraw
from datetime import datetime
import json
from zhdate import ZhDate
import os
import math
from PIL import Image
from moviepy.video.fx import Loop
from crawl_news import *
from ollama_client import OllamaClient
from logging_config import logger
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

BACKGROUND_IMAGE_PATH = "videos/generated_background.png"
GLOBAL_WIDTH = 1920
GLOBAL_HEIGHT = 1080
GAP = int(GLOBAL_WIDTH * 0.02)
INNER_WIDTH = GLOBAL_WIDTH - GAP
INNER_HEIGHT = GLOBAL_HEIGHT - GAP
W_H_RADIO = GLOBAL_WIDTH / GLOBAL_HEIGHT
W_H_RADIO = "{:.2f}".format(W_H_RADIO)
FPS = 40
MAIN_BG_COLOR = "#FF9900"
VIDEO_FILE_NAME = "video.mp4"

import time

REWRITE = False
EVENING = False

hint_information = """信息来源: 
1. chinadaily.com.cn [中国日报国际版] 
2. https://www.aljazeera.com [中东半岛电视台]
3. https://www.bbc.com [英国广播公司] 
4. https://www.rt.com/ [今日俄罗斯电视台]"""


def build_today_introduction_path(today=datetime.now().strftime("%Y%m%d")):
    if EVENING:
        return os.path.join(CN_NEWS_FOLDER_NAME, today, "introduction_evening.mp4")
    return os.path.join(CN_NEWS_FOLDER_NAME, today, "introduction.mp4")


def build_end_path():
    return os.path.join(CN_NEWS_FOLDER_NAME, "end.mp4")


def build_today_json_path(today=datetime.now().strftime("%Y%m%d")):
    return os.path.join(CN_NEWS_FOLDER_NAME, today, "all.json")


def build_today_introduction_audio_path(today=datetime.now().strftime("%Y%m%d")):
    if EVENING:
        return os.path.join(CN_NEWS_FOLDER_NAME, today, "introduction_evening.mp3")
    return os.path.join(CN_NEWS_FOLDER_NAME, today, "introduction.mp3")


def build_today_end_audio_path():
    return os.path.join(CN_NEWS_FOLDER_NAME, "end.mp3")


def build_today_final_video_path(today=datetime.now().strftime("%Y%m%d")):
    if EVENING:
        return os.path.join(FINAL_VIDEOS_FOLDER_NAME, today + "_" + EVENING_TAG + "_" + VIDEO_FILE_NAME)
    return os.path.join(FINAL_VIDEOS_FOLDER_NAME, today + "_" + VIDEO_FILE_NAME)


def build_today_bg_music_path():
    return os.path.join(CN_NEWS_FOLDER_NAME, "bg_music.mp4")


def generate_background_image(width=GLOBAL_WIDTH, height=GLOBAL_HEIGHT, color=MAIN_BG_COLOR):
    # 创建一个新的图像
    image = Image.new("RGB", (width, height), color)  # 橘色背景
    draw = ImageDraw.Draw(image)

    # 计算边框宽度(1%的宽度)
    border_width = GAP * 1.5

    # 绘制圆角矩形(内部灰白色)
    draw.rounded_rectangle(
        [(border_width, border_width), (width - border_width, height - border_width)],
        radius=40,  # 圆角半径
        fill="#FCFEFE"  # 灰白色填充
    )

    image.save(BACKGROUND_IMAGE_PATH)
    return image


def add_newline_every_n_chars(text, n):
    if n <= 0:
        return text

    return '\n'.join([text[i:i + n] for i in range(0, len(text), n)])


def calculate_font_size_and_line_length(text, box_width, box_height, font_ratio=1.0, line_height_ratio=1.5,
                                        start_size=72):
    # 从最大字体开始尝试，逐步减小直到文本适应文本框
    for font_size in range(start_size, 0, -1):
        # 计算每个字符的平均宽度和行高
        char_width = font_size * font_ratio
        line_height = font_size * line_height_ratio

        # 计算每行可容纳的字符数
        chars_per_line = max(1, math.floor(box_width / char_width))

        # 计算所需的总行数
        total_lines = math.ceil(len(text) / chars_per_line)

        # 计算所需的总高度
        total_height = total_lines * line_height

        # 如果高度符合要求，返回当前字体大小和每行字符数
        if total_height <= box_height:
            return font_size, chars_per_line

    return 40, len(text)


def truncate_after_find_period(text: str, end_pos: int = 400) -> str:
    if len(text) <= end_pos:
        return text
    # 从end_pos位置开始向后查找第一个句号
    last_period = text.find('。', end_pos)

    if last_period != -1:
        # 截取至句号位置（包含句号）
        return text[:last_period + 1]
    else:
        # 300字符后无句号，返回全文（或截断并添加省略号）
        return text  # 或返回 text[:end_pos] + "..."（按需选择）


def calculate_segment_times(duration, num_segments):
    segment_duration = duration / num_segments
    segment_times = []
    for i in range(num_segments):
        start_time = i * segment_duration
        end_time = (i + 1) * segment_duration
        segment_times.append((start_time, end_time))
    return segment_times


def generate_three_layout_video(audio_path, image_list, title, summary, output_path, index, is_preview=False):
    title = "" + index + " " + title
    # 加载背景和音频
    bg_clip = ColorClip(size=(INNER_WIDTH, INNER_HEIGHT), color=(252, 254, 254))  # 白色背景
    try:
        audio_clip = AudioFileClip(audio_path)
    except IOError as e:
        logger.error(f"音频文件加载失败，{audio_path}", e)
        return False
    duration = audio_clip.duration
    if duration < 2:
        logger.warning(f"{title} 音频文件时长过短，请检查音频文件{audio_path}")
        return False
    bg_clip = bg_clip.with_duration(duration).with_audio(audio_clip)
    bg_width, bg_height = bg_clip.size

    # 计算各区域尺寸
    title_height = 40
    HEIGHT_RATIO = 0.75
    top_height = int((bg_height - title_height) * HEIGHT_RATIO)
    bottom_height = bg_height - top_height - title_height

    bottom_right_width = int(bg_width * 0.2)
    bottom_left_width = bg_width - bottom_right_width

    bottom_right_img = VideoFileClip('videos/lady_announcer.mp4').with_effects([Loop(duration=duration)])
    if bottom_right_img.w > bottom_right_width or bottom_right_img.h > bottom_height:
        scale = min(bottom_right_width / bottom_right_img.w, bottom_height / bottom_right_img.h)
        bottom_right_img = bottom_right_img.resized(scale)
    bottom_right_img = bottom_right_img.with_position(('right', 'bottom')).with_duration(duration)

    # 左上图片处理
    segment_times = calculate_segment_times(duration, len(image_list))
    image_clip_list = []
    for image_path_top, (s, e) in zip(image_list, segment_times):
        top_left_img = ImageClip(image_path_top)
        scale = min(bg_width / top_left_img.w, top_height / top_left_img.h)
        top_left_img = top_left_img.resized(scale)
        offset_w, offest_h = (bg_width - top_left_img.w) // 2, (top_height - top_left_img.h) // 2
        top_left_img = top_left_img.with_position((offset_w, offest_h + title_height)).with_start(s).with_duration(
            e - s)
        image_clip_list.append(top_left_img)

    # 左下文字处理
    font_size, chars_per_line = calculate_font_size_and_line_length(summary, bottom_left_width * 95 / 100,
                                                                    bottom_height * 95 / 100)
    summary = '\n'.join([summary[i:i + chars_per_line] for i in range(0, len(summary), chars_per_line)])
    bottom_left_txt = TextClip(
        text=summary,
        interline=font_size // 2,
        font_size=font_size,
        color='black',
        font='./font/simhei.ttf',
        text_align='center',
        size=(bottom_left_width, bottom_height),
        method='caption'
    ).with_duration(duration).with_position(('left', top_height + title_height))

    # 标题
    title_font_size = 40
    top_title = TextClip(
        interline=title_font_size // 2,
        text=title,
        font_size=title_font_size,
        color='black',
        font='./font/simhei.ttf',
        method='label'
    ).with_duration(duration).with_position(('left', 'top'))

    # 创建各区域背景框

    # 合成最终视频
    image_clip_list.insert(0, bg_clip)
    image_clip_list.insert(1, bottom_left_txt)
    image_clip_list.insert(2, bottom_right_img)
    image_clip_list.insert(3, top_title)
    final_video = CompositeVideoClip(clips=image_clip_list, size=(bg_width, bg_height))
    if is_preview:
        final_video.preview()
    else:
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=FPS)
    return True


def get_full_date(today=datetime.now()):
    """获取完整的日期信息：公历日期、农历日期和星期"""

    # 获取公历日期
    solar_date = today.strftime("%Y年%m月%d日")

    # 获取农历日期
    lunar_date = ZhDate.from_datetime(today).chinese()

    # 获取星期几
    weekday_map = ["一", "二", "三", "四", "五", "六", "日"]
    weekday = f"星期{weekday_map[today.weekday()]}"
    if EVENING:
        return "今天是{}, \n农历{}, \n{},欢迎收看晚间【今日快电】".format(solar_date, lunar_date, weekday)
    return "今天是{}, \n农历{}, \n{},欢迎收看【今日快电】".format(solar_date, lunar_date, weekday)


def get_weekday_color():
    # 星期与颜色的映射关系 (0 = Monday, 6 = Sunday)
    weekday_color_map = {
        0: 'Red',  # 周一 - 红色
        1: 'Orange',  # 周二 - 橙色
        2: 'Yellow',  # 周三 - 黄色
        3: 'Green',  # 周四 - 绿色
        4: 'Blue',  # 周五 - 蓝色
        5: 'Purple',  # 周六 - 紫色
        6: 'Pink'  # 周日 - 粉色
    }

    # 获取当前星期几 (0=Monday, 6=Sunday)
    weekday = datetime.today().weekday()

    # 返回对应颜色
    return weekday_color_map[weekday]


def generate_video_introduction(output_path='temp/introduction.mp4', today=datetime.now().strftime("%Y%m%d"),
                                is_preview=False):
    """生成带日期文字和背景音乐的片头视频

    Args:
        bg_music_path: 背景音乐文件路径
        output_path: 输出视频路径
    """
    generate_background_image(GLOBAL_WIDTH, GLOBAL_HEIGHT)
    if os.path.exists(output_path) and not REWRITE:
        logger.info(f"片头{output_path}已存在,直接返回")
        return generate_top_topic_by_ollama(today), 0
        # 加载背景图片
    bg_clip = ImageClip(BACKGROUND_IMAGE_PATH)

    # 加载背景音乐
    date_obj = datetime.strptime(today, "%Y%m%d")
    date_text = get_full_date(date_obj)
    audio_path = build_today_introduction_audio_path(today)
    generate_audio(date_text, audio_path, rewrite=True)
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration

    # 设置背景视频时长
    bg_clip = bg_clip.with_duration(duration).with_audio(audio_clip)

    # 创建日期文字

    date_parts = date_text.split('\n')
    max_length = max(len(part) for part in date_parts) if date_parts else len(date_text)

    txt_clip = TextClip(
        text=date_text,
        font_size=int(GLOBAL_WIDTH / max_length * 0.75),
        color=MAIN_BG_COLOR,
        font='./font/simhei.ttf',
        stroke_color='black',
        stroke_width=2
    ).with_duration(duration).with_position((GAP * 1.75, GLOBAL_HEIGHT * 0.7))

    topics = generate_top_topic_by_ollama(today)
    logger.info(f"generate introduction topics=\n{topics}")
    topic_txt_clip = TextClip(
        text=topics,
        font_size=int(GLOBAL_HEIGHT * 0.75 / 5 * 0.6),
        color=get_weekday_color(),
        interline=int(GLOBAL_HEIGHT * 0.75 / 5 * 0.6) // 4,
        font='./font/simhei.ttf',
        stroke_color=MAIN_BG_COLOR,
        stroke_width=3
    ).with_duration(duration).with_position((GAP * 1.75, GLOBAL_HEIGHT * 0.1))

    lady = (VideoFileClip('videos/lady_announcer.mp4').with_effects([Loop(duration=duration)])
            .with_position((GLOBAL_WIDTH * 0.68, GLOBAL_HEIGHT * 0.47)).resized(0.7))

    # 合成最终视频
    final_clip = CompositeVideoClip([bg_clip, txt_clip, lady, topic_txt_clip], size=bg_clip.size)
    if is_preview:
        final_clip.preview()
    else:
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=FPS)
    return topics, duration


def generate_video_end(is_preview=False):
    output_path = build_end_path()
    if os.path.exists(output_path) and not REWRITE:
        logger.info(f"片尾{output_path}已存在,直接返回")
    generate_background_image(GLOBAL_WIDTH, GLOBAL_HEIGHT)
    bg_clip = ImageClip(BACKGROUND_IMAGE_PATH)
    audio_path = build_today_end_audio_path()

    generate_audio("今天的信息，至此结束，下次见", audio_path, rewrite=True)
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration

    # 设置背景视频时长
    bg_clip = bg_clip.with_duration(duration).with_audio(audio_clip)

    # 创建日期文字
    txt_clip = TextClip(
        text="谢谢收看",
        font_size=int(GLOBAL_HEIGHT * 0.15),
        color=MAIN_BG_COLOR,
        font='./font/simhei.ttf',
        stroke_color='black',
        stroke_width=2
    ).with_duration(duration).with_position(('center', GLOBAL_HEIGHT * 0.7))

    lady = (VideoFileClip('videos/lady_announcer.mp4').with_duration(duration)
            .with_position((GLOBAL_WIDTH * 0.38, GLOBAL_HEIGHT * 0.17)).resized(0.7))

    # 合成最终视频
    final_clip = CompositeVideoClip([bg_clip, txt_clip, lady], size=bg_clip.size)
    if is_preview:
        final_clip.preview()
    else:
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=FPS)
    return output_path


def combine_videos_with_transitions(video_paths, output_path):
    if os.path.exists(output_path) and not REWRITE:
        logger.info(f"视频整合生成{output_path}已存在,直接返回")
        return
    bg_clip = ImageClip(BACKGROUND_IMAGE_PATH)

    # 加载视频和音频
    clips = []
    for i, video_path in enumerate(video_paths):
        # 加载视频
        video = VideoFileClip(video_path)
        if (video.duration < 2):
            logger.warning(f"视频{video_path}时长不足2秒,跳过")
            continue
        video = video.with_position(('center', 'center'), relative=True)
        # 将视频放置在背景上
        video_with_bg = CompositeVideoClip([
            bg_clip,
            video
        ], use_bgclip=True)
        # 将视频放置在背景上
        clips.append(video_with_bg)

    final_clip = concatenate_videoclips(clips, method="compose")
    # 导出最终视频
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=FPS)
    logger.info(f"视频整合生成完成,path={output_path}")
    # final_clip.preview()


def combine_videos(today: str = datetime.now().strftime("%Y%m%d")):
    start_time = time.time()
    video_paths = []
    intro_path = build_today_introduction_path(today)
    video_paths.append(intro_path)
    logger.info(f"正在生成视频片头{intro_path}...")
    topics, duration = generate_video_introduction(intro_path, today)
    all_paths = generate_all_news_video(today=today)
    for i in range(len(all_paths)):
        video_paths.append(all_paths[i])
    video_paths.append(generate_video_end())
    logger.info(f"生成当前的JSON文件...")
    logger.info(f"根据子视频生成主视频并整合...")
    final_path = build_today_final_video_path(today)
    logger.info(f"视频保存在={final_path}")
    combine_videos_with_transitions(video_paths, final_path)

    end_time = time.time()  # 结束计时
    elapsed_time = end_time - start_time
    save_today_news_json(topics, today)
    logger.info(f"视频整合生成总耗时: {elapsed_time:.2f} 秒")


def generate_all_news_video(today: str = datetime.now().strftime("%Y%m%d")) -> list[str]:
    json_file_path = build_new_articles_path(today, EVENING)

    if not os.path.exists(json_file_path):
        logger.warning(f"新闻json文件不存在,path={json_file_path}")
        return []

    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        news_data = json.load(json_file)

    video_output_paths = []
    idx = 1
    for i, news_item in enumerate(news_data, start=1):
        article = NewsArticle(**news_item)
        dir_path = os.path.join(CN_NEWS_FOLDER_NAME, today, article.source, article.folder)
        logger.info(f"{article.source}{article.folder}{article.show}{article.title}   新闻正在处理...")
        if not article.show:
            logger.warning(f"{article.source}{article.folder}{article.title}新闻已隐藏，跳过生成")
            continue

        # 新增逻辑：将摘要转换为音频并保存
        video_output_path = os.path.join(dir_path, VIDEO_FILE_NAME)
        if os.path.exists(video_output_path) and not REWRITE:
            logger.warning(f"{article.source}{article.folder}  视频已存在，跳过生成,path={video_output_path}")
            video_output_paths.append(video_output_path)
            continue

        audio_output_path = os.path.join(dir_path, AUDIO_FILE_NAME)
        img_list = []
        for image in article.images:
            img_list.append(os.path.join(dir_path, image))
        generated_result = generate_three_layout_video(
            output_path=video_output_path,
            audio_path=audio_output_path,
            image_list=img_list,
            summary=article.summary,
            title=article.title,
            index=str(idx),
            is_preview=False
        )
        if generated_result:
            idx += 1
            video_output_paths.append(video_output_path)
    return video_output_paths


def load_json_by_source(source, today):
    folder_path = os.path.join(CN_NEWS_FOLDER_NAME, today, source)
    json_file_path = os.path.join(folder_path, PROCESSED_NEWS_JSON_FILE_NAME)
    if not os.path.exists(json_file_path):
        logger.warning(f"{source}新闻json文件不存在,path={json_file_path}")
        return json_file_path, None
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        news_data = json.load(json_file)
    logger.info(f"{source}新闻json文{json_file_path}件加载成功,news_data={len(news_data)}")
    return json_file_path, news_data


def save_today_news_json(topic, today: str = datetime.now().strftime("%Y%m%d")):
    json_file_path = build_new_articles_path(today, EVENING)

    if not os.path.exists(json_file_path):
        logger.warning(f"新闻json文件不存在,path={json_file_path}")
        return []

    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        news_data = json.load(json_file)
    urls = []
    titles = [hint_information]
    if news_data:
        for i in news_data:
            urls.append(i['url'])
            if i['show']:
                titles.append(i['title'])
    append_and_save_month_urls(today[:6], set(urls))
    json_file_path = build_today_json_path(today)

    if os.path.exists(json_file_path):
        json_data = json.load(open(json_file_path, 'r', encoding='utf-8'))
        topic = "###" + today + " |" + topic.replace("\n", "|")
        json_data['topic'] += topic
        [json_data['urls'].append(i) for i in urls]
        [json_data['titles'].append(i) for i in titles]
    else:
        json_data = {
            'topic': today + "|" + topic.replace("\n", "|"),
            'urls': urls,
            'titles': titles
        }
    json.dump(json_data, open(json_file_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
    logger.info(f"保存今日新闻json文件到 {json_file_path}")
    logger.info(f"今日新闻json文件\n {json_data}")


def generate_top_topic_by_ollama(today: str = datetime.now().strftime("%Y%m%d")) -> str:
    client = OllamaClient()
    json_file_path = build_new_articles_path(today, EVENING)
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        news_data = json.load(json_file)
    txt = ";".join([news_item['title'] if news_item['show'] else '' for news_item in news_data])
    data = client.generate_top_topic(txt)
    logger.info(f'topic is \n{data}')
    return data


def test_generate_all():
    today = '20250604'
    generate_all_news_video(today=today)
    generate_all_news_video(today=today)
    generate_background_image(GLOBAL_WIDTH, GLOBAL_HEIGHT)
    generate_video_introduction()
    combine_videos_with_transitions(
        ['cn_news/20250512/intro.mp4', 'cn_news/20250512/0000/video.mp4', 'cn_news/20250512/0001/video.mp4'], 'a.mp4',
        '', today)


def test_generate_video_introduction():
    REWRITE = True
    generate_video_introduction(today='20250606', is_preview=True)


def test_video_text_align():
    list = [
        'news/20250604/chinadaily/0000/683fd3d86b8efd9fa6284ef8_m.png',
        'news/20250604/chinadaily/0000/683fd3d96b8efd9fa6284efa_m.jpg',
        'news/20250604/chinadaily/0000/683fd3d96b8efd9fa6284efc_m.jpg',
        'news/20250604/chinadaily/0000/683fd3da6b8efd9fa6284efe_m.jpg'
    ]

    generate_three_layout_video(
        output_path="news/20250604/chinadaily/0000/video.mp4",
        audio_path="news/20250604/chinadaily/0000/summary_audio.aiff",
        image_list=list,
        summary="""韩国新总统李在镕以近50%的选票胜出，但其蜜月期仅一天即上任，需应对弹劾前总统尹锡烈留下的政治和安全漏洞。首轮挑战是处理唐纳德·特朗普可能破坏的经济、安全和与朝鲜关系。一季度韩国经济收缩，已因特朗普征收25%关税陷入困境。美国驻首尔军事存在可能转向遏制中国，增加韩国的外交和军事压力。李明博希望改善与中国的关系，但面临美国对朝鲜半岛战略布局的不确定性，同时需解决国内民主恢复问题。""",
        title="""[英国广播公司]韩国新总统需要避免特朗普式的危机""",
        index="0000",
        is_preview=False
    )


def test_generate_video_end():
    generate_video_end(is_preview=True)


import argparse


def print_init_parameters():
    logger.info('========================start generation==============================')
    logger.info(
        f"\nGLOBAL_WIDTH:{GLOBAL_WIDTH}\nGLOBAL_HEIGHT:{GLOBAL_HEIGHT}\n W_H_RADIO:{W_H_RADIO}\n  FPS:{FPS}\n  BACKGROUND_IMAGE_PATH:{BACKGROUND_IMAGE_PATH}\nGAP:{GAP}\nINNER_WIDTH:{INNER_WIDTH}\nINNER_HEIGHT:{INNER_HEIGHT}")
    if not os.path.exists('temp'):
        os.mkdir('temp')
    if not os.path.exists('videos'):
        os.mkdir('videos')
    if not os.path.exists('final_videos'):
        os.mkdir('final_videos')


if __name__ == "__main__":
    print_init_parameters()

    parser = argparse.ArgumentParser(description="新闻视频生成工具")
    parser.add_argument("--today", type=str, default=datetime.now().strftime("%Y%m%d"), help="指定日期")
    parser.add_argument("--evening", type=bool, default=False, help="是否执行晚间任务")
    parser.add_argument("--rewrite", type=bool, default=False, help="是否重写")
    args = parser.parse_args()
    logger.info(f"新闻视频生成工具 参数args={args}")

    # 示例：处理参数
    if args.evening:
        logger.info("执行晚间任务")
        EVENING = True
        CHINADAILY = CHINADAILY + EVENING_TAG
        CHINADAILY_EN = CHINADAILY_EN + EVENING_TAG
        RT = RT + EVENING_TAG
        ALJ = ALJ + EVENING_TAG
        BBC = BBC + EVENING_TAG

    if args.rewrite:
        REWRITE = True
        logger.info("指定强制重写")
    try:
        combine_videos(args.today)
    except Exception as e:
        logger.error(f"视频生成主线失败,error={e}", exc_info=True)
