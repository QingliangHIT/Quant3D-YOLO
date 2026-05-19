import glob
import cv2
from PyQt5.QtGui import QPixmap
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt


class CameraFilesDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Camera Files", parent)
        self.parent = parent
        self.file_paths = []
        self.init_ui()
        self.show_icon_in_list = None
        self.num_icon_size = 64

    def cleanup(self):
        self.list_widget.clear()
        self.file_paths.clear()
        self.lineEdit_jump.clear()
        self.update_file_list([], all=True)

    def init_ui(self):
        self.setMinimumSize(QtCore.QSize(185, 43))
        self.setFeatures(QtWidgets.QDockWidget.AllDockWidgetFeatures)
        self.setContentsMargins(6, 6, 6, 6)
        # self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # Content widget
        self.file_dock_content = QtWidgets.QWidget()
        self.file_dock_layout = QtWidgets.QVBoxLayout(self.file_dock_content)
        self.file_dock_layout.setContentsMargins(0, 0, 0, 0)
        self.file_dock_layout.setSpacing(0)

        # List widget
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setToolTip("Saved photo/video file list")
        self.file_dock_layout.addWidget(self.list_widget)

        # Status indicators
        self.widget_state = QtWidgets.QWidget()
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.widget_state)
        self.horizontalLayout_2.setContentsMargins(0, 6, 0, 6)

        self.label_prev_state = QtWidgets.QLabel()
        self.label_prev_state.setMaximumSize(QtCore.QSize(50, 8))
        self.label_prev_state.setStyleSheet("background-color: rgb(199, 0, 0);\nborder-radius: 3px;")
        self.label_prev_state.setText("")
        self.horizontalLayout_2.addWidget(self.label_prev_state)

        self.label_current_state = QtWidgets.QLabel()
        self.label_current_state.setMinimumSize(QtCore.QSize(80, 0))
        self.label_current_state.setMaximumSize(QtCore.QSize(16777215, 8))
        self.label_current_state.setStyleSheet("background-color: rgb(0, 199, 0);\nborder-radius: 3px;")
        self.label_current_state.setText("")
        self.horizontalLayout_2.addWidget(self.label_current_state)

        self.label_next_state = QtWidgets.QLabel()
        self.label_next_state.setMinimumSize(QtCore.QSize(0, 0))
        self.label_next_state.setMaximumSize(QtCore.QSize(50, 8))
        self.label_next_state.setStyleSheet("background-color: rgb(0, 0, 100);\nborder-radius: 3px;")
        self.horizontalLayout_2.addWidget(self.label_next_state)

        self.file_dock_layout.addWidget(self.widget_state)

        # Number controls
        self.widget_num = QtWidgets.QWidget()
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget_num)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)

        self.lineEdit_jump = QtWidgets.QLineEdit()
        self.lineEdit_jump.setPlaceholderText("Jump...")
        self.horizontalLayout.addWidget(self.lineEdit_jump)

        self.label_current = QtWidgets.QLabel()
        self.label_current.setFixedWidth(80)
        self.horizontalLayout.addStretch()
        self.horizontalLayout.addWidget(self.label_current)

        self.file_dock_layout.addWidget(self.widget_num)

        self.setWidget(self.file_dock_content)

        # Signal connections
        self.list_widget.itemClicked.connect(self.on_file_selected)
        self.lineEdit_jump.returnPressed.connect(self.jump_to_file)
        self.label_prev_state.mousePressEvent = self.prev_image
        self.label_current_state.mousePressEvent = self.reload_current_image
        self.label_next_state.mousePressEvent = self.next_image
        self.list_widget.itemDoubleClicked.connect(self.open_file_from_list)
        self.setup_file_context_menu()

    def setup_file_context_menu(self):
        self.num_icon_size = 64
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_widget.customContextMenuRequested.connect(self.show_file_context_menu)
        self.list_widget.setViewMode(QtWidgets.QListView.ListMode)
        self.list_widget.setGridSize(QtCore.QSize(160, self.num_icon_size // 2))
        self.list_widget.setSpacing(0)
        self.list_widget.setWordWrap(False)

    def show_file_context_menu(self, pos):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return

        menu = QtWidgets.QMenu(self)

        # Delete & operations related
        action_delete_file_selected = menu.addAction("❌ Delete Files")
        action_copy_paths = menu.addAction("📋 Copy Paths")
        action_open_folders = menu.addAction("📂 Open Containing Folder")
        action_delete_selected = menu.addAction("🗑 Delete Selected")
        action_clear_all = menu.addAction("🧹 Clear List")
        action_show_icon = menu.addAction("🖼 Show Icons")

        # View mode submenu
        view_mode_menu = menu.addMenu("🧭 View Mode")
        action_icon_view = view_mode_menu.addAction("🖼 Thumbnail View")
        action_list_view = view_mode_menu.addAction("📄 List View")

        action = menu.exec_(self.list_widget.mapToGlobal(pos))

        if action == action_delete_selected:
            for item in selected_items:
                self.list_widget.takeItem(self.list_widget.row(item))
                self.file_paths.remove(item.data(Qt.UserRole))
        elif action == action_delete_file_selected:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete {len(selected_items)} files? This operation cannot be undone.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                for item in selected_items:
                    file_path = item.data(Qt.UserRole)
                    self.file_paths.remove(file_path)
                    file_pair = glob.glob(file_path + "*")
                    if file_pair[0].endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                        self.parent.project_manager.i_img -= 1
                    elif file_pair[0].endswith(('.mp4', '.avi', '.mkv', '.mov')):
                        self.parent.project_manager.i_vid -= 1
                    for file in file_pair:
                        try:
                            os.remove(file)
                            # self.update_file_list(self.file_paths)
                            self.list_widget.takeItem(self.list_widget.row(item))
                        except Exception as e:
                            QtWidgets.QMessageBox.warning(
                                self,
                                "Deletion Failed",
                                f"Unable to delete file: {file_path}\nError: {str(e)}"
                            )
        elif action == action_copy_paths:
            paths = "\n".join([item.data(Qt.UserRole) for item in selected_items])
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(paths)
        elif action == action_open_folders:
            folders = set(os.path.dirname(item.data(Qt.UserRole)) for item in selected_items)
            for folder in folders:
                if os.path.exists(folder):
                    os.startfile(folder)
        elif action == action_clear_all:
            self.list_widget.clear()
            self.file_paths = []
        # Switch view mode
        elif action == action_icon_view:
            show = self.show_icon_in_list
            self.show_icon_in_list = True
            self.list_widget.setViewMode(QtWidgets.QListView.IconMode)
            self.list_widget.setIconSize(QtCore.QSize(64, 64))
            self.list_widget.setGridSize(QtCore.QSize(80, 80))
            self.list_widget.setSpacing(0)

            # self.list_widget.setWordWrap(True)
            self.update_file_list(self.file_paths, all=True)
            self.show_icon_in_list = show

        elif action == action_list_view:
            self.list_widget.setViewMode(QtWidgets.QListView.ListMode)
            self.list_widget.setSpacing(0)

            if self.show_icon_in_list:
                self.list_widget.setIconSize(QtCore.QSize(self.num_icon_size, self.num_icon_size))
                self.list_widget.setGridSize(QtCore.QSize(160, self.num_icon_size))
            else:
                self.list_widget.setIconSize(QtCore.QSize(0, 0))
                self.list_widget.setGridSize(QtCore.QSize(160, self.num_icon_size // 2))
            self.update_file_list(self.file_paths, all=True)
        elif action == action_show_icon:
            self.toggle_icon_display()

    def toggle_icon_display(self):
        self.show_icon_in_list = not self.show_icon_in_list
        if self.show_icon_in_list:
            self.list_widget.setIconSize(QtCore.QSize(self.num_icon_size, self.num_icon_size))
            self.list_widget.setGridSize(QtCore.QSize(160, self.num_icon_size))
        else:
            self.list_widget.setIconSize(QtCore.QSize(0, 0))
            self.list_widget.setGridSize(QtCore.QSize(160, self.num_icon_size//2))
        self.update_file_list(self.file_paths, all=True)

    def update_file_list(self, file_paths, current_index=None, all=False):
        """
        Update file list, support icon display and thumbnail loading
        :param all: Replace all updates
        :param file_paths: File path list
        :param current_index: Default selected index
        """
        if all:
            self.file_paths = file_paths
        else:
            self.file_paths += file_paths
        self.list_widget.clear()
        # self.list_widget.clearSelection()
        self.list_widget.setCurrentItem(None)
        total_files = len(file_paths)
        digits = len(str(total_files)) if total_files > 0 else 1

        for i, path in enumerate(self.file_paths):
            file_path = glob.glob(path+'*')[0]
            filename = os.path.basename(path)
            item = QtWidgets.QListWidgetItem()

            # Load icon (only when show_icon_in_list is enabled)
            if getattr(self, 'show_icon_in_list', False):
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                    if os.path.exists(file_path):  # Check if file exists
                        pixmap = QtGui.QPixmap(file_path)
                        if not pixmap.isNull():
                            icon_size = QtCore.QSize(self.num_icon_size, self.num_icon_size)
                            scaled_pixmap = pixmap.scaled(icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            icon = QtGui.QIcon(scaled_pixmap)
                            item.setIcon(icon)
                    else:
                        item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))
                elif file_path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                    # Load first frame as thumbnail for video files
                    cap = cv2.VideoCapture(file_path)
                    ret, frame = cap.read()
                    if ret:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = frame.shape
                        bytes_per_line = ch * w
                        qt_image = QtGui.QImage(frame.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
                        pixmap = QtGui.QPixmap.fromImage(qt_image).scaled(
                            self.num_icon_size, self.num_icon_size,
                            Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                        icon = QtGui.QIcon(pixmap)
                        item.setIcon(icon)
                    else:
                        default_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)
                        item.setIcon(default_icon)
                    cap.release()
                else:
                    default_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)
                    item.setIcon(default_icon)
                item.setText(f"[{i + 1:{digits}d}] {filename}")
                item.setData(QtCore.Qt.UserRole, path)
            else:
                # Determine file type and set icon prefix
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                    icon_emoji = "📸"
                elif file_path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                    icon_emoji = "🎥"
                elif file_path.lower().endswith(('.txt', '.csv', '.log', '.json', '.xml', '.ini')):
                    icon_emoji = "📄"
                elif file_path.lower().endswith(('.pdf', '.docx', '.xlsx')):
                    icon_emoji = "📑"
                else:
                    icon_emoji = ""

                item.setText(f"{icon_emoji}[{i + 1:{digits}d}] {filename}")
                item.setData(QtCore.Qt.UserRole, path)

            self.list_widget.addItem(item)

        # Set default selected item
        if current_index == -1:
            idx = self.list_widget.count() - 1
            self.list_widget.setCurrentItem(self.list_widget.item(idx))
            self.on_file_selected(self.list_widget.item(idx))
        else:
            self.list_widget.setCurrentItem(current_index)

    def open_file_from_list(self, item):
        file_path = item.data(Qt.UserRole)
        files = glob.glob(file_path+"*")
        for file in files:
            if os.path.exists(file):
                import webbrowser
                webbrowser.open(file)  # Will open with default program on Windows
            else:
                QtWidgets.QMessageBox.warning(self, "File Not Found", "The file has been moved or deleted.")

    def on_file_selected(self, item):
        if item:
            file_path = item.data(QtCore.Qt.UserRole)
            file_path = glob.glob(file_path+"*")[0]
            image_info = {
                "file_path": os.path.abspath(file_path)
            }
            self.parent.info_dock.set_info(image_info)

            current_index = self.list_widget.row(item)
            self.label_current.setText(f"{current_index + 1}/{self.list_widget.count()}")

            for i in range(self.list_widget.count()):
                list_item = self.list_widget.item(i)
                if list_item == item:
                    list_item.setBackground(QtGui.QColor(255, 255, 255))
                    list_item.setForeground(QtGui.QColor(0, 0, 0))
                else:
                    list_item.setBackground(QtGui.QColor(240, 240, 240))
                    list_item.setForeground(QtGui.QColor(0, 0, 0))

    def jump_to_file(self):
        input_text = self.lineEdit_jump.text()
        if not input_text:
            return
        try:
            index = int(input_text) - 1
            if 0 <= index < self.list_widget.count():
                item = self.list_widget.item(index)
                self.list_widget.setCurrentItem(item)
                self.on_file_selected(item)
            else:
                found = False
                for i in range(self.list_widget.count()):
                    item = self.list_widget.item(i)
                    clean_name = " - ".join(item.text().split(" - ")[1:])
                    if clean_name == input_text or clean_name.startswith(input_text):
                        self.list_widget.setCurrentItem(item)
                        self.on_file_selected(item)
                        found = True
                        break
                if not found:
                    QtWidgets.QMessageBox.warning(self, "Jump to File", "File not found.")
        except ValueError:
            found = False
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                clean_name = " - ".join(item.text().split(" - ")[1:])
                if clean_name == input_text or clean_name.startswith(input_text):
                    self.list_widget.setCurrentItem(item)
                    self.on_file_selected(item)
                    found = True
                    break
            if not found:
                QtWidgets.QMessageBox.warning(self, "Jump to File", "File not found.")

    def prev_image(self, event):
        if self.list_widget.count() > 0:
            row = (self.list_widget.currentRow() - 1) % self.list_widget.count()
            item = self.list_widget.item(row)
            self.list_widget.setCurrentItem(item)
            self.on_file_selected(item)

    def next_image(self, event):
        if self.list_widget.count() > 0:
            row = (self.list_widget.currentRow() + 1) % self.list_widget.count()
            item = self.list_widget.item(row)
            self.list_widget.setCurrentItem(item)
            self.on_file_selected(item)

    def reload_current_image(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.list_widget.count() > 0:
            item = self.list_widget.currentItem()
            self.on_file_selected(item)


class BurstSettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Burst Settings")
        self.layout = QtWidgets.QVBoxLayout(self)

        # Interval setting
        interval_layout = QtWidgets.QHBoxLayout()
        self.interval_label = QtWidgets.QLabel("⏱️ Interval(s):")
        self.spin_burst_interval = QtWidgets.QSpinBox()
        self.spin_burst_interval.setRange(1, 60)
        self.spin_burst_interval.setValue(1)
        interval_layout.addWidget(self.interval_label)
        interval_layout.addWidget(self.spin_burst_interval)

        # Count setting
        count_layout = QtWidgets.QHBoxLayout()
        self.count_label = QtWidgets.QLabel("📷 Count:")
        self.spin_burst_count = QtWidgets.QSpinBox()
        self.spin_burst_count.setRange(0, 1000)
        self.spin_burst_count.setValue(0)
        count_layout.addWidget(self.count_label)
        count_layout.addWidget(self.spin_burst_count)

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.layout.addLayout(interval_layout)
        self.layout.addLayout(count_layout)
        self.layout.addWidget(button_box)

    def get_settings(self):
        return self.spin_burst_interval.value(), self.spin_burst_count.value()


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
            if self.parent.mode == 'stereo':
                self.parent.camera_page.parent_conn2.send({"cmd": "focus", "val": auto_focus})
        else:
            self.checkbox_auto_focus.setChecked(True)

    def set_focus_value(self, value):
        if self.parent.camera_page.pixmap_item is not None:
            self.checkbox_auto_focus.setChecked(False)
            self.parent.camera_page.parent_conn.send({"cmd": "focus", "val": value})
            if self.parent.mode == 'stereo':
                self.parent.camera_page.parent_conn2.send({"cmd": "focus", "val": value})
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
