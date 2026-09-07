"""全局静态配置。

按关注点拆分为 4 个不可变配置对象；文件末尾保留模块级常量别名，
使旧代码 `from quant.core.config import IconSize` 之类的写法在过渡期继续可用。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UiConfig:
    """界面外观与窗口尺寸。"""

    icon_size: int = 24
    font_family: str = "Times New Roman"
    font_size: int = 12
    window_size: tuple = (1600, 900)
    min_window_size: tuple = (800, 600)
    default_theme: str = "Light"


@dataclass(frozen=True)
class MetricConfig:
    """像素到物理尺寸的换算比例（mm）。"""

    dx: float = 14142.1 / 640
    dy: float = 14142.1 / 640
    dz: float = 5.0


@dataclass(frozen=True)
class DetectionConfig:
    """YOLO 检测相关的可选项与默认值。"""

    default_task: str = "auto"
    label_json_format: str = "labelme"
    # YOLO 参数面板可选的任务类型，取值须与 ultralytics 的 task 一致
    model_tasks: tuple = ("detect", "segment", "pose", "classify", "obb")
    # 标注面板任务档位循环顺序，default_task 必须出现在其中
    annotation_tasks: tuple = ("detect", "segment", "obb", "pose", "auto")
    # 参数面板模型下拉框的静态可选项：会与模型目录(assets/models)扫描到的本地 .pt
    # 合并展示（见 model_service.available_models），此处保留可联网自动下载的官方权重名
    available_models: tuple = (
        "hole",
        "yolov5nu",
        "yolov8n",
        "yolov8n-seg",
        "yolov8n-pose",
        "yolov8n-obb",
    )
    default_conf: float = 0.25
    default_iou: float = 0.70
    default_patch_percent: int = 50
    default_max_detections: int = 50
    # 模型未暂露 task / names 时的回退值（与 default_task 的 UI 初值语义不同）
    fallback_task: str = "segment"
    fallback_class_count: int = 1000


@dataclass(frozen=True)
class DisplayConfig:
    """标注显示开关的初始值。"""

    show_filtered: bool = True
    show_boxes: bool = True
    show_confidence: bool = False
    show_labels: bool = False
    cache_image: bool = False


UI_CONFIG = UiConfig()
METRIC = MetricConfig()
DETECTION = DetectionConfig()
DISPLAY = DisplayConfig()

# ---------------------------------------------------------------------------
# 兼容别名（过渡期保留，全部调用点迁移完成后可整体删除）
# ---------------------------------------------------------------------------
IconSize = UI_CONFIG.icon_size
dx, dy, dz = METRIC.dx, METRIC.dy, METRIC.dz
JSON = DETECTION.label_json_format
TASK = DETECTION.default_task
show_filtered = DISPLAY.show_filtered
show_boxes = DISPLAY.show_boxes
show_confidence = DISPLAY.show_confidence
show_labels = DISPLAY.show_labels
cache_image = DISPLAY.cache_image
