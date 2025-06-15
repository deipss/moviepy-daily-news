import os
import json
import gradio as gr
from pathlib import Path
from datetime import datetime
from logging_config import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor
from crawl_news import build_new_articles_uploaded_path, ALJ_UP
from video_generator_portrait import combine_videos

# 保存目录
VIDEO_DIR = "news_p"
os.makedirs(VIDEO_DIR, exist_ok=True)
ROW = 4


def generate_audio(text: str, output_file: str = "audio.wav", rewrite=False) -> None:
    logger.info(f"{output_file}开始生成音频: {text}")
    rate = 70
    sh = f'edge-tts --voice zh-CN-XiaoxiaoNeural --text "{text}" --write-media {output_file} --rate="+{rate}%"'
    os.system(sh)


def save_videos(*args):
    try:
        video_info = []
        times = int(args[-2])
        for i in range(ROW):
            video_file = args[i * 3]
            if not video_file:
                logger.warning(f"{i}视频是空的")
                continue
            title = args[i * 3 + 1].replace('\n', '')
            description = args[i * 3 + 2].replace('\n', '')

            if not (video_file and title and description):
                return f" 第{i + 1}组信息不完整，请检查。"

            # 保存视频文件
            today = datetime.now().strftime('%Y%m%d')
            filename = f"{times}_{title}.mp4"
            uploaded_video_path = os.path.join(VIDEO_DIR, today, ALJ_UP, filename)
            os.makedirs(os.path.dirname(uploaded_video_path), exist_ok=True)

            with open(video_file.name, "rb") as src_file:
                with open(uploaded_video_path, "wb") as out_file:
                    out_file.write(src_file.read())
            mp3_path = f"{times}_{title}.mp3"
            mp3_path = os.path.join(VIDEO_DIR, today, ALJ_UP, mp3_path)

            generate_audio(description, mp3_path)

            video_info.append({
                "video": uploaded_video_path,
                "audio": mp3_path,
                "title": title,
                "summary": description,
                "source": ALJ_UP,
                "show": True
            })

        # 保存为 JSON
        with open(build_new_articles_uploaded_path(times_tag=times), "w", encoding="utf-8") as f:
            json.dump(video_info, f, ensure_ascii=False, indent=2)

        combine_videos(times_tag=times)

        return f"视频生成"
    except Exception as e:
        logger.error(f"上传失败: {e}", exc_info=True)
        return f"上传失败: {str(e)}"


if __name__ == '__main__':

    with gr.Blocks() as demo:
        with gr.Row():
            # 左侧：上传区
            with gr.Column(scale=3):
                inputs = []
                for i in range(ROW):
                    with gr.Group():
                        gr.Markdown(f"### 视频 {i + 1}")
                        video = gr.File(label="上传视频", file_types=["video"], file_count="single", scale=1)
                        title = gr.Textbox(label="视频名称")
                        description = gr.Textbox(label="视频描述", lines=2)
                        inputs.extend([video, title, description])

            # 右侧：输出结果区
            with gr.Column(scale=2):
                title_main = gr.Textbox(label="生成视频名称")
                times = gr.Textbox(label="生成视频序号")
                inputs.append(times)
                inputs.append(title_main)
                submit_btn = gr.Button("上传所有视频")
                result_output = gr.Textbox(label="上传结果", lines=10, interactive=False)

        submit_btn.click(fn=save_videos, inputs=inputs, outputs=result_output)

    demo.launch(server_port=7860)
