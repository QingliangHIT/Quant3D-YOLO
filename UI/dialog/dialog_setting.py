from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import sip
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton, QGroupBox, QSlider
from PyQt5.QtCore import Qt
from UI.viewer.viewerImage import ImageViewer
from UI.viewer.viewerImages import ImagesViewer
from UI.tools.utils import *
import os
import cv2
import numpy as np


class SettingsDialog(QtWidgets.QDialog):
    theme_changed = QtCore.pyqtSignal(str)
    language_changed = QtCore.pyqtSignal(str)
    left_camera_changed = QtCore.pyqtSignal(int)     # Left camera index signal
    right_camera_changed = QtCore.pyqtSignal(int)    # Right camera index signal
    mask_opacity_changed = QtCore.pyqtSignal(float)  # mask opacity change signal

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowIcon(QtGui.QIcon("../icons/Settings.SVG"))
        self._last_values = {
            'theme': 'Light',
            'language': 'Chinese',
            'left_camera': 0,
            'right_camera': 1,
            'mask_opacity': 0.5,
        }
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Theme Settings
        theme_group = QtWidgets.QGroupBox("Theme Settings")
        theme_layout = QtWidgets.QVBoxLayout()
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # Language Settings
        language_group = QtWidgets.QGroupBox("Language Settings")
        language_layout = QtWidgets.QVBoxLayout()
        self.language_combo = QtWidgets.QComboBox()
        self.language_combo.addItems(["Chinese", "English"])
        language_layout.addWidget(self.language_combo)
        language_group.setLayout(language_layout)
        layout.addWidget(language_group)

        # Camera Settings
        camera_group = QtWidgets.QGroupBox("Camera Settings")
        camera_layout = QtWidgets.QGridLayout()

        # Left Camera
        self.left_camera_combo = QtWidgets.QComboBox()
        self.left_camera_combo.currentIndexChanged.connect(self.update_right_camera_combo)
        camera_layout.addWidget(QtWidgets.QLabel("Left Camera:"), 0, 0)
        camera_layout.addWidget(self.left_camera_combo, 0, 1)

        # Right Camera
        self.right_camera_combo = QtWidgets.QComboBox()
        camera_layout.addWidget(QtWidgets.QLabel("Right Camera:"), 1, 0)
        camera_layout.addWidget(self.right_camera_combo, 1, 1)

        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)

        # Mask Opacity Settings (New)
        mask_group = QtWidgets.QGroupBox("Mask Settings")
        mask_layout = QtWidgets.QVBoxLayout()

        self.mask_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.mask_slider.setMinimum(0)
        self.mask_slider.setMaximum(100)
        self.mask_slider.setValue(50)  # Default 0.5 opacity
        self.mask_label = QtWidgets.QLabel(f"Opacity: {self.mask_slider.value()}%")

        self.mask_slider.valueChanged.connect(lambda v: self.mask_label.setText(f"Opacity: {v}%"))

        mask_layout.addWidget(self.mask_label)
        mask_layout.addWidget(self.mask_slider)
        mask_group.setLayout(mask_layout)
        layout.addWidget(mask_group)

        # Apply Button
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(self.apply_settings)
        layout.addWidget(apply_button)

    def set_available_cameras(self, available_indices):
        """ Set available camera list """
        self.left_camera_combo.clear()
        self.right_camera_combo.clear()
        if available_indices is None:
            return
        for idx in available_indices:
            self.left_camera_combo.addItem(f"Camera {idx}", userData=idx)
            self.right_camera_combo.addItem(f"Camera {idx}", userData=idx)

        # Select first by default
        if len(available_indices) > 0:
            self.left_camera_combo.setCurrentIndex(0)
        if len(available_indices) > 1:
            self.right_camera_combo.setCurrentIndex(1)

    def update_right_camera_combo(self):
        """ Update right camera options, excluding current left camera """
        current_left_idx = self.left_camera_combo.currentData()
        count = self.right_camera_combo.count()
        for i in range(count):
            item_data = self.right_camera_combo.itemData(i)
            self.right_camera_combo.setItemData(i, item_data != current_left_idx)

    def apply_settings(self):
        selected_theme = self.theme_combo.currentText()
        selected_language = self.language_combo.currentText()
        selected_left_camera = self.left_camera_combo.currentData()
        selected_right_camera = self.right_camera_combo.currentData()
        mask_opacity = self.mask_slider.value() / 100.0  # Convert to float [0.0 - 1.0]

        QtWidgets.QMessageBox.information(
            self,
            "Settings Applied",
            f"Theme: {selected_theme}\nLanguage: {selected_language}\nLeft Camera: {selected_left_camera}\nRight Camera: {selected_right_camera}\nMask Opacity: {mask_opacity:.2f}"
        )

        # Only emit signals when values change
        if selected_theme != self._last_values['theme']:
            self.theme_changed.emit(selected_theme)
            self._last_values['theme'] = selected_theme

        if selected_language != self._last_values['language']:
            self.language_changed.emit(selected_language)
            self._last_values['language'] = selected_language

        if selected_left_camera != self._last_values['left_camera']:
            self.left_camera_changed.emit(selected_left_camera)
            self._last_values['left_camera'] = selected_left_camera

        if selected_right_camera != self._last_values['right_camera']:
            self.right_camera_changed.emit(selected_right_camera)
            self._last_values['right_camera'] = selected_right_camera

        if mask_opacity != self._last_values['mask_opacity']:
            self.mask_opacity_changed.emit(mask_opacity)
            self._last_values['mask_opacity'] = mask_opacity

class MaskControlDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Mask Control Settings")
        self.resize(500, 400)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # 掩码反转选项
        self.invert_checkbox = QCheckBox("Invert Mask")
        self.invert_checkbox.setChecked(False)
        layout.addWidget(self.invert_checkbox)

        # 掩码透明度控制
        opacity_group = QGroupBox("Mask Opacity")
        opacity_layout = QVBoxLayout()

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(50)  # 默认50%

        self.opacity_label = QLabel(f"Opacity: {self.opacity_slider.value()}%")
        self.opacity_slider.valueChanged.connect(self.update_opacity_label)

        opacity_layout.addWidget(self.opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_group.setLayout(opacity_layout)
        layout.addWidget(opacity_group)

        # 掩码类型选项
        type_group = QGroupBox("Mask Type")
        type_layout = QVBoxLayout()

        self.binary_checkbox = QCheckBox("Binary Mask (0 or 255 only)")
        self.binary_checkbox.setChecked(True)
        type_layout.addWidget(self.binary_checkbox)

        self.smooth_checkbox = QCheckBox("Smooth Edges")
        self.smooth_checkbox.setChecked(False)
        type_layout.addWidget(self.smooth_checkbox)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # 掩码加载方式选择
        load_group = QGroupBox("Load Mask From")
        load_layout = QVBoxLayout()

        self.load_methods = ["Load Single Mask File", "Load from Directory"]
        self.load_combo = QtWidgets.QComboBox()
        self.load_combo.addItems(self.load_methods)
        load_layout.addWidget(self.load_combo)

        load_group.setLayout(load_layout)
        layout.addWidget(load_group)

        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Load Mask")
        self.unload_button = QPushButton("Unload Mask")  # 新增卸载按钮
        self.cancel_button = QPushButton("Cancel")

        self.ok_button.clicked.connect(self.load_mask)
        self.unload_button.clicked.connect(self.unload_mask)  # 新增卸载功能
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.unload_button)  # 添加卸载按钮
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def update_opacity_label(self, value):
        self.opacity_label.setText(f"Opacity: {value}%")

    def get_settings(self):
        return {
            'invert_mask': self.invert_checkbox.isChecked(),
            'opacity': self.opacity_slider.value() / 100.0,
            'binary_mask': self.binary_checkbox.isChecked(),
            'smooth_edges': self.smooth_checkbox.isChecked(),
            'load_method': self.load_combo.currentText()
        }

    def load_mask(self):
        """加载掩码的主函数"""
        settings = self.get_settings()
        invert_mask = settings['invert_mask']
        load_method = settings['load_method']
        opacity = settings['opacity']

        current_widget = self.parent.tab_widget.currentWidget()

        # 检查当前 widget 是否支持 mask 计算
        if not isinstance(current_widget, (ImageViewer, ImagesViewer)):
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "Mask is only available in image viewing modes."
            )
            return

        # 根据选择执行相应的加载逻辑
        if load_method == "Load Single Mask File":
            self._load_single_mask_file(current_widget, invert_mask, opacity)
        elif load_method == "Load from Directory":
            self._load_mask_from_directory(current_widget, invert_mask, opacity)

    def unload_mask(self):
        """卸载掩码的主函数"""
        current_widget = self.parent.tab_widget.currentWidget()

        # 检查当前 widget 是否支持 mask 计算
        if not isinstance(current_widget, (ImageViewer, ImagesViewer)):
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "Mask is only available in image viewing modes."
            )
            return

        # 检查当前是否已有掩码
        if hasattr(current_widget, 'mask_calcu') and current_widget.mask_calcu is not None:
            # 如果已有掩码，取消掩码
            current_widget.mask_calcu = None
            self.parent.statusbar.showMessage("❌ Mask unloaded", 3000)

            # 更新显示
            if hasattr(current_widget, 'img'):
                current_widget.load_file(current_widget.img[0])
        else:
            # 如果没有掩码，显示提示信息
            self.parent.statusbar.showMessage("No mask to unload", 3000)

        self.accept()  # 关闭对话框

    def _load_single_mask_file(self, current_widget, invert_mask=False, opacity=0.5):
        """加载单个掩码文件"""
        mask_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Mask File",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.tif);;All Files (*)"
        )

        if mask_file:
            try:
                mask = cv2.imread(mask_file, cv2.IMREAD_GRAYSCALE)
                if mask is not None:

                    # 将掩码赋值给当前widget
                    current_widget.mask_calcu = mask, invert_mask, opacity

                    # 更新显示
                    if hasattr(current_widget, 'img'):
                        current_widget.load_image()

                    status_msg = f"✅ Mask loaded: {os.path.basename(mask_file)}"
                    if invert_mask:
                        status_msg += " (inverted)"
                    self.parent.statusbar.showMessage(status_msg, 3000)

                    self.accept()  # 关闭对话框
                else:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Warning",
                        "Failed to load mask file. Please check the file format."
                    )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error",
                    f"Error loading mask file:\n{str(e)}"
                )

    def _load_mask_from_directory(self, current_widget, invert_mask=False, opacity=0.5):
        """从目录加载掩码文件"""
        # 选择目录
        mask_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Mask Directory"
        )

        if not mask_dir:
            return  # 用户取消

        # 获取目录中的所有掩码文件
        mask_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']
        mask_files = [
            os.path.join(mask_dir, f) for f in os.listdir(mask_dir)
            if any(f.lower().endswith(ext) for ext in mask_extensions)
        ]

        if not mask_files:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "No mask files found in the selected directory."
            )
            return

        # 将掩码文件路径列表存储到 mask_calcu
        current_widget.mask_calcu = mask_files, invert_mask, opacity
        status_msg = f"✅ Loaded {len(mask_files)} mask files from directory"
        if invert_mask:
            status_msg += " (inverted)"
        self.parent.statusbar.showMessage(status_msg, 3000)

        self.accept()  # 关闭对话框
