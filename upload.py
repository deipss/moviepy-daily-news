from playwright.sync_api import sync_playwright
import os
import time
import base64
import requests
from typing import Dict
import json
from logging_config import logger
from utils import send_to_dingtalk, build_daily_json_path, get_yesterday_str, send_qr_to_dingtalk
import argparse
from datetime import datetime

STATE_FILE = "temp/bilibili_state.json"
BILIBILI_HOME = "https://www.bilibili.com/"
UPLOAD_URL = "https://member.bilibili.com/platform/upload/video/frame"


def sessdata_valid(state_file=STATE_FILE):
    """检查 SESSDATA 是否存在且未过期"""
    if not os.path.exists(state_file):
        return False

    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    now_ts = time.time()
    for cookie in data.get("cookies", []):
        if cookie.get("name") == "SESSDATA":
            expires = cookie.get("expires", -1)
            if expires == -1:  # session cookie
                return True
            human_time = datetime.fromtimestamp(expires)
            print(f"SESSDATA 过期时间: {human_time}")
            if expires > now_ts:
                return True
            else:
                print("SESSDATA 已过期")
                return False
    return False


def save_login_state(context):
    """保存登录态"""
    context.storage_state(path=STATE_FILE)
    logger.info(f"登录态已保存到 {STATE_FILE}")


def load_context(browser):
    """加载已有登录态，如果存在"""
    if os.path.exists(STATE_FILE):
        logger.info("检测到已有登录态，尝试加载")
        return browser.new_context(storage_state=STATE_FILE)
    else:
        logger.info("没有检测到登录态，需要扫码登录")
        return browser.new_context()


def check_logged_in_by_cookie(context):
    """通过 Cookie 检测是否登录成功"""
    cookies = context.cookies()
    return any(c['name'] == 'SESSDATA' for c in cookies)


def login_with_qr(page, context, max_wait_time=60):
    """扫码登录逻辑"""
    page.goto(BILIBILI_HOME)
    page.wait_for_timeout(2000)
    logger.info("打开B站首页，准备扫码登录")

    # 点击登录按钮
    page.click(".header-login-entry")
    page.wait_for_timeout(1000)

    # 获取二维码
    qr_img = page.locator('img[alt="登录二维码"]').nth(0)
    qr_src = qr_img.get_attribute("src")

    if qr_src.startswith("data:image"):
        base64_data = qr_src.split(",", 1)[1]
        image_bytes = base64.b64decode(base64_data)
    else:
        response = requests.get(qr_src)
        image_bytes = response.content
        base64_data = base64.b64encode(image_bytes).decode("utf-8")

    os.makedirs("temp", exist_ok=True)
    image_path = "temp/bilibili_qrcode.png"
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    send_qr_to_dingtalk(base64_data)
    logger.info("二维码已发送到钉钉，等待扫码...")

    # 等待 Cookie 出现
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        if check_logged_in_by_cookie(context):
            logger.info("登录成功")
            return True
        time.sleep(0.5)

    logger.warning("扫码超时，登录失败")
    return False

def ensure_logged_in(browser):
    if sessdata_valid():
        logger.info("检测到有效的 SESSDATA，加载登录态")
        context = browser.new_context(storage_state=STATE_FILE)
        return context
    else:
        logger.info("SESSDATA 不存在或已过期，重新扫码登录")
        context = browser.new_context()
        page = context.new_page()
        if not login_with_qr(page, context):
            send_to_dingtalk("B站登录失败", True)
            raise Exception("登录失败")
        save_login_state(context)
        return context


def upload_one(page, news_dict):
    """上传视频逻辑"""
    page.goto(UPLOAD_URL)
    page.wait_for_timeout(2000)

    # 点击上传区域
    page.click('.bcc-upload-wrapper')
    upload_input = page.locator('.bcc-upload-wrapper input[type="file"]')
    upload_input.set_input_files(news_dict['final_path_walk'])
    logger.info(f"上传文件: {news_dict['final_path_walk']}")
    page.wait_for_timeout(10000)

    # 标题
    page.get_by_role("textbox", name="请输入稿件标题").fill(news_dict['title'])
    # 更换封面
    page.get_by_text("更换封面").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="完成").click()
    page.wait_for_timeout(3000)

    # 分类
    page.locator(".select-controller").first.click()
    page.get_by_title("资讯", exact=True).click()
    page.wait_for_timeout(1000)

    # 标签
    tag_input = page.get_by_role("textbox", name="按回车键Enter创建标签")
    for tag in news_dict['tags']:
        tag_input.fill(tag)
        tag_input.press("Enter")
        page.wait_for_timeout(100)

    # 活动
    try:
        page.get_by_text("环球资讯站", exact=True).click()
    except:
        logger.error("活动选择失败")
    # 简介
    page.locator(".ql-editor").first.fill(news_dict['introduction'])

    # 提交
    page.get_by_text("立即投稿", exact=True).click()
    page.wait_for_timeout(5000)
    send_to_dingtalk(f"{news_dict['final_path_walk']} 上传成功", False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="B站自动上传工具")
    parser.add_argument("--today", type=str, default=get_yesterday_str(), help="指定日期")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = ensure_logged_in(browser)
            page = context.new_page()

            daily_text_path = build_daily_json_path(args.today)
            if os.path.exists(daily_text_path):
                with open(daily_text_path, 'r', encoding='utf-8') as json_file:
                    upload_file_json: Dict[str, Dict[str, object]] = json.load(json_file)

                for k, news_dict in upload_file_json.items():
                    try:
                        logger.info(f"开始上传: {k}")
                        upload_one(page, news_dict)
                    except Exception as e:
                        logger.error(f"上传 {k} 出错: {e}", exc_info=True)
                        send_to_dingtalk(f"上传 {k} 出错", True)
                    finally:
                        page.wait_for_timeout(5000)
            else:
                logger.info(f"{daily_text_path} file not exists")
        finally:
            browser.close()
