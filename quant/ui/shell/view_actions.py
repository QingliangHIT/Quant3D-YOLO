"""视图动作：缩放、全屏、适应窗口、重载当前图、掩码透明度与内存报告。"""

from quant.ui.views.image_view import ImageViewer
from quant.ui.views.batch_image_view import ImagesViewer
from quant.core.memory import cache_memory_report


def zoom_in(window):
    """放大当前视图"""
    current_widget = window.tab_widget.currentWidget()
    if hasattr(current_widget, 'zoom_in'):
        current_widget.zoom_in()
        window.statusbar.showMessage("Zoomed in", 1000)


def zoom_out(window):
    """缩小当前视图"""
    current_widget = window.tab_widget.currentWidget()
    if hasattr(current_widget, 'zoom_out'):
        current_widget.zoom_out()
        window.statusbar.showMessage("Zoomed out", 1000)


def toggle_fullscreen(window):
    """
    Toggle fullscreen mode
    """
    if window.isFullScreen():
        window.showNormal()
    else:
        window.showFullScreen()


def toggle_fit_window(window):
    """
    Toggle fixed image size mode
    """
    window.is_fixed_size = not window.is_fixed_size
    if window.is_fixed_size:
        window.statusbar.showMessage("Fixed size mode enabled.", 2000)
        # window.action_fit_window.setIcon(QtGui.QIcon("icon/full_width_active.svg"))
    else:
        window.statusbar.showMessage("Fixed size mode disabled.", 2000)


def reload_current_view(window):
    current_widget = window.tab_widget.currentWidget()
    file_path = current_widget.img[0]
    if file_path in current_widget.yolo_cache:
        del current_widget.yolo_cache[file_path]
    current_widget.load_file(file_path)


def change_mask_opacity(window, opacity):
    current_widget = window.tab_widget.currentWidget()
    current_widget.mask_opacity = opacity
    if isinstance(current_widget, (ImageViewer, ImagesViewer)) and current_widget.img:
        current_widget.load_file(current_widget.img[0])
    window.statusbar.showMessage(f"Mask Opacity: {int(opacity * 100)}%", 2000)


def report_memory_usage(window):
    """统计各类缓存占用并显示在状态栏。"""
    current_widget = window.tab_widget.currentWidget()
    status_text, detail_text = cache_memory_report(
        current_widget.yolo_results,
        current_widget.image_cache,
        current_widget.label_cache,
        current_widget.yolo_cache,
    )
    window.statusbar.showMessage(status_text, 5000)
    print(detail_text)


def change_left_camera(window, camera_index):
    """
    Switch left camera index
    """
    if window.camera_page:
        window.camera_page.camera_index = camera_index
