"""YOLO 模型加载与元信息解析。

集中处理 ultralytics 的惰性导入、权重加载、类别名与任务类型解析；
UI 层只负责状态提示与控件刷新，不再直接依赖 ultralytics。
"""
from __future__ import annotations

import os

from quant.core.config import DETECTION
from quant.core.paths import MODEL_DIR, model_path

DEFAULT_TASK = "segment"
DEFAULT_NAMES = {index: f"class_{index}" for index in range(1000)}


class ModelLoadError(RuntimeError):
    """模型加载失败。

    missing_dependency 为 True 表示缺少 ultralytics，需要提示用户安装依赖；
    否则是权重文件本身不可用。
    """

    def __init__(self, message: str, missing_dependency: bool = False):
        super().__init__(message)
        self.missing_dependency = missing_dependency


def is_ready(model, name, expected: str | None = None) -> bool:
    """判断模型状态是否可用。

    模型实例与名称是一对必须同步的状态：两者缺一即视为未就绪。
    传入 expected 时还要求已加载的就是该名称，用于判断是否需要重新加载。
    """
    if model is None or not name:
        return False
    return expected is None or name == expected


def resolve_weights(model_name: str) -> str:
    """把模型名解析为权重文件路径。

    优先查 assets/models/，其次按当前工作目录查找（兼容自备权重），
    避免权重文件随工作目录变化而找不到。
    """
    if os.path.basename(model_name) != model_name:
        return model_name  # 已含路径，直接使用
    bundled = model_path(model_name)
    if bundled.is_file():
        return str(bundled)
    return f"{model_name}.pt"


def list_local_models() -> list:
    """扫描模型目录，返回目录内所有 .pt 权重名（不含扩展名），按字母排序。"""
    if not MODEL_DIR.is_dir():
        return []
    return sorted(path.stem for path in MODEL_DIR.glob("*.pt") if path.is_file())


def available_models() -> list:
    """合并静态可选模型与模型目录扫描到的本地权重。

    静态项（DETECTION.available_models，含可联网自动下载的 yolov8n 等）保持在前，
    目录中新增的本地权重（如 holeX）追加在后，按名称去重。
    """
    merged = list(DETECTION.available_models)
    for name in list_local_models():
        if name not in merged:
            merged.append(name)
    return merged


def load_model(model_name: str):
    """按名称加载 `<model_name>.pt` 权重，返回 ultralytics YOLO 实例。"""
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise ModelLoadError(
            "Using YOLO detection requires installing the ultralytics library.\n"
            "Please run: pip install ultralytics",
            missing_dependency=True,
        ) from exc

    try:
        return YOLO(resolve_weights(model_name))
    except Exception as exc:
        raise ModelLoadError(f"Model loading failed: {exc}") from exc


def model_names(model) -> dict:
    """读取模型类别表；模型未加载或未暴露 names 时回退到占位类别名。"""
    names = getattr(model, "names", None)
    return dict(names) if names else dict(DEFAULT_NAMES)


def model_task(model, fallback: str = DEFAULT_TASK) -> str:
    """读取模型任务类型；缺失时回退到 fallback。"""
    return getattr(model, "task", None) or fallback


def describe(model) -> tuple:
    """返回 (task, names)，供渲染器构造使用。"""
    return model_task(model), model_names(model)
