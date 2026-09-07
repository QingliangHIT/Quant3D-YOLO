"""标注绘制：把 results_label 结构直接画到 OpenCV 图像上（纯函数，无状态）。"""
from __future__ import annotations

import cv2
import numpy as np

from quant.imaging.colors import COLORS


def adaptive_style(width: int, height: int) -> tuple:
    """按图像尺寸自适应线宽与字号，返回 (line_thickness, font_scale)。"""
    line_thickness = max(1, int(min(width, height) / 432))
    font_scale = min(width, height) / 1080.0
    return line_thickness, font_scale


def _clip(value, low: int, high: int) -> int:
    return max(low, min(value, high))


def _draw_label(img, text: str, origin, color, font_scale: float, line_thickness: int):
    """在 origin 上方绘制带底色的文字标签。"""
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, max(1, line_thickness // 2))[0]
    label_bg_height = int(1.5 * text_size[1])
    x, y = int(origin[0]), int(origin[1])
    cv2.rectangle(img, (x, y - label_bg_height), (x + text_size[0], y), color, -1)
    cv2.putText(img, text, (x, y - max(2, label_bg_height // 4)),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), max(1, line_thickness // 2))


def draw_boxes(img, boxes_data, names, height: int, width: int,
               line_thickness: int, font_scale: float, show_conf: bool, show_labels: bool, offset: int = 0):
    """绘制水平边界框（box = [x1, y1, x2, y2, conf, class_id]）。"""
    for box in boxes_data:
        x1, y1, x2, y2 = box[:4]
        confidence = box[4]
        class_id = int(box[5])

        x1 = _clip(x1, 0, width - 1)
        y1 = _clip(y1, 0, height - 1)
        x2 = _clip(x2, 0, width - 1)
        y2 = _clip(y2, 0, height - 1)

        class_name = names.get(class_id, f"{class_id}")
        color = COLORS[(class_id + offset) % len(COLORS)]
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, line_thickness)

        if show_labels or show_conf:
            parts = []
            if show_labels:
                parts.append(class_name)
            if show_conf:
                parts.append(f"{confidence:.2f}")
            if parts:
                _draw_label(img, " ".join(parts), (x1, y1), color, font_scale, line_thickness)
    return img


def draw_masks(img, masks_data, height: int, width: int, offset: int = 0, opacity: float = 0.5):
    """绘制分割多边形掩码（mask_info = [class_id, x1, y1, x2, y2, ...]）。"""
    mask_img = np.zeros_like(img)
    for mask_info in masks_data:
        class_id = int(mask_info[0])
        points = mask_info[1:]
        if len(points) < 6 or len(points) % 2 != 0:
            continue
        color = COLORS[(class_id + offset) % len(COLORS)]
        pts = [[_clip(int(points[j]), 0, width - 1), _clip(int(points[j + 1]), 0, height - 1)]
               for j in range(0, len(points), 2)]
        if len(pts) >= 3:
            cv2.fillPoly(mask_img, [np.array(pts, np.int32).reshape((-1, 1, 2))], color)
    return cv2.addWeighted(img, 1.0, mask_img, opacity, 0)


def draw_keypoints(img, keypoints_data, width: int, height: int, line_thickness: int):
    """绘制关键点（conf > 0 才可见）。"""
    for kps in keypoints_data:
        for kp in kps:
            x, y, conf = kp
            if conf > 0:
                cv2.circle(img, (int(_clip(x, 0, width - 1)), int(_clip(y, 0, height - 1))),
                           line_thickness * 2, (0, 255, 0), -1)
    return img


def draw_obb(img, obb_data, names, height: int, width: int,
             line_thickness: int, font_scale: float, show_conf: bool, show_labels: bool, offset: int = 0):
    """绘制旋转边界框（obb = [class_id, x1, y1, ..., x4, y4]）。"""
    for obb in obb_data:
        class_id = int(obb[0])
        points = obb[1:]
        if len(points) != 8:
            continue
        color = COLORS[(class_id + offset) % len(COLORS)]
        pts = [(_clip(points[j], 0, width - 1), _clip(points[j + 1], 0, height - 1)) for j in range(0, 8, 2)]
        for j in range(4):
            cv2.line(img, pts[j], pts[(j + 1) % 4], color, line_thickness)

        if show_labels or show_conf:
            class_name = names.get(class_id, f"class_{class_id}")
            parts = [class_name] if show_labels else []
            if parts:
                _draw_label(img, " ".join(parts), pts[0], color, font_scale, line_thickness)
    return img


def render_annotation(img, results_label: dict, names: dict, task: str = "detect", offset: int = 0,
                      show_boxes: bool = True, show_conf: bool = False, show_labels: bool = False):
    """把 results_label 中的框/掩码/关键点/旋转框绘制到 img 上。

    仅负责绘制；按类别过滤由上层（detection.renderer）先完成。
    """
    height, width = img.shape[:2]
    show_masks = task != "detect"
    if not show_masks and not show_boxes:
        show_boxes = True

    try:
        line_thickness, font_scale = adaptive_style(width, height)
        boxes_data = results_label.get("boxes", [])
        masks_data = results_label.get("masks", [])
        keypoints_data = results_label.get("keypoints", [])
        obb_data = results_label.get("obb", [])
        label_names = results_label.get("names", names)

        if show_boxes and boxes_data:
            img = draw_boxes(img, boxes_data, label_names, height, width,
                             line_thickness, font_scale, show_conf, show_labels, offset)
        if show_masks and masks_data:
            img = draw_masks(img, masks_data, height, width, offset)
        if keypoints_data:
            img = draw_keypoints(img, keypoints_data, width, height, line_thickness)
        if obb_data:
            img = draw_obb(img, obb_data, label_names, height, width,
                           line_thickness, font_scale, show_conf, show_labels, offset)
        return img
    except Exception as exc:  # noqa: BLE001 - 绘制失败不应中断浏览
        print(f"Error processing YOLO results: {exc}")
        return img
