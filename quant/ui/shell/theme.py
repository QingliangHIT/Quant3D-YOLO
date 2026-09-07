"""主题（QSS）加载与应用。"""
from __future__ import annotations

from enum import Enum

from PyQt5 import QtWidgets

from quant.core.paths import style_path


class Theme(str, Enum):
    LIGHT = "Light"
    DARK = "Dark"

    @classmethod
    def parse(cls, value) -> "Theme":
        """容错解析主题名（兼容中英文与空值）。"""
        text = str(value or "").strip().lower()
        if text in ("dark", "深色", "暗色", "黑色"):
            return cls.DARK
        return cls.LIGHT


_QSS_FILE = {Theme.LIGHT: "light.qss", Theme.DARK: "dark.qss"}


def load_qss(theme: Theme) -> str:
    path = style_path(_QSS_FILE[theme])
    return path.read_text(encoding="utf-8") if path.exists() else ""


def apply_theme(widget: QtWidgets.QWidget, theme) -> Theme:
    """给 widget 应用主题，返回实际生效的 Theme。"""
    resolved = theme if isinstance(theme, Theme) else Theme.parse(theme)
    widget.setStyleSheet(load_qss(resolved))
    return resolved
