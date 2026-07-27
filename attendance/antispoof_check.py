import os
import cv2
import torch
import numpy as np
import torch.nn.functional as F
from torchvision import transforms

from .antispoof_src.model_lib.MiniFASNet import MiniFASNetV1, MiniFASNetV2, MiniFASNetV1SE, MiniFASNetV2SE

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'antispoof_models')
DEVICE = torch.device("cpu")

MODEL_MAPPING = {
    'MiniFASNetV1': MiniFASNetV1,
    'MiniFASNetV2': MiniFASNetV2,
    'MiniFASNetV1SE': MiniFASNetV1SE,
    'MiniFASNetV2SE': MiniFASNetV2SE,
}

def parse_model_name(model_name):
    info = model_name.split('_')[0:-1]
    h_input, w_input = info[-1].split('x')
    model_type = model_name.split('.pth')[0].split('_')[-1]
    scale = None if info[0] == "org" else float(info[0])
    return int(h_input), int(w_input), model_type, scale

def get_kernel(height, width):
    return ((height + 15) // 16, (width + 15) // 16)

def _load_model(model_path):
    model_name = os.path.basename(model_path)
    h_input, w_input, model_type, scale = parse_model_name(model_name)
    kernel_size = get_kernel(h_input, w_input)
    model = MODEL_MAPPING[model_type](conv6_kernel=kernel_size).to(DEVICE)

    state_dict = torch.load(model_path, map_location=DEVICE)
    keys = iter(state_dict)
    first_layer_name = next(keys)

    if first_layer_name.find('module.') >= 0:
        from collections import OrderedDict
        new_state_dict = OrderedDict()
        for key, value in state_dict.items():
            new_state_dict[key[7:]] = value
        model.load_state_dict(new_state_dict)
    else:
        model.load_state_dict(state_dict)

    model.eval()
    return model, scale, (w_input, h_input)


# ---------------------------------------------------------------------------
# PERFORMANCE FIX: load every anti-spoof model ONCE when this module is first
# imported (i.e. once when the Django server starts), instead of reloading
# both .pth files from disk on every single frame of every request. This was
# the main cause of slow/laggy responses during live attendance marking.
# ---------------------------------------------------------------------------
_MODEL_CACHE = []
for _model_file in os.listdir(MODEL_DIR):
    if _model_file.endswith('.pth'):
        _model_path = os.path.join(MODEL_DIR, _model_file)
        _model, _scale, _out_size = _load_model(_model_path)
        _MODEL_CACHE.append((_model_file, _model, _scale, _out_size))


def _get_new_box(src_w, src_h, bbox, scale):
    x, y, box_w, box_h = bbox
    scale = min((src_h - 1) / box_h, min((src_w - 1) / box_w, scale))
    new_width = box_w * scale
    new_height = box_h * scale
    center_x, center_y = box_w / 2 + x, box_h / 2 + y

    left_top_x = center_x - new_width / 2
    left_top_y = center_y - new_height / 2
    right_bottom_x = center_x + new_width / 2
    right_bottom_y = center_y + new_height / 2

    if left_top_x < 0:
        right_bottom_x -= left_top_x
        left_top_x = 0
    if left_top_y < 0:
        right_bottom_y -= left_top_y
        left_top_y = 0
    if right_bottom_x > src_w - 1:
        left_top_x -= right_bottom_x - src_w + 1
        right_bottom_x = src_w - 1
    if right_bottom_y > src_h - 1:
        left_top_y -= right_bottom_y - src_h + 1
        right_bottom_y = src_h - 1

    return int(left_top_x), int(left_top_y), int(right_bottom_x), int(right_bottom_y)


def _crop_face(image_bgr, bbox_xyxy, scale, out_size):
    x1, y1, x2, y2 = bbox_xyxy
    bbox = (x1, y1, x2 - x1, y2 - y1)
    src_h, src_w = image_bgr.shape[0], image_bgr.shape[1]

    if scale is None:
        return cv2.resize(image_bgr, out_size)

    left_top_x, left_top_y, right_bottom_x, right_bottom_y = _get_new_box(src_w, src_h, bbox, scale)
    cropped = image_bgr[left_top_y:right_bottom_y + 1, left_top_x:right_bottom_x + 1]

    if cropped.size == 0:
        cropped = image_bgr

    return cv2.resize(cropped, out_size)


_transform = transforms.Compose([transforms.ToTensor()])

def check_real_or_fake(image_bgr, bbox, threshold=0.01):
    """
    image_bgr: full captured frame (numpy array, BGR)
    bbox: (x1, y1, x2, y2) from InsightFace's face detection
    threshold: minimum "real" class probability (averaged across models)
               required to classify as real. Calibrated empirically.

    Returns: (label, confidence) where label is "real" or "fake"
    """
    prediction = np.zeros((1, 3))

    for model_file, model, scale, out_size in _MODEL_CACHE:
        face_crop = _crop_face(image_bgr, bbox, scale, out_size)
        tensor = _transform(face_crop).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            result = model(tensor)
            result = F.softmax(result, dim=1).cpu().numpy()

        prediction += result

    real_score = prediction[0][1] / len(_MODEL_CACHE)

    if real_score > threshold:
        return "real", float(real_score)
    else:
        return "fake", float(real_score)


# import os
# import cv2
# import torch
# import numpy as np
# import torch.nn.functional as F
# from torchvision import transforms

# from .antispoof_src.model_lib.MiniFASNet import MiniFASNetV1, MiniFASNetV2, MiniFASNetV1SE, MiniFASNetV2SE

# MODEL_DIR = os.path.join(os.path.dirname(__file__), 'antispoof_models')
# DEVICE = torch.device("cpu")

# MODEL_MAPPING = {
#     'MiniFASNetV1': MiniFASNetV1,
#     'MiniFASNetV2': MiniFASNetV2,
#     'MiniFASNetV1SE': MiniFASNetV1SE,
#     'MiniFASNetV2SE': MiniFASNetV2SE,
# }

# def parse_model_name(model_name):
#     info = model_name.split('_')[0:-1]
#     h_input, w_input = info[-1].split('x')
#     model_type = model_name.split('.pth')[0].split('_')[-1]
#     scale = None if info[0] == "org" else float(info[0])
#     return int(h_input), int(w_input), model_type, scale

# def get_kernel(height, width):
#     return ((height + 15) // 16, (width + 15) // 16)

# def _load_model(model_path):
#     model_name = os.path.basename(model_path)
#     h_input, w_input, model_type, scale = parse_model_name(model_name)
#     kernel_size = get_kernel(h_input, w_input)
#     model = MODEL_MAPPING[model_type](conv6_kernel=kernel_size).to(DEVICE)

#     state_dict = torch.load(model_path, map_location=DEVICE)
#     keys = iter(state_dict)
#     first_layer_name = next(keys)

#     if first_layer_name.find('module.') >= 0:
#         from collections import OrderedDict
#         new_state_dict = OrderedDict()
#         for key, value in state_dict.items():
#             new_state_dict[key[7:]] = value
#         model.load_state_dict(new_state_dict)
#     else:
#         model.load_state_dict(state_dict)

#     model.eval()
#     return model, scale, (w_input, h_input)


# def _get_new_box(src_w, src_h, bbox, scale):
#     x, y, box_w, box_h = bbox
#     scale = min((src_h - 1) / box_h, min((src_w - 1) / box_w, scale))
#     new_width = box_w * scale
#     new_height = box_h * scale
#     center_x, center_y = box_w / 2 + x, box_h / 2 + y

#     left_top_x = center_x - new_width / 2
#     left_top_y = center_y - new_height / 2
#     right_bottom_x = center_x + new_width / 2
#     right_bottom_y = center_y + new_height / 2

#     if left_top_x < 0:
#         right_bottom_x -= left_top_x
#         left_top_x = 0
#     if left_top_y < 0:
#         right_bottom_y -= left_top_y
#         left_top_y = 0
#     if right_bottom_x > src_w - 1:
#         left_top_x -= right_bottom_x - src_w + 1
#         right_bottom_x = src_w - 1
#     if right_bottom_y > src_h - 1:
#         left_top_y -= right_bottom_y - src_h + 1
#         right_bottom_y = src_h - 1

#     return int(left_top_x), int(left_top_y), int(right_bottom_x), int(right_bottom_y)


# def _crop_face(image_bgr, bbox_xyxy, scale, out_size):
#     x1, y1, x2, y2 = bbox_xyxy
#     bbox = (x1, y1, x2 - x1, y2 - y1)
#     src_h, src_w = image_bgr.shape[0], image_bgr.shape[1]

#     if scale is None:
#         return cv2.resize(image_bgr, out_size)

#     left_top_x, left_top_y, right_bottom_x, right_bottom_y = _get_new_box(src_w, src_h, bbox, scale)
#     cropped = image_bgr[left_top_y:right_bottom_y + 1, left_top_x:right_bottom_x + 1]

#     if cropped.size == 0:
#         cropped = image_bgr

#     return cv2.resize(cropped, out_size)


# _transform = transforms.Compose([transforms.ToTensor()])


# # Threshold Value
# def check_real_or_fake(image_bgr, bbox, threshold=0.01):
#     """
#     image_bgr: full captured frame (numpy array, BGR)
#     bbox: (x1, y1, x2, y2) from InsightFace's face detection
#     threshold: minimum "real" class probability (averaged across models)
#                required to classify as real. Lower this if genuine faces
#                keep getting rejected; raise it if spoofs keep passing.

#     Returns: (label, confidence) where label is "real" or "fake"
#     """
#     prediction = np.zeros((1, 3))
#     model_files = [f for f in os.listdir(MODEL_DIR) if f.endswith('.pth')]

#     for model_file in model_files:
#         model_path = os.path.join(MODEL_DIR, model_file)
#         model, scale, out_size = _load_model(model_path)

#         face_crop = _crop_face(image_bgr, bbox, scale, out_size)
#         cv2.imwrite(f'debug_crop_{model_file}.jpg', face_crop)

#         tensor = _transform(face_crop).unsqueeze(0).to(DEVICE)

#         with torch.no_grad():
#             result = model(tensor)
#             result = F.softmax(result, dim=1).cpu().numpy()

#         print(f"DEBUG {model_file}: raw softmax = {result}")
#         prediction += result

#     # Class index 1 = "real" in this model's convention.
#     # Average the "real" probability across however many models we ran.
#     real_score = prediction[0][1] / len(model_files)

#     print(f"DEBUG total prediction: {prediction}, real_score={real_score}")

#     if real_score > threshold:
#         return "real", float(real_score)
#     else:
#         return "fake", float(real_score)