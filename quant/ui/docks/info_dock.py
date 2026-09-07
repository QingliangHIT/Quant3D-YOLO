"""图像/检测信息面板：显示当前图像与目标的统计信息。"""

import os
import cv2
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from quant.core.qt_image import get_image_format_name

from quant.ui.widgets.image_preview_window import ImageViewerWindow


class InfoDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Info", parent)
        self.parent = parent
        self.init_ui()

    def cleanup(self):
        self.clear_info()

    def init_ui(self):
        self.setMinimumSize(QtCore.QSize(185, 43))
        self.setFeatures(QtWidgets.QDockWidget.AllDockWidgetFeatures)

        # Create content widget
        self.content_widget = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Image preview area
        self.preview_label = QtWidgets.QLabel("Preview")
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        self.preview_label.setMinimumHeight(100)
        self.preview_label.setMaximumHeight(200)
        self.preview_label.setCursor(QtCore.Qt.PointingHandCursor)
        self.preview_label.mousePressEvent = self.show_full_preview

        # Use QListWidget for key-value pairs
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.list_widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
            }
            QListWidgetItem {
                height: 24px;
            }
        """)

        # Add to layout
        self.content_layout.addWidget(self.preview_label)
        self.content_layout.addWidget(self.list_widget)
        self.setWidget(self.content_widget)
        self.preview_label.hide()

    def set_info(self, data: dict):
        """
        Set info dict to display
        """
        if data:
            self.list_widget.clear()
            self.preview_label.hide()
            for key, value in data.items():
                if key == "file_path":
                    self.preview_label.show()
                    image_info = self.show_preview_info(value)
                    if image_info is not None:
                        for key1, value1 in image_info.items():
                            item = QtWidgets.QListWidgetItem(f"{key1}: {value1}")
                            item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                            self.list_widget.addItem(item)
                else:
                    item = QtWidgets.QListWidgetItem(f"{key}: {value}")
                    item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                    self.list_widget.addItem(item)

    def clear_info(self):
        self.list_widget.clear()

    def show_preview_info(self, file_path):
        image_info = {}
        if os.path.exists(file_path):
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                pixmap = QPixmap(file_path)
                image_info = {
                    "File": os.path.basename(file_path),
                    "Width": pixmap.width(),
                    "Height": pixmap.height(),
                    "Format": get_image_format_name(pixmap.toImage().format())}
                pixmap = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(pixmap)
            elif file_path.lower().endswith(('.avi', '.mp4', '.mkv', '.mov')):
                image_info = self.show_video_thumbnail(file_path)
            else:
                self.preview_label.setText("📁 File")
        else:
            self.preview_label.setText("❌ File not found")
        return image_info

    def show_full_preview(self, event):
        if hasattr(self, 'full_preview_window') and self.full_preview_window:
            self.full_preview_window.close()

        if hasattr(self.preview_label, 'pixmap') and self.preview_label.pixmap():
            self.full_preview_window = ImageViewerWindow(self.preview_label.pixmap())
            self.full_preview_window.show()

    def show_video_thumbnail(self, video_path):
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        image_info = {}
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QtGui.QImage(frame.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
            pixmap = QtGui.QPixmap.fromImage(qt_image)
            image_info = {
                "File": os.path.basename(video_path),
                "Width": pixmap.width(),
                "Height": pixmap.height(),
                "Format": get_image_format_name(pixmap.toImage().format())}
            pixmap = pixmap.scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(pixmap)
        else:
            self.preview_label.setText("🎞 Cannot read video")
        cap.release()
        return image_info
