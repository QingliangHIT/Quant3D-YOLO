"""文件面板：图像列表、浏览进度、跳转与列表右键批量操作。"""

import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt


class FilesDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Files", parent)
        self.show_icon_in_list = None
        self.num_icon_size = None
        self.parent = parent
        self.file_paths = []
        self.label_paths = []
        self.init_ui()

    def init_ui(self):
        self.setMinimumSize(QtCore.QSize(185, 43))
        self.setFeatures(QtWidgets.QDockWidget.AllDockWidgetFeatures)
        self.setContentsMargins(6, 6, 6, 6)

        # Content widget
        self.file_dock_content = QtWidgets.QWidget()
        self.file_dock_layout = QtWidgets.QVBoxLayout(self.file_dock_content)
        self.file_dock_layout.setContentsMargins(0, 0, 0, 0)
        self.file_dock_layout.setSpacing(0)

        # List widget
        self.list_widget = QtWidgets.QListWidget()
        self.file_dock_layout.addWidget(self.list_widget)

        # Status indicator
        self.widget_state = QtWidgets.QWidget()
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.widget_state)
        self.horizontalLayout_2.setContentsMargins(0, 6, 0, 6)

        self.label_prev_state = QtWidgets.QLabel()
        self.label_prev_state.setMaximumSize(QtCore.QSize(50, 8))
        self.label_prev_state.setStyleSheet("background-color: rgb(199, 0, 0);\nborder-radius: 3px;")
        self.label_prev_state.setText("")
        self.horizontalLayout_2.addWidget(self.label_prev_state, 1)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)  # Hide percentage text
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #e0e0e0;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #00c700;
                border-radius: 3px;
            }
        """)
        self.horizontalLayout_2.addWidget(self.progress_bar, 1)

        self.label_next_state = QtWidgets.QLabel()
        self.label_next_state.setMinimumSize(QtCore.QSize(0, 0))
        self.label_next_state.setMaximumSize(QtCore.QSize(50, 8))
        self.label_next_state.setStyleSheet("background-color: rgb(0, 0, 100);\nborder-radius: 3px;")
        self.horizontalLayout_2.addWidget(self.label_next_state, 1)

        self.file_dock_layout.addWidget(self.widget_state)

        # Number widget
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
        self.list_widget.itemClicked.connect(self.on_files_selected)
        self.lineEdit_jump.returnPressed.connect(self.jump_to_file)
        self.label_prev_state.mousePressEvent = self.prev_image
        # self.label_current_state.mousePressEvent = self.reload_current_image
        self.label_next_state.mousePressEvent = self.next_image
        self.list_widget.itemDoubleClicked.connect(self.open_file_from_list)
        self.setup_file_context_menu()

    def setup_file_context_menu(self):
        self.num_icon_size = 64
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_widget.customContextMenuRequested.connect(self.show_file_context_menu)
        self.list_widget.setViewMode(QtWidgets.QListView.ListMode)
        self.list_widget.setGridSize(QtCore.QSize(160, self.num_icon_size//2))
        self.list_widget.setSpacing(0)
        self.list_widget.setWordWrap(False)

    def show_file_context_menu(self, pos):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return

        menu = QtWidgets.QMenu(self)

        # Delete & related ops
        action_delete_selected = menu.addAction("🗑 Delete selected")
        action_delete_file_selected = menu.addAction("❌ Delete file")
        action_copy_paths = menu.addAction("📋 Copy path")
        action_open_folders = menu.addAction("📂 Open containing folder")
        action_clear_all = menu.addAction("🧹 Clear list")
        action_show_icon = menu.addAction("🖼 Show icon")

        # View mode submenu
        view_mode_menu = menu.addMenu("🧭 View mode")
        action_icon_view = view_mode_menu.addAction("🖼 Thumbnail view")
        action_list_view = view_mode_menu.addAction("📄 List view")

        action = menu.exec_(self.list_widget.mapToGlobal(pos))

        if action == action_delete_selected:
            for item in selected_items:
                self.list_widget.takeItem(self.list_widget.row(item))
                file_path = item.data(Qt.UserRole)
                if file_path in self.file_paths:
                    self.file_paths.remove(file_path)
        elif action == action_delete_file_selected:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Confirm delete",
                f"Delete {len(selected_items)} files? This cannot be undone.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                for item in selected_items:
                    file_path = item.data(Qt.UserRole)
                    try:
                        os.remove(file_path)
                        self.list_widget.takeItem(self.list_widget.row(item))
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(
                            self,
                            "Delete failed",
                            f"Failed to delete: {file_path}\nError: {str(e)}"
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
            self.file_paths.clear()

        # Switch view mode
        elif action == action_icon_view:
            show = self.show_icon_in_list
            self.show_icon_in_list = True
            self.list_widget.setViewMode(QtWidgets.QListView.IconMode)
            self.list_widget.setIconSize(QtCore.QSize(64, 64))
            self.list_widget.setGridSize(QtCore.QSize(80, 80))
            # self.list_widget.setWordWrap(True)
            self.update_file_list(self.file_paths)
            self.show_icon_in_list = show

        elif action == action_list_view:
            self.list_widget.setViewMode(QtWidgets.QListView.ListMode)
            if self.show_icon_in_list:
                self.list_widget.setIconSize(QtCore.QSize(self.num_icon_size, self.num_icon_size))
                self.list_widget.setGridSize(QtCore.QSize(160, self.num_icon_size))
            else:
                self.list_widget.setIconSize(QtCore.QSize(0, 0))
                self.list_widget.setGridSize(QtCore.QSize(160, self.num_icon_size // 2))
            self.update_file_list(self.file_paths)
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
        self.update_file_list(self.file_paths)

    def update_file_list(self, file_paths, show=True, add=False):
        if add and len(self.file_paths) > 0:
            self.file_paths.extend([path for path in file_paths if path not in self.file_paths])
        else:
            self.file_paths = file_paths
        self.list_widget.clear()
        total_files = len(self.file_paths)
        digits = len(str(total_files)) if total_files > 0 else 1

        for i, path in enumerate(self.file_paths):
            filename = os.path.basename(path)
            item_text = f"{i + 1:{digits}d} - {filename}"

            # Create QListWidgetItem
            item = QtWidgets.QListWidgetItem()

            # Set text
            item.setText(item_text)

            # If image file, load thumbnail
            if getattr(self, 'show_icon_in_list', False):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                    pixmap = QtGui.QPixmap(path)
                    if not pixmap.isNull():
                        icon_size = QtCore.QSize(self.num_icon_size, self.num_icon_size)
                        scaled_pixmap = pixmap.scaled(icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        icon = QtGui.QIcon(scaled_pixmap)
                        item.setIcon(icon)
                else:
                    # Optional: set default icon for non-images
                    default_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)
                    item.setIcon(default_icon)

            item.setData(QtCore.Qt.UserRole, path)
            self.list_widget.addItem(item)

        if file_paths and show:
            self.list_widget.setCurrentItem(self.list_widget.item(0))
            self.on_files_selected([self.list_widget.currentItem()])

    def load_all_labels(self):
        """
        Load labels for all images in dock_file
        """
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select image folder")
        if not folder_path:
            return
        image_files = []
        label_extensions = ('.txt', '.json', '.xml', '.png', '.jpg', '.jpeg', '.bmp', '.gif')

        for file in os.listdir(folder_path):
            full_path = os.path.join(folder_path, file)
            if os.path.isfile(full_path):
                filename, ext = os.path.splitext(file)
                if ext.lower() in label_extensions:
                    image_files.append(full_path)

        if not image_files:
            self.parent.statusbar.showMessage("❌ No label files found in folder", 3000)
            return
        self.label_paths = image_files
        current_widget = self.parent.tab_widget.currentWidget()
        current_widget.show_label = True
        self.parent.show_label()
        self.parent.statusbar.showMessage(f"✅ Loaded {len(image_files)} label files", 3000)

    def cleanup(self):
        # Clear list widget
        self.list_widget.clear()

        # Clear file paths
        self.file_paths.clear()

        # Clear input
        self.lineEdit_jump.clear()

        # Set to empty list and update UI
        self.update_file_list([])

    def open_file_from_list(self, item):
        file_path = item.data(Qt.UserRole)
        if os.path.exists(file_path):
            import webbrowser
            webbrowser.open(file_path)  # Windows: opens with default program
        else:
            QtWidgets.QMessageBox.warning(self, "File not found", "File was moved or deleted")

    def on_files_selected(self, item):
        if not isinstance(item, QtWidgets.QListWidgetItem):
            item = item[0]
        if item:
            file_path = item.data(QtCore.Qt.UserRole)
            if file_path and self.parent:
                self.parent.load_file(file_path)

            current_index = self.list_widget.row(item) + 1
            total_files = self.list_widget.count()
            self.label_current.setText(f"{current_index}/{total_files}")

            # Update progress bar
            progress = int((current_index / total_files) * 100)
            self.progress_bar.setValue(progress)

            # Highlight logic unchanged
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
                self.on_files_selected([item])
            else:
                found = False
                for i in range(self.list_widget.count()):
                    item = self.list_widget.item(i)
                    clean_name = " - ".join(item.text().split(" - ")[1:])
                    if clean_name == input_text or clean_name.startswith(input_text):
                        self.list_widget.setCurrentItem(item)
                        self.on_files_selected([item])
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
                    self.on_files_selected([item])
                    found = True
                    break
            if not found:
                QtWidgets.QMessageBox.warning(self, "Jump to File", "File not found.")

    def prev_image(self, event, group_size=1):
        if self.list_widget.count() > 0:
            row = (self.list_widget.currentRow() - 1) % self.list_widget.count()
            items = [self.list_widget.item(i) for i in range(row, row + group_size)]
            self.list_widget.setCurrentItem(items[0])
            self.on_files_selected(items)

    def next_image(self, event, group_size=1):
        if self.list_widget.count() > 0:
            row = (self.list_widget.currentRow() + 1) % self.list_widget.count()
            items = [self.list_widget.item(i) for i in range(row, row+group_size)]
            self.list_widget.setCurrentItem(items[-1])
            self.on_files_selected(items)

    def to_first_image(self, event):
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            self.on_files_selected(self.list_widget.item(0))

    def to_last_image(self, event):
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)
            self.on_files_selected(self.list_widget.item(self.list_widget.count() - 1))

    def reload_current_image(self):
        if self.list_widget.count() > 0:
            item = self.list_widget.currentItem()
            if item is None:
                item = self.list_widget.item(0)
            self.on_files_selected([item])

    def wheelEvent(self, event: QtGui.QWheelEvent):
        if event.modifiers() & Qt.ShiftModifier:
            delta = event.angleDelta().y()
            current_icon_size = self.list_widget.iconSize()
            new_size = current_icon_size.width() + (delta // 120) * 4

            # Set min/max size limits
            min_size = 32
            max_size = 256
            new_size = max(min(new_size, max_size), min_size)

            # Only change icon size
            self.list_widget.setIconSize(QtCore.QSize(new_size, new_size))

            # Force refresh all icons
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                file_path = item.data(Qt.UserRole)
                filename = os.path.basename(file_path)

                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                    pixmap = QtGui.QPixmap(file_path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(
                            new_size, new_size,
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                        icon = QtGui.QIcon(scaled_pixmap)
                        item.setIcon(icon)

            event.accept()
        else:
            super().wheelEvent(event)
