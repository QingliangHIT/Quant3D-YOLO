"""检测控制器：YOLO 模型生命周期、检测开关与角点检测参数。

模型状态（yolo_model / yolo_model_name / plotter）只经 apply_model 写入，
加载与就绪判断只经 load_model / ensure_model，渲染器只经 rebuild_plotter 重建。
"""

import os

from PyQt5 import sip, QtWidgets
from quant.calibration.pattern_detector import CalibrationDetector
from quant.ui.dialogs.calibration_settings_dialog import CalibrationSettingsDialog
from quant.detection import model_service
from quant.detection.renderer import YOLOPlotter
from quant.ui.views.base_view import Viewer

# window.dock_dict 中 yolo_dock 的下标（与 window_builder.build_docks 的顺序一致）
YOLO_DOCK_INDEX = 6


def current_viewer(window):
    """返回当前图像视图页；当前页不是图像视图（相机页或未开页）时返回 None 并提示。"""
    widget = window.tab_widget.currentWidget()
    if isinstance(widget, Viewer) and not sip.isdeleted(widget):
        return widget
    window.statusbar.showMessage("⚠️ Please open an image view first", 3000)
    return None


def rebuild_plotter(window, task=None):
    """按当前模型重建渲染器；task 缺省时取模型自身任务类型。"""
    window.plotter = YOLOPlotter(task or model_service.model_task(window.yolo_model),
                                 model_service.model_names(window.yolo_model))
    return window.plotter


def ensure_plotter(window):
    """渲染器缺失时补建；已存在则保留（其中 task 可能来自用户手动选择）。"""
    if window.plotter is None:
        rebuild_plotter(window)
    return window.plotter


def apply_model(window, model, name):
    """模型状态的唯一写入点：同步实例、名称、参数面板与渲染器。"""
    window.yolo_model = model
    window.yolo_model_name = name
    task = model_service.model_task(model)
    names = model_service.model_names(model)
    # setCurrentText 会发 yolo_model_changed 导致 on_model_changed 重入，此处屏蔽信号
    window.yolo_dock.task_combo.blockSignals(True)
    window.yolo_dock.task_combo.setCurrentText(task)
    window.yolo_dock.task_combo.blockSignals(False)
    window.yolo_dock.update_content(names)
    window.plotter = YOLOPlotter(task, names)
    return task


def load_model(window):
    """按参数面板当前选择加载模型，返回是否成功。"""
    yolo_params = window.yolo_dock.get_parameters()
    if model_service.is_ready(window.yolo_model, window.yolo_model_name, yolo_params["model"]):
        return True

    try:
        model = model_service.load_model(yolo_params["model"])
    except model_service.ModelLoadError as exc:
        if exc.missing_dependency:
            QtWidgets.QMessageBox.warning(window, "Missing Dependency", str(exc))
        else:
            window.statusbar.showMessage(f"❌ {exc}", 8000)
        return False

    task = apply_model(window, model, yolo_params["model"])
    # 手动浏览时 yolo_model_name 可能是完整路径，只取文件名并保证带 .pt 后缀
    display_name = os.path.basename(window.yolo_model_name)
    if not display_name.lower().endswith(".pt"):
        display_name += ".pt"
    window.statusbar.showMessage(
        f"✅ Loaded YOLO model: {display_name} (Task: {task})", 3000)
    return True


def ensure_model(window):
    """确保已有可用模型；未就绪时按面板选择加载，返回是否可用。"""
    if model_service.is_ready(window.yolo_model, window.yolo_model_name):
        return True
    return load_model(window)


def invalidate_results(window):
    """模型变更后旧的检测结果与渲染缓存不再有效，需清掉后重算。"""
    for viewer in (window.image_view_page, window.images_view_page):
        if isinstance(viewer, Viewer) and not sip.isdeleted(viewer):
            viewer.yolo_results.clear()
            viewer.yolo_cache.clear()


def sync_yolo_dock(window):
    """按整图检测与点检测的合并状态同步 YOLO 面板可见性。

    两个开关共用同一个面板：任一开启就要显示，只有全部关闭才隐藏，
    避免关掉其中一个时把另一个仍在用的面板也藏掉。
    """
    active = bool(window.action_yolo_detect.isChecked() or window.action_yolo_point_detect.isChecked())
    if active:
        window.yolo_dock.setVisible(True)
        if YOLO_DOCK_INDEX not in window.image_view_page_source:
            window.image_view_page_source.append(YOLO_DOCK_INDEX)
    else:
        window.yolo_dock.setVisible(False)
        if YOLO_DOCK_INDEX in window.image_view_page_source:
            window.image_view_page_source.remove(YOLO_DOCK_INDEX)
    window.check_state()
    return active


