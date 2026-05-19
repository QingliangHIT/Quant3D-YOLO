from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt


class CategoriesDock(QtWidgets.QDockWidget):
    class_filter_changed = QtCore.pyqtSignal()  # Add category filter signal
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

        self.select_all_button = QtWidgets.QPushButton()
        self.select_all_button.setToolTip("Select All")
        self.select_all_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton))
        self.select_all_button.setFixedSize(20, 20)
        self.select_all_button.setIconSize(QtCore.QSize(12, 12))

        self.deselect_all_button = QtWidgets.QPushButton()
        self.deselect_all_button.setToolTip("Select None")
        self.deselect_all_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserStop))
        self.deselect_all_button.setFixedSize(20, 20)
        self.deselect_all_button.setIconSize(QtCore.QSize(12, 12))

        self.categories_list = QtWidgets.QListWidget()
        self.categories_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)  # Disable default selection mode
        self.layout.addWidget(self.categories_list)

        # Bind events
        # self.bind_events()
        # self.bind_key()
        self.setup_file_context_menu()

    def setup_file_context_menu(self):
        self.categories_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.categories_list.customContextMenuRequested.connect(self.show_file_context_menu)

    def on_class_selection_changed(self):
        """
        Handle class selection changes
        """
        self.class_filter_changed.emit()

    def show_file_context_menu(self, pos):
        selected_items = self.categories_list.selectedItems()
        if not selected_items:
            return

        menu = QtWidgets.QMenu(self)

        action_delete_selected = menu.addAction("🗑 Delete Selected")
        action_clear_all = menu.addAction("🧹 Clear List")

        action = menu.exec_(self.categories_list.mapToGlobal(pos))

        if action == action_delete_selected:
            for item in selected_items:
                self.categories_list.takeItem(self.categories_list.row(item))
        elif action == action_clear_all:
            self.categories_list.clear()

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
