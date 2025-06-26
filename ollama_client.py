import requests
from typing import Dict, Any
from logging_config import logger
import time
from functools import wraps


def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        logger.info(f" Ollama函数 {func.__name__} 耗时 {elapsed_time:.4f} 秒")
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

    def _generate_text(self, prompt: str, model: str = "deepseek-r1:8b", options: Dict[str, Any] = None) -> Dict[
        str, Any]:
        """
        使用Ollama服务生成文本。

        :param prompt: 输入的提示文本
        :param model: 使用的模型名称，默认为"deepseek-r1:8b"
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

    def generate_summary(self, text: str, model: str = "deepseek-r1:8b", max_tokens: int = 200) -> str:
        """
        生成中文文本的摘要。

        :param text: 输入的中文文本
        :param model: 使用的模型名称，默认为"deepseek-r1:8b"
        :param max_tokens: 摘要的最大token数，默认为50
        :return: 生成的摘要文本
        """
        prompt = f"请为以下文本生成一个简洁的中文新闻摘要（不超过{max_tokens}个字）：\n{text}"
        cnt = 3
        response = self._generate_text(prompt, model, {"max_tokens": max_tokens})
        while cnt > 0:
            if "error" in response:
                response = self._generate_text(prompt, model, {"num_predict": max_tokens})
                logger.error(f"生成摘要失败,last time is {cnt}: {response['error']},text={text}")
            cnt -= 1
        summary = response.get("response", "")
        summary = self._extract_think(summary)

        if len(summary) > max_tokens:
            logger.info(f"当前摘要={summary}")
            logger.info(f"当前摘要={len(summary)},摘要超过{max_tokens}个字，再次生成摘要")
            prompt = f"请为以下文本生成一个简洁的中文新闻摘要（不超过{max_tokens}个字）：\n{summary}"
            response = self._generate_text(prompt, model, {"num_predict": max_tokens})
            summary = response.get("response", "")
            summary = self._extract_think(summary)

        return summary

    def generate_summary_cn(self, text: str, model: str = "deepseek-r1:8b", max_tokens: int = 200) -> str:
        """
        生成中文文本的摘要。

        :param text: 输入的中文文本
        :param model: 使用的模型名称，默认为"deepseek-r1:8b"
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

        prompt = f"请为以下文本生成一个简洁的中文新闻摘要（不超过{max_tokens}个字）：\n{text}"
        cnt = 3
        response = self._generate_text(prompt, model, {"num_predict": max_tokens})
        while cnt > 0:
            if "error" in response:
                response = self._generate_text(prompt, model, {"num_predict": max_tokens})
                logger.error(f"生成摘要失败,last time is {cnt}: {response['error']},text={text}")
            cnt -= 1
        summary = response.get("response", "")
        summary = self._extract_think(summary)

        if len(summary) > max_tokens:
            logger.info(f"当前摘要={summary}")
            logger.info(f"当前摘要={len(summary)},摘要超过{max_tokens}个字，再次生成摘要")
            prompt = f"请为以下文本生成一个简洁的中文新闻摘要（不超过{max_tokens}个字）：\n{summary}"
            response = self._generate_text(prompt, model, {"num_predict": max_tokens})
            summary = response.get("response", "")
            summary = self._extract_think(summary)

        return summary

    def generate_top_topic(self, text: str, model: str = "deepseek-r1:8b", max_tokens: int = 50) -> str:
        prompt = f"请从以下新闻主题，提取出影响力最高的4个，这4个主题每个主题再精简到10个字左右，同时请排除一些未成年内容,只需返回按序号排列4个主题：\n{text}"
        response = self._generate_text(prompt, model, {"num_predict": max_tokens})
        summary = response.get("response", "")
        summary = self._extract_think(summary, is_replace_line=False)
        summary = summary.replace("**", "")
        if len(summary) > max_tokens:
            logger.info(f"当前主题={summary}")
            logger.info(f"当前主题={len(summary)},主题超过{max_tokens}个字，再次生成主题")
            prompt = f"请从以下新闻主题，提取出影响力最高的4个，这4个主题每个主题再精简到8个字左右，同时请排除一些未成年内容，只需返回按序号排列4个主题：：\n{summary}"
            response = self._generate_text(prompt, model, {"num_predict": max_tokens // 10 * 9})
            summary = response.get("response", "")
            summary = self._extract_think(summary, is_replace_line=False)
            summary = summary.replace("**", "")
        return summary

    def generate_top_title(self, text: str, model: str = "deepseek-r1:8b",
                           max_tokens: int = 80, count: int = 15) -> str:
        prompt = f"请从以下带有序号的新闻主题，提取出影响力最高的{count}个，过滤一些区县市的新闻，最终返回影响力最高的新闻的原始序号（用英文逗号隔开）：\n{text}"
        response = self._generate_text(prompt, model, {"num_predict": max_tokens})
        summary = response.get("response", "")
        summary = self._extract_think(summary, is_replace_line=False)
        summary = summary.replace("**", "")
        return summary

    def generate_top_news_summary(self, text: str, model: str = "deepseek-r1:8b",
                                  max_tokens: int = 80, count: int = 15) -> str:
        prompt = f"请从以下标题信息，生成一从在{max_tokens}左右的新闻稿：\n{text}"
        response = self._generate_text(prompt, model, {"num_predict": max_tokens})
        summary = response.get("response", "")
        summary = self._extract_think(summary, is_replace_line=False)
        summary = summary.replace("**", "")
        return summary

    def translate_to_chinese(self, text: str, model: str = "deepseek-r1:8b") -> str:

        prompt = f"请将以下英文文本翻译成中文,只返回中文：\n{text}"
        response = self._generate_text(prompt, model)
        return self._extract_think(response.get("response", ""))

    def translate_to_english(self, text: str, model: str = "deepseek-r1:8b") -> str:

        prompt = f"请将以下英文文本翻译成英文，只返回英文：\n{text}"
        response = self._generate_text(prompt, model)
        return self._extract_think(response.get("response", ""))


if __name__ == '__main__':
    client = OllamaClient()
    a = client.generate_summary_cn("""
    \"Did you know I can run 100 metres in 19 seconds?\" Rod Stewart,SirRod Stewart, is boasting about his physical prowess. And why not? At the age of 80, he's still cavorting around the world, playing sold out shows, recording new music and even writing a book about his beloved model train set. This weekend, he'll play the coveted \"legends\" slot on Glastonbury's Pyramid stage... although the former headliner isn't 100% happy about his billing. \"I just wish they wouldn't call it the tea time slot,\" he complains. \"That sounds like pipe and slippers, doesn't it?\" He's also persuaded organisers to extend his set, securing an hour-and-a-half slot after initially being offered 75 minutes. \"Usually I do well over two hours so there's still a load of songs we won't be able to do,\" he says. \"But we've been working at it. I'm not gonna make any announcements between songs. I'll do one number, shout 'next', and go straight into the next one. \"I'm going to get in as many songs I can.\" It's not like he's short of choice. Sir Rod has one of the all-time classic songbooks, from early hits with the Faces such as Stay With Me and Ooh La La, to his solo breakthrough with Maggie May, the slick pop of Do Ya Think I'm Sexy? and his reinvention as a crooner on songs like Downtown Train and Have I Told You Lately. The last time he played Glastonbury, in 2002, he was viewed as an interloper – sitting awkwardly on the bill beside the likes of The White Stripes, Coldplay and Orbital. At first, \"the crowd was wary\" of the musician, who \"looked to be taking himself too seriously\", said the BBC's Ian Youngs in a review of the show. But a peerless setlist of singalongs won them over. By the end of the night, 100,000 people were swaying in time to Sailing as if they were genuinely adrift on the surging tides of the Atlantic. Amazingly, Rod has no memory of it. \"I don't remember a thing,\" he confesses. \"I do so many concerts, they all blend into one.\" One particular show does stand out, though. On New Year's Eve 1994, Sir Rod played a free gig on Brazil's Copacabana Beach, drawing a crowd of more than three million people. But it wasn't the record-breaking audience that made it memorable. \"I was violently sick about an hour before I was supposed to go on,\" he confesses. \"I'd eaten something terrible, and I was in a toilet going, 'huerrrgurkurkbleaggggh' \"I didn't think I was going to make it but luckily they got a doctor to sort me out.\" We're talking to the star about a month before Glastonbury at the Devonshire, a relaxed, old-school boozer just off Picadilly Circus that's become the favoured haunt of everyone from Ed Sheeran to U2. It's a bit too early for a drink, though, so Sir Rod orders up a venti coffee, shooing away an over-eager assistant who attempts to stir in his sugar. He's dressed in a cream jacket and black jeans, which sit above the ankle to show off his box-fresh, zebra-striped trainers. His white shirt is unbuttoned far enough to display a diamond-encrusted necklace with the crest of his beloved football club, Celtic. And then there's the hair. A bleached blonde vista of windswept spikes, so famous that it earned a whole chapter in the singer's autobiography. Steve Marriott of The Small Faces once claimed that Sir Rod achieved this gravity-defying barnet by rubbing mayonnaise into his scalp, then rubbing it with a towel. This, says the musician, is utter \"bollocks\". \"Nah, nah, nah. I used to use sugared hot water, before the days of hair lacquer. And I couldn't afford hair lacquer, anyway.\" But what really sets Sir Rod apart is that voice. Raspy, soulful, raw and expressive, he's one of rock and roll's best interpretive singers. There's a reason why his covers of Cat Steven's First Cut Is The Deepest or Crazy Horse's I Don't Wanna Talk About It have eclipsed the originals. So it's a surprise to learn that he was discovered not for his vocals, but his harmonica skills. That fateful night in 1964, he'd been at a gig on Twickenham's Eel Pie Island, and was drunkenly playing the riff from Holwin' Wolf's Smokestack Lightnin' while he waited for the train home, when he was overheard by influential blues musician Long John Baldry. \"As he described it, he was walking along platform nine when he noticed this pile of rubble and clothes with a nose pointing out,\" Sir Rod recalls. \"And that was me playing harmonica.\" At the time, he \"wasn't so sure\" about his singing voice. But, with Baldry's encouragement, he started to develop his signature sound. \"I wanted to always sound like Sam Cooke and Otis Redding, so that's the way I went,\" he says.  \"I suppose I was trying to be different from anybody else.\" Sir Rod began his ascent to stardom with the Jeff Beck Group and the Faces, a boisterous blues-rock outfit heavily inspired by the Rolling Stones – both on and off the stage. They were regularly so drunk he'd forget the words to his own songs, he admits. In the US, the group received a 40-year ban from the Holiday Inn hotel chain after racking up a $11,000 bill (£8,000 – or £54,000 in 2025 money) for trashing their rooms. \"We only did it because the Holiday Inns would treat us so badly, like we were the scum of the earth,\" he says. \"So we'd get our own back by smashing the hotels up. One time we actually got a couple of spoons and chiselled through the walls to one another's rooms. \"But we used to book in as Fleetwood Mac, so they'd get the blame.\" How come he never succumbed to drink and drugs, like many of his contemporaries? \"I never was a really druggy person, because I played football all the time and I had to be match fit,\" he says. \"I would use the word dabble. I've dabbled in drugs, but not anymore.\" Perhaps a more destructive force was the singer's womanising. He wrote You're In My Heart for Bond girl Britt Ekland, but they split two years later, due to his persistent unfaithfulness. His marriage to Alana Stewart and relationship with model Kelly Emberg ended the same way. \"When it came to beautiful women, I was a tireless seeker of experiences,\" he wrote in his memoir. \"I didn't know how to resist. And also... I thought I could get away with it.\" He thought he'd settled down after marrying model Rachel Hunter in 1990, but she left him nine years later, saying she felt she had \"lost her identity\" in the relationship. The split hit Sir Rod hard. \"I felt cold all the time,\" he said. \"I took to lying on the sofa in the day, with a blanket over me and holding a hot water bottle against my chest. \"I knew then why they call it heartbroken: You can feel it in your heart. I was distracted, almost to the point of madness.\" However, since 2007, the star has been happily married to TV presenter / police constable Penny Lancaster, with the couple reportedly renewing their vows in 2023. Last week, they celebrated their 18th wedding anniversary with a trip on the Orient Express from Paris, where they met in 2005, to La Cervara in Portofino, where they held their wedding ceremony, in a medieval monastery. These days, Sir Rod says, family is his priority. \"I've got eight kids all together, so sometimes I'll wake up in the morning and see all these messages, Stewart, Stewart, Stewart, Stewart…  and it's all the kids. It's just gorgeous.\" His youngest, Aiden, is now 14, and becoming an historian of his dad's work. \"He's gone back and listened to everything I've done, bless him,\" says the star. \"He knows songs that I don't even remember recording!\" His Glastonbury appearance coincides with the release of a new greatest hits album – his 20th. (\"Is it really?\" gasps Sir Rod. \"Ohgawwwwd.\") So how does it feel to look back over those five decades of music? \"Oh, it's tremendous,\" he says. \"It's a feeling that you've done what you set out to do. \"I don't consider myself a particularly good songwriter,\" he adds. \"I struggle with it. It takes me ages to write a set of lyrics. \"So I don't think I'm a natural songwriter. I'm just a storyteller, that's all. A humble storyteller.\" Maybe – but this humble storyteller is going to draw a crowd of thousands when he plays the Pyramid Stage on Sunday afternoon. \"You know, it's wonderful,\" he concedes. \"I'll be in good voice. I'll enjoy myself. I don't care anymore what the critics think. \"I'm there to entertain my people.\" A wheelie bin to carry your tent to smiling faces in the crowd - the festival is now under way. Alison Howe credits a Northampton teacher for inspiring her to pursue a dream of working in music. The Indian megastar stands by Sardaar Ji 3 as political tensions threaten to overshadow its release. U2 bassist Adam Clayton delivered a reading at the funeral of Lord Henry Mount Charles in Slane. Sir Michael and Emily Eavis welcome hundreds of punters to \"the most joyful city in the UK\". Copyright 2025 BBC. All rights reserved.TheBBCisnot responsible for the content of external sites.Read about our approach to external linking.
    """)
    print(a)
