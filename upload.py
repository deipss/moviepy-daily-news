from playwright.sync_api import sync_playwright
import base64
import requests
from logging_config import logger
import os
import time
import argparse
from utils import send_to_dingtalk, build_daily_json_path, get_yesterday_str
from typing import Dict
import json
from datetime import datetime, timedelta


def upload_one(page, news_dict):
    # 打开你的目标页面（需要你根据实际情况添加）
    page.goto("https://member.bilibili.com/platform/upload/video/frame")
    page.wait_for_timeout(2000)
    # 点击上传区域
    page.click('.bcc-upload-wrapper')
    logger.info("bcc-upload-wrapper click")
    # 设置上传视频文件
    upload_input = page.locator('.bcc-upload-wrapper input[type="file"]')
    logger.info(f'upload file path  = {news_dict["final_path_walk"]}')
    upload_input.set_input_files(news_dict['final_path_walk'])
    page.wait_for_timeout(10000)  # 等待页面加载动画完成
    logger.info("上传10S结束")
    # 输入标题
    page.get_by_role("textbox", name="请输入稿件标题").fill(news_dict['title'])
    # 点击更换封面
    page.get_by_text("更换封面").click()
    page.wait_for_timeout(1000)  # 等待页面加载动画完成
    page.get_by_role("button", name="完成").click()
    page.wait_for_timeout(3000)  # 等待页面加载动画完成
    # 分类选择
    page.locator(".select-controller").first.click()
    page.get_by_title("资讯", exact=True).click()
    # 选择账号
    try:
        page.get_by_text("环球资讯站").click()
    except Exception as e:
        logger.error(f'add activity tag error {e}', exc_info=True)
        send_to_dingtalk(f'add activity tag error ')

    # 输入标签
    tag_input = page.get_by_role("textbox", name="按回车键Enter创建标签")
    tag_input.click()
    tag_input.press("Backspace")
    tag_input.press("Backspace")
    tag_input.press("Backspace")
    tag_input.press("Backspace")
    tag_input.press("Backspace")
    for i in news_dict['tags']:
        tag_input.fill(i)
        tag_input.press("Enter")
        page.wait_for_timeout(100)
    # 编辑正文内容
    page.locator(".ql-editor").first.click()
    page.locator(".ql-editor").first.fill(news_dict['introduction'])
    # 提交
    page.get_by_text("立即投稿", exact=True).click()
    # 保持浏览器可见
    page.wait_for_timeout(5000)
    send_to_dingtalk(f'{news_dict["final_path_walk"]} upload successful')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="新闻爬取和处理工具")
    parser.add_argument("--today", type=str, default=get_yesterday_str(), help="指定日期")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 打开 bilibili 首页
        page.goto("https://www.bilibili.com/")
        page.wait_for_timeout(2000)  # 等待页面加载动画完成
        logger.info("load bilibili index html")
        # 点击登录按钮
        page.click(".header-login-entry")
        page.wait_for_timeout(1000)  # 等待弹出登录框出现
        logger.info("click login button")

        # 查找登录二维码 <img alt="登录二维码" src="...">
        qr_img = page.locator('img[alt="登录二维码"]').nth(0)
        qr_src = qr_img.get_attribute("src")

        if qr_src.startswith("data:image"):
            # 直接 base64 数据，提取部分
            base64_data = qr_src.split(",", 1)[1]
            image_bytes = base64.b64decode(base64_data)
        else:
            # 非 base64，下载后编码
            response = requests.get(qr_src)
            image_bytes = response.content

        logger.info("logging QRCode base64：")
        logger.info(base64_data)  # 只显示前100字符避免太长
        # 保存为本地图片
        image_path = "temp/bilibili_qrcode.png"
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        os.system(f"open {image_path}")
        logger.info(f"qrcode saved in {image_path}")
        send_to_dingtalk(f"qrcode saved in {image_path}")
        max_wait_time = 60  # 最多等待 60 秒
        interval = 0.5  # 每次检查间隔 0.5 秒
        start_time = time.time()

        logged_in = False
        while time.time() - start_time < max_wait_time:
            cookies = context.cookies()
            sessdata_cookie = next((c for c in cookies if c['name'] == 'SESSDATA'), None)
            if sessdata_cookie:
                logger.info("log in successful")
                logged_in = True
                break
            time.sleep(interval)
            logger.info('wait for user log in')

        if not logged_in:
            logger.warning("logging failed")
            browser.close()
            send_to_dingtalk("logging in bilibili failed")
            exit(1)

        upload_file_json: Dict[str, Dict[str, object]] = {}
        daily_text_path = build_daily_json_path(args.today)
        if os.path.exists(daily_text_path):
            with open(daily_text_path, 'r', encoding='utf-8') as json_file:
                upload_file_json = json.load(json_file)
        for k, news_dict in upload_file_json.items():
            try:
                logger.info(f"start to upload {k}")
                upload_one(page, news_dict)
            except Exception as e:
                logger.error(f'upload_one {k} error {e}', exc_info=True)
                send_to_dingtalk(f'upload_one {k} error ')
            finally:
                page.wait_for_timeout(1000)

        browser.close()
