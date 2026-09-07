"""掩码上色与叠加。"""
from __future__ import annotations

import cv2
import numpy as np

from quant.imaging.colors import COLORS


def colorize_mask(mask: np.ndarray, offset: int) -> np.ndarray:
    """把单通道掩码按调色板上色，返回与输入同 dtype 的图像。"""
    if mask.ndim not in (2, 3):
        return mask
    if mask.ndim == 3 and mask.shape[2] != 1:
        return mask

    color = COLORS[offset % len(COLORS)]
    if mask.max() <= 0:
        return mask

    normalized = mask.astype(np.float32) / mask.max()
    channels = [normalized * value for value in color]
    return cv2.merge(channels).astype(mask.dtype)


def blend_mask(image: np.ndarray, mask: np.ndarray, opacity: float, color_offset: int = 3) -> np.ndarray:
    """把上色后的掩码按透明度叠加到原图，仅覆盖掩码非零区域（原地修改 image）。"""
    if mask.shape[:2] != image.shape[:2]:
        mask = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)

    overlay = colorize_mask(mask, color_offset)
    blended = cv2.addWeighted(image, opacity, overlay, 1 - opacity, 0)
    image[mask > 0] = blended[mask > 0]
    return image


# 兼容旧接口名
get_img_color = colorize_mask
