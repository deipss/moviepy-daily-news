import torch
from PIL import Image
import argparse

from models.module_photo2pixel import Photo2PixelModel
from models import img_common_util


def convert(input_img:str, output_img:str, k=8, p=3, e=192):

    img_input = Image.open(input_img)
    img_pt_input = img_common_util.convert_image_to_tensor(img_input)

    model = Photo2PixelModel()
    model.eval()
    with torch.no_grad():
        img_pt_output = model(
            img_pt_input,
            param_kernel_size=k,
            param_pixel_size=p,
            param_edge_thresh=e
        )
    img_output = img_common_util.convert_tensor_to_image(img_pt_output)
    img_output.save(output_img)



