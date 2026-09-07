"""新建工程对话框。"""

import os
import configparser
import os.path
from PyQt5 import QtWidgets, QtGui
from quant.core.paths import icon_path


class NewProjectDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, current_project_dir=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setWindowIcon(QtGui.QIcon(icon_path("OpenFolder.ico")))

        # Initialize configuration path
        self.current_project_dir = current_project_dir
        self.save_dir = 'capture'

        # If there is a current project directory, try to load the save path from its configuration
        if current_project_dir and os.path.isdir(current_project_dir):
            config_path = os.path.join(self.current_project_dir, 'config.ini')
            if os.path.exists(config_path):
                config = configparser.ConfigParser()
                config.read(config_path)
                self.save_dir = config.get('DEFAULT', 'save_dir', fallback='capture')

        self.setup_ui()

    def setup_ui(self):
        # Use QVBoxLayout as main layout
        main_layout = QtWidgets.QVBoxLayout(self)

        # Form layout for input fields
        form_layout = QtWidgets.QFormLayout()

        # Project name input
        self.project_name_edit = QtWidgets.QLineEdit()
        # Handle case where current_project_dir is None
        if self.current_project_dir and os.path.isdir(self.current_project_dir):
            default_name = os.path.basename(self.current_project_dir)
        else:
            default_name = "new_project"
        self.project_name_edit.setText(default_name)
        self.project_name_edit.setPlaceholderText("Enter project name")
        form_layout.addRow("Project Name:", self.project_name_edit)

        # Project directory selection
        path_layout = QtWidgets.QHBoxLayout()
        self.path_edit = QtWidgets.QLineEdit()
        default_path = os.getcwd()  # Default to current working directory

        # If there is a current project directory, use its parent directory as default project root
        if self.current_project_dir and os.path.isdir(self.current_project_dir):
            default_path = os.path.dirname(self.current_project_dir)

        self.path_edit.setText(default_path)
        self.path_button = QtWidgets.QPushButton("...")
        self.path_button.clicked.connect(self.select_folder)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.path_button)
        form_layout.addRow("Save Path:", path_layout)

        # Save Path input
        save_path_layout = QtWidgets.QHBoxLayout()
        self.save_path_edit = QtWidgets.QLineEdit()
        self.save_path_edit.setText(self.save_dir)
        save_path_btn = QtWidgets.QPushButton("Select Path")
        save_path_btn.clicked.connect(self.select_save_dir)
        save_path_layout.addWidget(self.save_path_edit)
        save_path_layout.addWidget(save_path_btn)
        form_layout.addRow("Data Save Directory:", save_path_layout)

        # Add form layout to main layout
        main_layout.addLayout(form_layout)

        # Add hint information
        info_label = QtWidgets.QLabel("Hint: A project folder will be automatically generated at the specified path when creating a new project")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        main_layout.addWidget(info_label)

        # Button area
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def select_folder(self):
        """Select project root directory"""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Project Root Directory",
            self.path_edit.text() if os.path.isdir(self.path_edit.text()) else ""
        )
        if folder:
            self.path_edit.setText(folder)

    def select_save_dir(self):
        """Select save path"""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Data Save Path",
            self.save_path_edit.text() if os.path.isdir(self.save_path_edit.text()) else ""
        )
        if folder:
            self.save_path_edit.setText(folder)

    def get_inputs(self):
        """
        Get user input project information

        Returns:
            tuple: Contains project path, save path, project name
        """
        project_root = self.path_edit.text().strip()
        save_dir = self.save_path_edit.text().strip()
        project_name = self.project_name_edit.text().strip()

        # Ensure save path is relative to project path
        if save_dir.startswith(project_root):
            save_dir = os.path.relpath(save_dir, project_root)

        return (
            project_root,  # Project root path
            save_dir,  # Data save directory
            project_name  # Project name
        )
