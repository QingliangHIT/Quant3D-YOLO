"""标注调色板（BGR）。"""
from __future__ import annotations

COLORS = (
    (0, 0, 255),      # Red
    (0, 255, 0),      # Green
    (255, 0, 0),      # Blue
    (255, 255, 0),    # Cyan
    (255, 0, 255),    # Purple
    (0, 255, 255),    # Yellow
    (128, 0, 128),    # Dark purple
    (0, 128, 128),    # Dark cyan
    (128, 128, 0),    # Dark yellow
    (128, 128, 128),  # Gray
)


def color_for(class_id: int, offset: int = 0) -> tuple:
    """按类别 id 与全局色偏取色，越界自动回绕。"""
    return COLORS[(class_id + offset) % len(COLORS)]
