"""相机页文件面板：图像目录浏览、连拍序列管理。"""

import glob
import cv2
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
