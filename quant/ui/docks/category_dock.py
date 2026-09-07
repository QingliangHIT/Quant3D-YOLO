"""类别面板：展示当前图像命中的检测类别，并提供列表右键清理。"""

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt


class CategoriesDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("categories_dock")
        self.setWindowTitle("Categories")

        # Create main widget container
        self.main_widget = QtWidgets.QWidget(self)
        self.setWidget(self.main_widget)
        self.layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(2)

        self.categories_list = QtWidgets.QListWidget()
        self.categories_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)  # Disable default selection mode
        self.layout.addWidget(self.categories_list)

        self.setup_file_context_menu()

    def setup_file_context_menu(self):
        self.categories_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.categories_list.customContextMenuRequested.connect(self.show_file_context_menu)

    def show_file_context_menu(self, pos):
        """列表禁用了选中模式，因此以光标所在项作为删除目标。"""
        item = self.categories_list.itemAt(pos)
        menu = QtWidgets.QMenu(self)
        action_delete_selected = menu.addAction("🗑 Delete Selected") if item else None
        action_clear_all = menu.addAction("🧹 Clear List")

        action = menu.exec_(self.categories_list.mapToGlobal(pos))

        if action == action_clear_all:
            self.categories_list.clear()
        elif action_delete_selected is not None and action == action_delete_selected:
            self.categories_list.takeItem(self.categories_list.row(item))

    def update_content(self, context, selected=None):
        self.categories_list.clear()
        self.categories_list.setVisible(True)
        # If input is a dictionary, convert key-value pairs to string list
        if isinstance(context, dict):
            # Convert dictionary to formatted string list
            if isinstance(selected, (dict, list)):
                items = [f"{key}\t{value}" for key, value in context.items() if key in selected]
            else:
                items = [f"{key}\t{value}" for key, value in context.items()]

            for item_text in items:
                item = QtWidgets.QListWidgetItem(item_text)
                self.categories_list.addItem(item)
        # If input is a list or other iterable object
        elif hasattr(context, '__iter__') and not isinstance(context, str):
            for item_text in context:
                item = QtWidgets.QListWidgetItem(str(item_text))
                self.categories_list.addItem(item)
        # If input is a single string
        else:
            item = QtWidgets.QListWidgetItem(str(context))
            self.categories_list.addItem(item)

    def cleanup(self):
        self.categories_list.clear()
        self.categories_list.setVisible(True)
