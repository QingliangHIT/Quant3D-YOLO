"""全局快捷键分发。

主窗口只负责把按键事件交给 handle_key_press，具体映射集中在此处维护。
"""
from __future__ import annotations

from PyQt5.QtCore import Qt


def _shift_color_offset(window, delta: int) -> None:
    """调整标注色偏并在状态栏提示。"""
    plotter = getattr(window, "plotter", None)
    if plotter is None:
        return
    plotter.offset += delta
    window.statusbar.showMessage(f"Color Offset: {plotter.offset}", 2000)


def handle_navigation(window, event, key) -> bool:
    """无修饰键的 A/D/W/S 图像翻页。"""
    handlers = {
        Qt.Key_A: window.files_dock.prev_image,
        Qt.Key_D: window.files_dock.next_image,
        Qt.Key_W: window.files_dock.to_first_image,
        Qt.Key_S: window.files_dock.to_last_image,
    }
    handler = handlers.get(key)
    if handler is None:
        return False
    handler(event)
    return True


def handle_key_press(window, event) -> bool:
    """处理图像浏览相关的快捷键；返回 True 表示事件已消费。"""
    from quant.ui.views.batch_image_view import ImagesViewer
    from quant.ui.views.image_view import ImageViewer

    current_widget = window.tab_widget.currentWidget()
    if not isinstance(current_widget, (ImageViewer, ImagesViewer)):
        return False

    key = event.key()
    modifiers = event.modifiers()
    has_modifier = modifiers != Qt.NoModifier

    if not has_modifier:
        return handle_navigation(window, event, key)

    if key == Qt.Key_M:
        window.get_memory_usage()
        return True

    if key == Qt.Key_C:
        # Ctrl+Shift+C 反向偏移，其余组合键正向偏移
        _shift_color_offset(window, -1 if modifiers == (Qt.ControlModifier | Qt.ShiftModifier) else 1)
        return True

    if key == Qt.Key_R and modifiers == Qt.ControlModifier:
        current_widget.reset_view()
        return True

    if key == Qt.Key_R and modifiers == (Qt.ControlModifier | Qt.ShiftModifier):
        current_widget.reset_results()
        return True

    return False
