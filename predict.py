import argparse
import os
import time

import torch
from torchvision import transforms
import numpy as np
from PIL import Image

from src import deeplabv3_resnet50


def time_synchronized():
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    return time.time()


def main(args):
    aux = False  # inference time not need aux_classifier
    classes = 1
    weights_path = "./save_weights/best_model.pth"
    img_path = args.test_path
    assert os.path.exists(weights_path), f"weights {weights_path} not found."
    assert os.path.exists(img_path), f"image {img_path} not found."

    mean = (0.419, 0.432, 0.447)
    std = (0.084, 0.082, 0.082)
    # get devices
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"using {device} device.")

    # create model
    model = deeplabv3_resnet50(aux=aux, num_classes=classes+1)

    # delete weights about aux_classifier
    weights_dict = torch.load(weights_path, map_location='cpu')['model']
    for k in list(weights_dict.keys()):
        if "aux" in k:
            del weights_dict[k]

    # load weights
    model.load_state_dict(weights_dict)
    model.to(device)

    # load image
    original_img = Image.open(img_path)

    # from pil image to tensor and normalize
    data_transform = transforms.Compose([transforms.ToTensor(),
                                         transforms.Normalize(mean=mean, std=std)])
    img = data_transform(original_img)
    # expand batch dimension
    img = torch.unsqueeze(img, dim=0)

    model.eval()  # 进入验证模式
    with torch.no_grad():
        # init model
        img_height, img_width = img.shape[-2:]
        init_img = torch.zeros((1, 3, img_height, img_width), device=device)
        model(init_img)

        t_start = time_synchronized()
        output = model(img.to(device))
        t_end = time_synchronized()
        print(f"inference+NMS time: {t_end - t_start}")

        prediction = output['out'].argmax(1).squeeze(0)
        prediction = prediction.to("cpu").numpy().astype(np.uint8)
        # 将前景对应的像素值改成255(白色)
        prediction[prediction == 1] = 255
        # 将不敢兴趣的区域像素设置成0(黑色)
        prediction[prediction == 0] = 0
        mask = Image.fromarray(prediction)
        mask.save("test_result.png")


def parse_args():
    parser = argparse.ArgumentParser(description="pytorch unet predicting")
    # parser.add_argument('--model-flag', default='unet', type=str, help='model class flag')
    parser.add_argument('--test-path', default='./DRIVE/test/images/007.jpg', type=str, help='test image path')

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    main(args)
