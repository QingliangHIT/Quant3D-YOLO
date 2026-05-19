import sys
import GPUtil
import cv2
import numpy as np
from UI.tools.tool_plot_yolo import COLORS


def get_dict_memory_usage(d):
    """
    Calculate memory usage of a dictionary and all its nested objects

    :param d: Dictionary to calculate memory usage for
    :return: Memory usage size (bytes)
    """
    if not isinstance(d, dict):
        return sys.getsizeof(d)

    total_size = sys.getsizeof(d)

    for key, value in d.items():
        # Calc key size
        total_size += sys.getsizeof(key)

        # Recursively calc value size
        if isinstance(value, dict):
            total_size += get_dict_memory_usage(value)
        elif isinstance(value, list):
            total_size += get_list_memory_usage(value)
        elif isinstance(value, tuple):
            total_size += get_tuple_memory_usage(value)
        else:
            total_size += sys.getsizeof(value)

    return total_size

def get_list_memory_usage(lst):
    """
    Calc list memory usage
    """
    if not isinstance(lst, list):
        return sys.getsizeof(lst)

    total_size = sys.getsizeof(lst)

    for item in lst:
        if isinstance(item, dict):
            total_size += get_dict_memory_usage(item)
        elif isinstance(item, list):
            total_size += get_list_memory_usage(item)
        elif isinstance(item, tuple):
            total_size += get_tuple_memory_usage(item)
        else:
            total_size += sys.getsizeof(item)

    return total_size

def get_tuple_memory_usage(tpl):
    """
    Calc tuple memory usage
    """
    if not isinstance(tpl, tuple):
        return sys.getsizeof(tpl)

    total_size = sys.getsizeof(tpl)

    for item in tpl:
        if isinstance(item, dict):
            total_size += get_dict_memory_usage(item)
        elif isinstance(item, list):
            total_size += get_list_memory_usage(item)
        elif isinstance(item, tuple):
            total_size += get_tuple_memory_usage(item)
        else:
            total_size += sys.getsizeof(item)

    return total_size

def print_gpu_memory_usage(ret=False):
    # 调用函数打印显存使用情况
    GPUs = GPUtil.getGPUs()
    used = ''
    for i, gpu in enumerate(GPUs):
        used += f"GPU {i}: {gpu.name} | Memory Used: {gpu.memoryUsed}MB / {gpu.memoryTotal}MB\n"
    if ret:
        return used
    else:
        print(used)
        return None


def get_img_color(img, offset):
    if len(img.shape) == 2 or (len(img.shape) == 3 and img.shape[2] == 1):
        color = COLORS[(offset) % len(COLORS)]
        if img.max() > 0:
            img_normalized = img.astype(np.float32) / img.max()
            img = cv2.merge([
                img_normalized * color[0],
                img_normalized * color[1],
                img_normalized * color[2]
            ]).astype(img.dtype)
    return img


# Usage example
# Assume you have a dict variable my_dict
# memory_usage = get_dict_memory_usage(my_dict)
# print(f"Dict memory usage: {memory_usage} bytes")
# print(f"Dict memory usage: {memory_usage / 1024:.2f} KB")
# print(f"Dict memory usage: {memory_usage / (1024 * 1024):.2f} MB")
