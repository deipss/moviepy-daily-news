<p align="center">

![Static Badge](https://img.shields.io/badge/python-3.10-blue)
![Static Badge](https://img.shields.io/badge/ollama_client-0.4.8-yellow)
![Static Badge](https://img.shields.io/badge/moviepy-2.1.2-red)
![Static Badge](https://img.shields.io/badge/beautifulsoup4-4.12.2-green)
![Static Badge](https://img.shields.io/badge/deepseekr1-R8-%23CC0033)
</p>

# 📄 免责声明（Disclaimer）

>
> 本项目为开源性质，提供新闻数据爬取功能，仅供学习、研究和非商业用途。使用本代码进行任何操作前，请您务必仔细阅读以下免责声明：
>
> 1. 遵守法律法规
> 使用者应确保其行为符合所在国家/地区的相关法律法规，包括但不限于《网络安全法》《个人信息保护法》《著作权法》等相关法律规定。开发者不对因使用本项目而引发的任何法律责任负责。
>
> 2. 尊重网站规则
> 本项目仅为技术演示目的，爬取方式可能违反部分网站的服务条款或robots协议。请在使用前查阅目标网站的 robots.txt
文件及相关政策，并获得合法授权后再进行大规模抓取。如因爬虫行为导致IP被封禁、账号受限或其他后果，责任由使用者自行承担。
>
> 3. 数据使用风险
> 通过本项目获取的数据仅限于个人学习、测试或研究用途。禁止将数据用于非法传播、商业牟利、侵犯他人隐私等不当用途。开发者对使用者如何处理所爬取的数据概不负责。
>
> 4. 无商业支持与担保
> 本项目为免费开源项目，不提供任何形式的技术支持、维护或更新。代码可能存在缺陷、错误或兼容性问题，使用时需自行评估风险。
>
> 5. 不承担连带责任
> 开发者及贡献者不对由于使用本项目造成的任何直接或间接损失（包括但不限于数据丢失、服务中断、名誉损害等）承担责任。

# ✅ 技术方案

大概的方向就是先使用爬虫技术，爬取网站的新闻文本、图片，英文新闻使用机器翻译进行翻译，使用ollama中deepseek进行翻译，摘要提取，
上述的素材准备好，使用moviepy生成视频。主要用的技术：

- 爬虫：BeautifulSoup
- 机器翻译：~~字节旗下的[火山翻译](https://www.volcengine.com/docs/4640/65067)~~（每月有免费额度，不够用已移除）使用Deepseek翻译
- 摘要提取：ollama 部署了  [deepseek-r1:8b](https://ollama.com/library/deepseek-r1 "点击打开ollama")
- 文字转语音:~~[字节的megaTTS](https://github.com/bytedance/MegaTTS3)~~，8G的GTX1080显存不够，使用微软的edge-tts，效果还可以。
- 视频生成：moviepy

> 硬件最好是有GPU，用来运行ollama，当然可以用云服务器代替，取决于个人的资源。

# 🧠 新闻来源

- [x] 中国日报（chinadaily）
- [x] 英国广播公司（BBC）
- [ ] 英国卫报（The Guardian）https://www.theguardian.com/us
- [ ] 泰晤士报（The Times） https://www.thetimes.com/
- [x] 今日俄罗斯 https://www.rt.com/
- [x] 中东半岛新闻 https://www.aljazeera.com/

英国卫报、泰晤士报、彭博社报和BBC的内容差不多，不再重复爬取。

# 📊 使用

在ubuntu 22.04 中，使用conda创建一个python3.11的环境，安装依赖包，然后运行crawl_news.py和video_generator.py。

> 要先使用python crawl_news.py，下载好的数据，再调用video_generator.py生成视频。

```shell
source activate py311
python crawl_news.py
python video_generator.py
# 支持日期的传入
python crawl_news.py 20250605
python vedio_generator.py 20250605
```

# 🔮 效果

- https://space.bilibili.com/372736088 每日生成的视频

以下生成的视频截图
![img.png](assets/introduction.png)

![img1.png](assets/news.png)

# 🧭测试

功能可用，在摘要生成时，以下的nvidia 1080 8G 显卡，在运行ollama deepseek-r1:8b进行摘要生成的情况：
![nvidia.png](assets/nvidia.png)

# 📌 todo

- [x] 英文翻译成中文
- [x] ollama进行摘要提取
- [ ] ~~ollama进行摘要提取后，增加一个小的评论~~
- [x] 信息的过滤，对于政治类的信息，中英文的都要去除
- [ ] ~~照片去重~~
- [x] 晚间新闻
- [x] 重试入口
- [x] 内容过滤
- [x] 时长过多，要精简
- [x] 片头优化
- [x] china daily 英文版
- [x] bbc 下线，因为爬虫被检测到，封禁了
- [x] ~~china daily asis 版~~
- [ ] 背景音乐
- [ ] 视频爬取
- [ ] 自动上传B站:制定一个APP，可以上传多平台
- [x] multiple threading : is edge-tts thread safety? No, It is not safety, meanwhile it is would be limited traffic.
- [x] multiple threading : is moviepy write_file thread safety? No, It is not safety, cause some global variates are
  shared .


