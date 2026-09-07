"""对话框动作：标定、掩码计算、设置、关于与窗口关闭确认。"""

import os
from PyQt5 import QtWidgets
from quant.ui.dialogs.calibration_dialog import CalibrationDialog
from quant.ui.dialogs.mask_control_dialog import MaskControlDialog
from quant.ui.dialogs.settings_dialog import SettingsDialog


def show_calibrator_dialog(window):
    if not hasattr(window, "calibrator_dialog"):
        folder_path = str(os.path.join(window.project_manager.current_project_dir, window.project_manager.save_dir))
        window.calibrator_dialog = CalibrationDialog(window, window.detector, square_size=40, image_dir=folder_path)
    window.calibrator_dialog.show()


def show_mask_control_dialog(window):
    control_dialog = MaskControlDialog(window)
    control_dialog.exec_()


def show_about_dialog(window):
    """
    Show about dialog
    """
    QtWidgets.QMessageBox.about(
        window,
        "About Quant",
        """<h1>Quant</h1>
        <p>Version 1.1.0</p>
        <p>Copyright © 2025. All rights reserved.</p>
        <hr>
        <p><b>Email:</b> 1349978767@qq.com</p>
        """
    )


def show_settings_dialog(window):
    if not window.settings_dialog:
        window.settings_dialog = SettingsDialog(window)
        # if window.camera_page.camera_available is None:
        #     window.camera_page.init_camera()
        window.settings_dialog.set_available_cameras(window.camera_page.camera_available)
        # Ensure signals and slots are correctly connected
        window.settings_dialog.theme_changed.connect(window.change_theme)
        window.settings_dialog.language_changed.connect(window.change_language)
        window.settings_dialog.left_camera_changed.connect(window.change_left_camera)
        window.settings_dialog.mask_opacity_changed.connect(window.change_mask_opacity)

    window.settings_dialog.show()


def change_language(window, theme):
    print("Language changed to:", theme)


def handle_close_event(window, event):
    """
    Override close event
    """
    window.project_manager.save_project()
    if window.is_modified:
        reply = QtWidgets.QMessageBox.question(
            window,
            "Confirm Close",
            "The document has been modified. Do you want to save your changes?",
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Save
        )

        if reply == QtWidgets.QMessageBox.Save:
            window.save_file()
            event.accept()
        elif reply == QtWidgets.QMessageBox.Discard:
            event.accept()
        else:
            event.ignore()
    else:
        event.accept()
