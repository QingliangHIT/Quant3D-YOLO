"""主窗口：仅负责装配与转发，具体行为分布在 quant/ui/shell/ 下的各个模块。"""

from PyQt5 import QtWidgets
from quant.ui.docks.volume_control_dock import Control3DDock
from quant.project.manager import ProjectManager
from quant.core.config import UI_CONFIG
from quant.ui.shell import shortcuts, menu_builder, view_switcher, window_builder, detection_controller, file_actions, view_actions, dialog_actions
from quant.ui.shell.theme import apply_theme


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.yolo_model = None
        self.yolo_model_name = None
        self.images_view_page = None
        self.plotter = None
        self.current_state = 0
        self.detector = None
        self.settings_dialog = None
        self.control3D_dock = None
        self.image_view_page = None
        self.images_view_page = None
        self.setup_variables()
        # Initialize settings
        self.setup_ui()
        self.project_manager = ProjectManager(self)  # Initialize project manager
        if not getattr(self, 'current_project_dir', None):
            self.statusbar.showMessage("⚠️ Please create or open a project first", 3000)

        self.control3D_dock = Control3DDock(self)
        self.setup_connections()
        QtWidgets.QApplication.processEvents()
        self.action_toggle_images_view.setChecked(True)
        self.toggle_images_view()
        self.check_state()
        self.change_theme(UI_CONFIG.default_theme)
        self.action_show_label.setChecked(True)
        self.action_show_yolo.setChecked(True)
        self.show_label()
        self.show_yolo()

    def check_state(self):
        view_switcher.check_state(self)

    def setup_variables(self):
        """
        Set application variables
        """
        self.current_file = None
        self.is_modified = False
        # Add mouse drag related variables
        self.mouse_pressed = False
        self.last_mouse_pos = None
        # Added: fixed size mode state variable
        self.is_fixed_size = True

    def setup_ui(self):
        window_builder.build_ui(self)

    def setup_menubar(self):
        window_builder.build_menubar(self)

    def setup_toolbar(self):
        window_builder.build_toolbar(self)

    def setup_docks(self):
        window_builder.build_docks(self)

    def setup_menu_items(self):
        menu_builder.build_menu_items(self)

    def setup_toolbar_buttons(self):
        window_builder.build_toolbar_buttons(self)

    def setup_connections(self):
        window_builder.connect_signals(self)

    def show_calibrator_dialog(self):
        dialog_actions.show_calibrator_dialog(self)

    def zoom_in(self):
        view_actions.zoom_in(self)

    def zoom_out(self):
        view_actions.zoom_out(self)

    def load_mask_calcu(self):
        dialog_actions.show_mask_control_dialog(self)

    def load_model(self):
        return detection_controller.load_model(self)

    def ensure_model(self):
        return detection_controller.ensure_model(self)

    def toggle_yolo_detection(self):
        detection_controller.toggle_yolo_detection(self)

    def toggle_yolo_point_detection(self):
        detection_controller.toggle_yolo_point_detection(self)

    def on_yolo_model_changed(self, message):
        return detection_controller.on_model_changed(self, message)

    def on_yolo_conf_threshold_changed(self, conf_threshold):
        detection_controller.on_conf_threshold_changed(self, conf_threshold)

    def on_yolo_iou_threshold_changed(self, iou_threshold):
        detection_controller.on_iou_threshold_changed(self, iou_threshold)

    def show_label(self):
        detection_controller.show_label(self)

    def show_yolo(self):
        detection_controller.show_yolo(self)

    def show_detect_results(self):
        detection_controller.show_detect_results(self)

    def realtime_detect(self):
        detection_controller.toggle_realtime_detect(self)

    def load_corner_detection(self):
        detection_controller.load_corner_detection(self)

    def change_theme(self, theme):
        """切换浅色/深色主题（样式表位于 assets/styles/）。"""
        self.current_theme = apply_theme(self, theme)

    def change_language(self, theme):
        dialog_actions.change_language(self, theme)

    def change_left_camera(self, camera_index):
        view_actions.change_left_camera(self, camera_index)

    def toggle_image_view(self):
        view_switcher.toggle_image_view(self)

    def toggle_images_view(self):
        view_switcher.toggle_images_view(self)

    def reload_img_view(self):
        view_actions.reload_current_view(self)

    def _show_image_view(self):
        view_switcher.show_image_view(self)

    def _show_images_view(self):
        view_switcher.show_images_view(self)

    def _hide_image_view(self):
        view_switcher.hide_image_view(self)

    def _hide_images_view(self):
        view_switcher.hide_images_view(self)

    def toggle_camera_view(self):
        view_switcher.toggle_camera_view(self)

    def toggle_fullscreen(self):
        view_actions.toggle_fullscreen(self)

    def toggle_fit_window(self):
        view_actions.toggle_fit_window(self)

    def retranslate_ui(self):
        window_builder.retranslate_ui(self)

    def show_about_dialog(self):
        dialog_actions.show_about_dialog(self)

    def closeEvent(self, event):
        dialog_actions.handle_close_event(self, event)

    def load_image(self):
        file_actions.open_images(self)

    def load_file(self, file_path):
        file_actions.open_file(self, file_path)

    def get_memory_usage(self):
        view_actions.report_memory_usage(self)

    def load_folder(self):
        return file_actions.open_folder(self)

    def load_save_dir(self):
        return file_actions.open_project_dir(self)

    def save_file(self):
        file_actions.save_file(self)

    def save_file_as(self):
        file_actions.save_file_as(self)

    def change_mask_opacity(self, opacity):
        view_actions.change_mask_opacity(self, opacity)

    def show_settings_dialog(self):
        dialog_actions.show_settings_dialog(self)

    def keyPressEvent(self, event):
        """全局快捷键（映射表见 quant/ui/shell/shortcuts.py）。"""
        if shortcuts.handle_key_press(self, event):
            event.accept()
            return
        super().keyPressEvent(event)
