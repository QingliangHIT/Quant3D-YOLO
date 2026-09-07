"""GPU 显存信息（GPUtil 为可选依赖）。"""
from __future__ import annotations


def gpu_memory_report() -> str:
    """返回所有 GPU 的显存占用文本。"""
    try:
        import GPUtil
    except ImportError:
        return "GPUtil not installed"

    lines = [
        f"GPU {i}: {gpu.name} | Memory Used: {gpu.memoryUsed}MB / {gpu.memoryTotal}MB"
        for i, gpu in enumerate(GPUtil.getGPUs())
    ]
    return "\n".join(lines) if lines else "No GPU detected"


def log_gpu_memory() -> None:
    print(gpu_memory_report())


def print_gpu_memory_usage(ret: bool = False):
    """兼容旧接口：ret=True 返回文本，否则打印并返回 None。"""
    report = gpu_memory_report()
    if ret:
        return report
    print(report)
    return None
