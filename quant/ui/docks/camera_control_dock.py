"""相机控制面板：设备选择、参数调节与采集触发。"""

import cv2
from PyQt5.QtGui import QPixmap
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt

from quant.ui.dialogs.burst_settings_dialog import BurstSettingsDialog


class ControlDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.interval = 1
        self.count = 1
        self.parent = parent
        self.setObjectName("control_dock")
        self.setWindowTitle("Control")
        self.files_list = []

        self.init_ui()
        # Bind events
        self.bind_events()
        self.bind_key()

    def init_ui(self):
        self.main_widget = QtWidgets.QWidget(self)
        self.setWidget(self.main_widget)
        self.layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.layout.setSpacing(0)  # Uniform spacing

        # Photo & Video buttons
        self.camera_control_layout = QtWidgets.QHBoxLayout()
        self.btn_snapshot = QtWidgets.QPushButton("📸")
        self.btn_record = QtWidgets.QPushButton("🎥")
        self.btn_snapshot.setToolTip("Take Photo (F1)")
        self.btn_record.setToolTip("Start Recording (F2)")
        self.camera_control_layout.addWidget(self.btn_snapshot, 1)
        self.camera_control_layout.addWidget(self.btn_record, 1)
        self.layout.addLayout(self.camera_control_layout)

        # Burst buttons
        self.camera_burst_layout = QtWidgets.QHBoxLayout()
        self.btn_start_burst = QtWidgets.QPushButton("🔁")
        self.btn_start_burst.setToolTip("Start Burst Mode")
        self.camera_burst_layout.addWidget(self.btn_start_burst)
        self.btn_setting_burst = QtWidgets.QPushButton("⚙️")
        self.btn_setting_burst.setToolTip("Open Burst Settings")
        self.camera_burst_layout.addWidget(self.btn_setting_burst)
        self.layout.addLayout(self.camera_burst_layout)

        # Zoom control
        self.zoom_layout = QtWidgets.QHBoxLayout()
        self.btn_zoom_in = QtWidgets.QPushButton("🔍+")
        self.btn_zoom_out = QtWidgets.QPushButton("🔎-")
        self.btn_zoom_in.setToolTip("Zoom In View")
        self.btn_zoom_out.setToolTip("Zoom Out View")
        self.zoom_layout.addWidget(self.btn_zoom_in)
        self.zoom_layout.addWidget(self.btn_zoom_out)
        self.layout.addLayout(self.zoom_layout)

        # Focus control row (Auto Focus + Focus Adjustment)
        self.spin_focus = QtWidgets.QSpinBox()
        self.spin_focus.setRange(0, 255)
        self.spin_focus.setValue(80)
        self.spin_focus.setEnabled(False)
        # self.spin_focus.setFixedWidth(50)
        self.select_row = QtWidgets.QHBoxLayout()
        self.checkbox_auto_focus = QtWidgets.QCheckBox("AF")
        self.checkbox_auto_focus.setChecked(True)
        # Show FPS option
        self.checkbox_show_fps = QtWidgets.QCheckBox("FPS")
        self.checkbox_show_fps.setChecked(False)
        self.select_row.addWidget(self.spin_focus, 1)
        self.select_row.addWidget(self.checkbox_auto_focus, 1)
        self.select_row.addStretch()
        self.select_row.addWidget(self.checkbox_show_fps, 1)
        self.layout.addLayout(self.select_row)

        self.btn_focus_minus = QtWidgets.QPushButton("➖")
        self.btn_focus_minus.setToolTip("Decrease Focus")
        self.btn_focus_plus = QtWidgets.QPushButton("➕")
        self.btn_focus_plus.setToolTip("Increase Focus")
        self.focus_row = QtWidgets.QHBoxLayout()
        self.focus_row.addWidget(self.btn_focus_minus)
        self.focus_row.addWidget(self.btn_focus_plus)
        # self.focus_row.addStretch()

        self.layout.addLayout(self.focus_row)

        # Resolution selection
        self.resolution_layout = QtWidgets.QHBoxLayout()
        self.btn_set_resolution = QtWidgets.QPushButton("🔄")
        self.btn_set_resolution.setToolTip("Switch Resolution")
        self.resolution_combo = QtWidgets.QComboBox()
        self.resolution_combo.addItems([
            "1920x1080", "3840x2160", "1280x720", "640x480", "800x600",
            "2048x1536", "2592x1944", "4000x3000", "4608x3456", "8000x6000"
        ])
        self.resolution_combo.setEditable(True)  # Allow custom input
        self.resolution_combo.lineEdit().setAlignment(Qt.AlignCenter)
        # self.resolution_combo.setMaximumWidth(100)
        self.resolution_layout.addWidget(self.resolution_combo)
        self.resolution_layout.addWidget(self.btn_set_resolution)
        self.layout.addLayout(self.resolution_layout)

        # Hide unused old controls
        self.burst_timer = None
        self.is_recording = False
        self.video_writer = None

    def toggle_burst_settings(self, checked):
        if checked:
            self.btn_start_burst.setText("🛑")
        else:
            self.btn_start_burst.setText("🔁")

    def bind_events(self):
        self.btn_snapshot.clicked.connect(self.on_snapshot)
        self.btn_record.clicked.connect(self.on_record)
        self.btn_start_burst.clicked.connect(self.start_burst_mode)
        self.btn_setting_burst.clicked.connect(self.on_start_burst)
        self.btn_zoom_in.clicked.connect(self.on_zoom_in)
        self.btn_zoom_out.clicked.connect(self.on_zoom_out)
        # self.zoom_slider.valueChanged.connect(self.on_zoom_change)
        self.checkbox_auto_focus.toggled.connect(self.toggle_auto_focus)
        self.spin_focus.valueChanged.connect(self.set_focus_value)
        self.btn_focus_minus.clicked.connect(lambda: self.adjust_focus(-5))
        self.btn_focus_plus.clicked.connect(lambda: self.adjust_focus(+5))
        self.btn_set_resolution.clicked.connect(self.change_resolution)
        self.checkbox_show_fps.toggled.connect(self.toggle_show_fps)

    def toggle_show_fps(self, state):
        # print(state)
        # print(self.parent.current_state)
        if self.parent.camera_page.pixmap_item is not None:
            camera_window = self.parent.camera_page
            camera_window.set_fps(state)
        else:
            self.checkbox_show_fps.setChecked(False)

    def toggle_auto_focus(self, state):
        if self.parent.camera_page.pixmap_item is not None:
            auto_focus = -1 if state else 0
            self.spin_focus.setEnabled(auto_focus == 0)  # Can only modify focus when auto focus is off
            self.parent.camera_page.parent_conn.send({"cmd": "focus", "val": auto_focus})
        else:
            self.checkbox_auto_focus.setChecked(True)

    def set_focus_value(self, value):
        if self.parent.camera_page.pixmap_item is not None:
            self.checkbox_auto_focus.setChecked(False)
            self.parent.camera_page.parent_conn.send({"cmd": "focus", "val": value})
            self.checkbox_auto_focus.setChecked(False)

        else:
            self.checkbox_auto_focus.setChecked(True)

    def adjust_focus(self, delta):
        new_value = max(0, min(255, self.spin_focus.value() + delta))
        self.spin_focus.setValue(new_value)

    def show_preview(self, item, pixmap=None):
        file_path = item.data(Qt.UserRole)
        image_info = {
            "file_path": os.path.abspath(file_path),
            }
        self.parent.info_dock.set_info(image_info)

        if os.path.exists(file_path):
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                pixmap = QPixmap(file_path).scaled(
                    self.preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(pixmap)
            elif file_path.lower().endswith(('.avi', '.mp4', '.mkv', '.mov')):
                self.show_video_thumbnail(file_path)
            else:
                self.preview_label.setText("📁 File")
        else:
            self.preview_label.setText("❌ File Not Found")

    def show_video_thumbnail(self, video_path):
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QtGui.QImage(frame.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
            pixmap = QtGui.QPixmap.fromImage(qt_image).scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(pixmap)
        else:
            self.preview_label.setText("🎞 Unable to Read Video")
        cap.release()

    def bind_key(self):
        self.shortcut_snapshot = QtWidgets.QShortcut(QtGui.QKeySequence("F1"), self)
        self.shortcut_snapshot.activated.connect(self.on_snapshot)

        self.shortcut_record = QtWidgets.QShortcut(QtGui.QKeySequence("F2"), self)
        self.shortcut_record.activated.connect(self.on_record)

    def change_resolution(self):
        resolution = self.resolution_combo.currentText()
        width, height = map(int, resolution.split('x'))
        if hasattr(self.parent, 'camera_page'):
            self.parent.camera_page.change_resolution(width, height)

    def on_snapshot(self):
        """Take photo: save current frame"""
        if hasattr(self.parent, 'camera_page') and self.parent.camera_page.capture:
            pass
        else:
            return
        self.parent.camera_page.start_snapshot()
        self.parent.is_modified = True

    def on_record(self):
        """Start or stop recording"""
        if hasattr(self.parent, 'camera_page') and self.parent.camera_page.capture:
            pass
        else:
            return

        if not self.is_recording:
            self.parent.camera_page.start_recording()
            self.btn_record.setText("⏹️")
            # self.parent.statusbar.showMessage(f"✅ Recording...")
            self.is_recording = True
        else:
            self.parent.camera_page.stop_recording()
            self.btn_record.setText("🎥")
            self.is_recording = False
            self.parent.is_modified = True

    def on_start_burst(self):
        dialog = BurstSettingsDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.interval, self.count = dialog.get_settings()
            # self.start_burst_mode(interval, count)

    def start_burst_mode(self):
        """Start burst mode"""
        interval = self.interval
        count = self.count
        interval_ms = interval * 1000  # Seconds to milliseconds
        if hasattr(self.parent, 'camera_page') and self.parent.camera_page.capture:
            pass
        else:
            return

        if not hasattr(self, 'is_bursting') or not self.is_bursting:
            self.burst_timer = QtCore.QTimer()
            if count == 0:
                # Infinite burst
                self.burst_timer.timeout.connect(lambda: self.on_snapshot())
                self.burst_count = self.parent.project_manager.i_img

            else:
                # Burst with specified count
                self.remaining_burst_count = count

                def burst_action():
                    if self.remaining_burst_count > 0:
                        self.parent.camera_page.start_snapshot()
                        self.remaining_burst_count -= 1
                    else:
                        self.burst_timer.stop()
                        self.btn_start_burst.setText("🔁")
                        self.parent.statusbar.showMessage(f"✅ Completed {count} burst shots", 2000)

                self.burst_timer.timeout.connect(burst_action)

            self.burst_timer.start(interval_ms)
            self.btn_start_burst.setText("🛑")
            self.is_bursting = True
        else:
            self.is_bursting = False
            if self.burst_timer and self.burst_timer.isActive():
                self.burst_timer.stop()
                self.btn_start_burst.setText("🔁")
                self.parent.statusbar.showMessage(f"✅ Completed {self.parent.project_manager.i_img-self.burst_count} burst shots", 2000)

    def on_zoom_in(self):
        """Zoom in image"""
        if hasattr(self.parent, 'camera_page'):
            self.parent.camera_page.zoom_in()

    def on_zoom_out(self):
        """Zoom out image"""
        if hasattr(self.parent, 'camera_page'):
            self.parent.camera_page.zoom_out()