def toggle_yolo_detection(window):
    """开关整图 YOLO 检测显示。"""
    enabled = window.action_yolo_detect.isChecked()
    if enabled and not ensure_model(window):
        window.action_yolo_detect.setChecked(False)
        return  # 加载失败时保持关闭，错误提示不被后续状态消息覆盖

    viewer = current_viewer(window)
    if viewer is None:
        window.action_yolo_detect.setChecked(False)
        sync_yolo_dock(window)
        return

    viewer.load_yolo_results = enabled
    sync_yolo_dock(window)
    window.files_dock.reload_current_image()
    window.statusbar.showMessage(f"YOLO Detection: {'ON' if enabled else 'OFF'}", 3000)


def toggle_yolo_point_detection(window):
    """开关点击式局部检测。"""
    enabled = window.action_yolo_point_detect.isChecked()
    if enabled and not ensure_model(window):
        window.action_yolo_point_detect.setChecked(False)
        return  # 加载失败时保持关闭，错误提示不被后续状态消息覆盖

    viewer = current_viewer(window)
    if viewer is None:
        window.action_yolo_point_detect.setChecked(False)
        sync_yolo_dock(window)
        return

    viewer.show_yolo_point_results = enabled
    if enabled:
        viewer.enable_point_detection_mode()
        window.statusbar.showMessage("Point Detection Mode: ON - Click image for local detection", 3000)
    else:
        viewer.disable_point_detection_mode()
        window.statusbar.showMessage("Point Detection Mode: OFF", 2000)
    sync_yolo_dock(window)


def on_model_changed(window, message):
    """参数面板切换模型或任务类型时同步模型状态与渲染器。"""
    kind, value = message[0], message[1]
    if kind == "model":
        if not load_model(window):
            return
        invalidate_results(window)
        window.files_dock.reload_current_image()
    elif kind == "task":
        if not load_model(window):
            return
        window.yolo_dock.update_content(model_service.model_names(window.yolo_model))
        rebuild_plotter(window, value)
        window.statusbar.showMessage(f"YOLO Task changed to: {value}", 2000)


def on_conf_threshold_changed(window, conf_threshold):
    """When confidence threshold changes"""
    window.statusbar.showMessage(f"YOLO Confidence Threshold: {conf_threshold}", 2000)


def on_iou_threshold_changed(window, iou_threshold):
    """When IOU threshold changes"""
    window.statusbar.showMessage(f"YOLO IOU Threshold: {iou_threshold}", 2000)


def show_label(window):
    """开关人工标注（标签文件）叠加显示。"""
    ensure_plotter(window)
    viewer = current_viewer(window)
    if viewer is None:
        return
    viewer.show_label = window.action_show_label.isChecked()
    viewer.label_cache.clear()
    window.files_dock.reload_current_image()


def show_yolo(window):
    """开关 YOLO 检测结果叠加显示。"""
    ensure_plotter(window)
    viewer = current_viewer(window)
    if viewer is None:
        return
    viewer.show_results = window.action_show_yolo.isChecked()
    window.files_dock.reload_current_image()


def show_detect_results(window):
    """开关标定角点检测结果叠加显示。"""
    viewer = current_viewer(window)
    if viewer is None:
        return
    viewer.show_detect_results = window.action_show_calibration.isChecked()
    if window.detector is None:
        window.detector = CalibrationDetector()
    window.files_dock.reload_current_image()


def toggle_realtime_detect(window):
    window.camera_page.realtime_detect = window.action_realtime_detect.isChecked()
    window.statusbar.showMessage("⚠️ Real-time detection will take effect next time...", 3000)


def load_corner_detection(window):
    # Get calibration parameters
    if window.action_corner_detector.isChecked():
        dialog = CalibrationSettingsDialog(window)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            settings = dialog.get_settings()
            window.statusbar.showMessage("Calibration Settings: " + str(settings), 3000)
            # Optional: save these settings for later use
            window.calibration_settings = settings
            window.inner_corners = window.calibration_settings['inner_corners']
            window.pattern_type = window.calibration_settings['pattern_type']
            # window.square_size = window.calibration_settings['square_size']
        # if not hasattr(window, 'calibration_settings'):
        #     QtWidgets.QMessageBox.warning(window, "Warning", "Please set calibration parameters first.")
        #     return
        if hasattr(window, 'inner_corners') and hasattr(window, 'pattern_type'):
            window.detector = CalibrationDetector(window.inner_corners, window.pattern_type)
            window.statusbar.showMessage("Corner Detection: ON", 2000)
    else:
        window.detector = None
        window.statusbar.showMessage("Corner Detection: OFF", 2000)
