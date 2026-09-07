"""资源路径解析：所有图标/样式/模型路径的唯一入口，避免依赖当前工作目录。"""
from __future__ import annotations

import sys
from pathlib import Path


def _base_dir() -> Path:
    """返回资源根目录，兼容 PyInstaller 冻结环境。"""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


ROOT_DIR = _base_dir()
PACKAGE_DIR = ROOT_DIR / "quant"
ASSETS_DIR = ROOT_DIR / "assets"
ICON_DIR = ASSETS_DIR / "icons"
STYLE_DIR = ASSETS_DIR / "styles"
MODEL_DIR = ASSETS_DIR / "models"


def resource_path(*parts: str) -> Path:
    """拼接 assets/ 下的资源路径。"""
    return ASSETS_DIR.joinpath(*parts)


def icon_path(name: str) -> str:
    """图标绝对路径（QIcon/QPixmap 接受 str）。"""
    return str(ICON_DIR / name)


def style_path(name: str) -> Path:
    """样式表绝对路径。"""
    return STYLE_DIR / name


def model_path(name: str) -> Path:
    """模型文件绝对路径，自动补 .pt 后缀。"""
    if not name.endswith(".pt"):
        name = f"{name}.pt"
    return MODEL_DIR / name
