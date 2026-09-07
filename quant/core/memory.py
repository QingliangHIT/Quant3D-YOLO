"""内存占用统计与格式化。"""
from __future__ import annotations

import sys
from typing import Any

_UNITS = ("B", "KB", "MB", "GB", "TB")


def deep_sizeof(obj: Any, _seen: set | None = None) -> int:
    """递归统计容器（dict/list/tuple/set）及其元素的内存占用（字节）。

    带环检测，避免自引用结构导致无限递归。
    """
    seen = _seen if _seen is not None else set()
    if id(obj) in seen:
        return 0
    seen.add(id(obj))

    total = sys.getsizeof(obj)
    if isinstance(obj, dict):
        items = list(obj.items())
    elif isinstance(obj, (list, tuple, set, frozenset)):
        items = [(None, value) for value in obj]
    else:
        return total

    for key, value in items:
        if key is not None:
            total += deep_sizeof(key, seen)
        total += deep_sizeof(value, seen)
    return total


def format_size(size_bytes: int) -> str:
    """把字节数格式化为带单位的可读字符串。"""
    size = float(size_bytes)
    for unit in _UNITS:
        if size < 1024 or unit == _UNITS[-1]:
            return f"{int(size)} B" if unit == "B" else f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def get_dict_memory_usage(data: Any) -> int:
    """兼容旧接口名。"""
    return deep_sizeof(data)


_CACHE_FIELDS = (
    ("yolo_results", "YOLO Results"),
    ("image_cache", "Image Cache"),
    ("label_cache", "Label Cache"),
    ("yolo_cache", "YOLO Cache"),
)


def cache_memory_report(yolo_results: Any, image_cache: Any, label_cache: Any, yolo_cache: Any) -> tuple:
    """统计四类缓存占用，返回 (状态栏单行文本, 控制台多行明细)。"""
    caches = {
        "yolo_results": yolo_results,
        "image_cache": image_cache,
        "label_cache": label_cache,
        "yolo_cache": yolo_cache,
    }
    sizes = {key: deep_sizeof(value) for key, value in caches.items()}
    total = sum(sizes.values())

    summary = ", ".join(f"{label}: {format_size(sizes[key])}" for key, label in _CACHE_FIELDS)
    status_text = f"Memory Usage - {summary}, Total: {format_size(total)}"

    details = ["Memory Usage Details:"]
    details += [
        f"  {label}: {format_size(sizes[key])} ({sizes[key]} bytes)" for key, label in _CACHE_FIELDS
    ]
    details.append(f"  Total: {format_size(total)} ({total} bytes)")
    return status_text, "\n".join(details)
