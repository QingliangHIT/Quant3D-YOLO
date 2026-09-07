"""掩码控制对话框：加载 / 管理分割掩码文件。"""

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton, QGroupBox, QSlider
from quant.ui.views.image_view import ImageViewer
from quant.ui.views.batch_image_view import ImagesViewer
import os
import cv2


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
