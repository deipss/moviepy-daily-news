# 技术方案
大概的方向就是先使用爬虫技术，爬取网站的新闻文本、图片，英文新闻使用机器翻译进行翻译，使用ollama中deepseek进行摘要提取，上述的素材准备好，使用moviepy生成视频。
主要用的技术：
- 爬虫：BeautifulSoup
- 机器翻译：字节旗下的火山翻译 https://www.volcengine.com/docs/4640/65067
- 摘要提取：ollama 部署了 deepseek-r1:8b https://ollama.com/library/deepseek-r1
- 视频生成：moviepy

> 硬件最好是有GPU，用来运行ollama，当然可以用云服务器代替，取决于个人的资源。



## 细节处理

# 新闻来源

- [x] 中国日报（chinadaily）
- [x] 英国广播公司（BBC）
- [ ] 英国卫报（The Guardian）https://www.theguardian.com/us
- [ ] 泰晤士报（The Times） https://www.thetimes.com/
- [ ] 彭博社报 （要钱）https://www.bloomberg.com/
  英国卫报、泰晤士报、彭博社报和BBC的内容差不多，不再重复爬取。

# todo 

- [x] 英文翻译成中文
- [x] ollama进行摘要提取
- [ ] ollama进行摘要提取后，增加一个小的评论
- [x] 信息的过滤，对于政治类的信息，中英文的都要去除

