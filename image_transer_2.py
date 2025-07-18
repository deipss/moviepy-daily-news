import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import torchvision.transforms as transforms
from torchvision import models
from torchvision.utils import save_image
import numpy as np
import matplotlib.pyplot as plt
import os


# 定义网络模型
class Encoder(nn.Module):
    def __init__(self):
        super(Encoder, self).__init__()
        vgg = models.vgg19(pretrained=True).features

        self.slice1 = nn.Sequential()
        self.slice2 = nn.Sequential()
        self.slice3 = nn.Sequential()
        self.slice4 = nn.Sequential()

        for x in range(2):
            self.slice1.add_module(str(x), vgg[x])
        for x in range(2, 7):
            self.slice2.add_module(str(x), vgg[x])
        for x in range(7, 12):
            self.slice3.add_module(str(x), vgg[x])
        for x in range(12, 21):
            self.slice4.add_module(str(x), vgg[x])

        # 冻结参数
        for param in self.parameters():
            param.requires_grad = False

    def forward(self, x):
        h1 = self.slice1(x)
        h2 = self.slice2(h1)
        h3 = self.slice3(h2)
        h4 = self.slice4(h3)
        return h1, h2, h3, h4


class Decoder(nn.Module):
    def __init__(self):
        super(Decoder, self).__init__()
        self.decoder = nn.Sequential(
            nn.ReflectionPad2d((1, 1, 1, 1)),
            nn.Conv2d(512, 256, kernel_size=3),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='nearest'),
            nn.ReflectionPad2d((1, 1, 1, 1)),
            nn.Conv2d(256, 256, kernel_size=3),
            nn.ReLU(),
            nn.ReflectionPad2d((1, 1, 1, 1)),
            nn.Conv2d(256, 256, kernel_size=3),
            nn.ReLU(),
            nn.ReflectionPad2d((1, 1, 1, 1)),
            nn.Conv2d(256, 256, kernel_size=3),
            nn.ReLU(),
            nn.ReflectionPad2d((1, 1, 1, 1)),
            nn.Conv2d(256, 128, kernel_size=3),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='nearest'),
            nn.ReflectionPad2d((1, 1, 1, 1)),
            nn.Conv2d(128, 128, kernel_size=3),
            nn.ReLU(),
            nn.ReflectionPad2d((1, 1, 1, 1)),
            nn.Conv2d(128, 64, kernel_size=3),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='nearest'),
            nn.ReflectionPad2d((1, 1, 1, 1)),
            nn.Conv2d(64, 64, kernel_size=3),
            nn.ReLU(),
            nn.ReflectionPad2d((1, 1, 1, 1)),
            nn.Conv2d(64, 3, kernel_size=3)
        )

    def forward(self, x):
        return self.decoder(x)


# AdaIN 函数
def adain(content_features, style_features):
    eps = 1e-5

    content_mean = torch.mean(content_features, dim=[2, 3], keepdim=True)
    content_std = torch.std(content_features, dim=[2, 3], keepdim=True) + eps
    style_mean = torch.mean(style_features, dim=[2, 3], keepdim=True)
    style_std = torch.std(style_features, dim=[2, 3], keepdim=True) + eps

    normalized_features = (content_features - content_mean) / content_std
    return normalized_features * style_std + style_mean


# 风格迁移函数
def style_transfer(encoder, decoder, content, style, alpha=1.0):
    content_features = encoder(content)
    style_features = encoder(style)

    t = adain(content_features[-1], style_features[-1])
    t = alpha * t + (1 - alpha) * content_features[-1]

    g_t = decoder(t)

    return g_t


# 图像加载与处理
def load_image(path, size=None):
    transform = transforms.Compose([
        transforms.Resize(size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    image = PIL.Image.open(path).convert('RGB')
    image = transform(image).unsqueeze(0)

    return image


# 保存图像
def save_image(tensor, filename):
    image = tensor.cpu().clone()
    image = image.squeeze(0)
    image = unnormalize(image)

    torchvision.utils.save_image(image, filename)


# 反归一化
def unnormalize(tensor):
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

    return tensor * std + mean


# 主函数
def main(content_path, style_path, output_path, alpha=1.0, image_size=512):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 加载模型
    encoder = Encoder().to(device)
    decoder = Decoder().to(device)

    # 加载预训练权重（如果有）
    # decoder.load_state_dict(torch.load('decoder.pth'))

    # 加载图像
    content = load_image(content_path, size=image_size).to(device)
    style = load_image(style_path, size=image_size).to(device)

    # 执行风格迁移
    with torch.no_grad():
        output = style_transfer(encoder, decoder, content, style, alpha)

    # 保存结果
    save_image(output, output_path)
    print(f"Styled image saved to {output_path}")


# 使用示例
if __name__ == "__main__":

    content_image = '/ds1/workspace/moviepy-daily-news/news/20250717/bbc0/00/4bf9e050-60f0-11f0-ae6b-f98c94e089e3.png'
    style_image = '/ds1/workspace/moviepy-daily-news/news/20250717/bbc0/00/jojo.jpg'
    output_image = '/ds1/workspace/moviepy-daily-news/news/20250717/bbc0/00/out1.jpg'

    main(content_image, style_image, output_image, alpha=0.7)