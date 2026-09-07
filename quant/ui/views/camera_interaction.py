"""相机视图交互：滚轮缩放、中键拖拽平移与浮动按钮自动隐藏。"""

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt


def on_wheel(view, event):
    if not view.parent.is_fixed_size:
        delta = event.angleDelta().y()
        if delta > 0:
            view.graphics_view.scale(1.1, 1.1)
        elif delta < 0:
            view.graphics_view.scale(0.9, 0.9)
    event.accept()


def on_mouse_press(view, event):
    if event.button() == Qt.MouseButton.MiddleButton or event.button() == Qt.MouseButton.RightButton:
        view.mouse_pressed = True
        view.last_mouse_pos = event.pos()
        view.graphics_view.setCursor(Qt.ClosedHandCursor)
    elif event.button() == Qt.MouseButton.LeftButton and view.label.isVisible() and view.label.geometry().contains(
            event.pos()):
        view.start_camera(mode=view.parent.mode)
    elif event.button() == Qt.MouseButton.LeftButton:
        if view.close_button.isVisible():
            view.reset_hide_timer()
        else:
            view.close_button.show()
            view.switch_camera_btn.setText(str(view.camera_index))
            view.switch_camera_btn.show()
            view.close_button.move(view.graphics_view.width() - view.close_button.width() - 10, 10)
            view.switch_camera_btn.move(
                view.close_button.x() - view.switch_camera_btn.width() - 8,
                view.close_button.y()
            )
    else:
        QtWidgets.QGraphicsView.mousePressEvent(view.graphics_view, event)


def on_mouse_move(view, event):
    if view.mouse_pressed:
        delta = event.pos() - view.last_mouse_pos
        view.last_mouse_pos = event.pos()
        h_scroll = view.graphics_view.horizontalScrollBar()
        v_scroll = view.graphics_view.verticalScrollBar()
        h_scroll.setValue(h_scroll.value() - delta.x())
        v_scroll.setValue(v_scroll.value() - delta.y())


def on_mouse_release(view, event):
    if event.button() == Qt.MiddleButton:
        view.mouse_pressed = False
        view.graphics_view.setCursor(Qt.ArrowCursor)
    else:
        QtWidgets.QGraphicsView.mouseReleaseEvent(view.graphics_view, event)


def on_mouse_double_click(view, event):
    if event.button() == Qt.MouseButton.LeftButton:
        view.graphics_view.fitInView(view.pixmap_item, Qt.KeepAspectRatio)


def reset_hide_timer(view):
    """Reset hide button timer"""
    if hasattr(view, 'hide_timer'):
        view.hide_timer.stop()
    view.hide_timer = QtCore.QTimer(view)
    view.hide_timer.setSingleShot(True)
    view.hide_timer.timeout.connect(view.hide_floating_button)
    view.hide_timer.start(2000)


def hide_floating_button(view):
    """Hide close button"""
    view.close_button.hide()
    view.switch_camera_btn.hide()
