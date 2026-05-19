import os
import configparser
from PyQt5.QtCore import QSettings
import os.path
from PyQt5 import QtWidgets, QtGui


class ProjectManager:
    def __init__(self, parent=None):
        self.parent = parent
        settings_path = os.path.join(os.getcwd(), 'settings.ini')
        self.settings = QSettings(settings_path, QSettings.IniFormat)
        self.current_project_dir = None
        self.save_dir = None
        self.i_img = 0
        self.i_vid = 0
        # Load last project
        last_project = self.settings.value("last_project")
        if last_project and os.path.isdir(last_project):
            self.current_project_dir = last_project
            self.load_config()
            self.parent.statusbar.showMessage(f"Automatically opened last project: {last_project}", 3000)

    def new_project(self):
        self.parent.is_modified = True
        dialog = NewProjectDialog(self.parent, self.current_project_dir)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            project_root, save_dir, project_name = dialog.get_inputs()

            if not project_root or not os.path.isdir(project_root):
                QtWidgets.QMessageBox.warning(self.parent, "Error", "Please select a valid project save path.")
                return
            if not project_name:
                QtWidgets.QMessageBox.warning(self.parent, "Notice", "Project name cannot be empty!")
                return

            project_dir = os.path.join(project_root, project_name)
            # if os.path.exists(project_dir):
            #     QtWidgets.QMessageBox.warning(self.parent, "Error", f"Project {project_name} already exists!")
            #     return

            try:
                os.makedirs(project_dir, exist_ok=True)

                # Create save_dir path
                os.makedirs(os.path.join(str(project_dir), save_dir), exist_ok=True)

                # Write to config.ini
                config = configparser.ConfigParser()
                config['DEFAULT'] = {
                    'save_dir': save_dir.replace("\\", "/"),
                    'i_img': str(0),
                    'i_vid': str(0)
                }

                with open(os.path.join(str(project_dir), 'config.ini'), 'w') as f:
                    config.write(f)

                self.current_project_dir = project_dir
                self.settings.setValue("last_project", project_dir)  # Save as recent project
                self.load_config()
                self.parent.statusbar.showMessage(f"Project {project_name} created successfully.", 3000)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self.parent, "Error", f"Failed to create project: {str(e)}")

    def open_project(self):
        project_dir = QtWidgets.QFileDialog.getExistingDirectory(self.parent, "Select Project Directory")
        if not project_dir:
            return

        config_path = os.path.join(project_dir, 'config.ini')
        if not os.path.exists(config_path):
            QtWidgets.QMessageBox.warning(self.parent, "Error", "This directory is not a valid project (missing config.ini)")
            return

        try:
            self.current_project_dir = project_dir
            self.load_config()
            self.parent.statusbar.showMessage(f"Project opened: {project_dir}", 3000)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.parent, "Error", f"Failed to load project: {str(e)}")
            self.current_project_dir = None

    def save_project(self):
        # 1. Basic validation
        if not getattr(self, 'current_project_dir', None):
            # QtWidgets.QMessageBox.information(self.parent, "Notice", "Please create or open a project first.")
            return

        # 2. Verify save path exists
        if not os.path.exists(self.current_project_dir):
            reply = QtWidgets.QMessageBox.question(
                self.parent,
                "Path Not Found",
                f"Project path {self.current_project_dir} does not exist. Do you want to reselect the project path?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
            )

            if reply == QtWidgets.QMessageBox.Yes:
                self.open_project()
            return

        try:
            # 3. Create backup (optional)
            config_path = os.path.join(self.current_project_dir, 'config.ini')
            if os.path.exists(config_path):
                import shutil
                backup_path = config_path + '.backup'
                shutil.copy2(config_path, backup_path)

            # 4. Data validation
            if self.save_dir is None:
                self.save_dir = 'capture'  # Set default value

            # 5. Save configuration
            config = configparser.ConfigParser()
            config['DEFAULT'] = {
                'save_dir': str(self.save_dir),
                'i_img': str(self.i_img),
                'i_vid': str(self.i_vid),
            }

            # 6. Ensure directory exists
            os.makedirs(self.current_project_dir, exist_ok=True)

            # 7. Write configuration file
            with open(config_path, 'w', encoding='utf-8') as f:
                config.write(f)

            # 8. Save to global settings
            self.settings.setValue("last_project", self.current_project_dir)
            self.parent.statusbar.showMessage("Project saved to config.ini", 3000)

        except PermissionError:
            QtWidgets.QMessageBox.critical(
                self.parent,
                "Permission Error",
                f"No permission to write project configuration file, please check directory permissions: {config_path}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.parent,
                "Save Failed",
                f"Error occurred while saving project configuration: {str(e)}"
            )

    def load_config(self):
        config_path = os.path.join(self.current_project_dir, 'config.ini')
        config = configparser.ConfigParser()
        config.read(config_path)

        self.save_dir = config.get('DEFAULT', 'save_dir', fallback='capture')
        self.i_img = int(config.get('DEFAULT', 'i_img', fallback='0'))
        self.i_vid = int(config.get('DEFAULT', 'i_vid', fallback='0'))

    def show_current_project_info(self):
        if not getattr(self, 'current_project_dir', None):
            QtWidgets.QMessageBox.information(self.parent, "Notice", "No project is currently open.")
            return

        project_info = {
            'project_dir': self.current_project_dir,
            'save_dir': self.save_dir,
            'i_img': self.i_img,
            'i_vid': self.i_vid,
        }

        dialog = CurrentProjectDialog(project_info, self.parent)
        dialog.exec_()


class NewProjectDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, current_project_dir=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setWindowIcon(QtGui.QIcon("UI/icon/new_project.svg"))

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


class CurrentProjectDialog(QtWidgets.QDialog):
    def __init__(self, project_info, parent=None):
        super().__init__(parent)
        self.i_vid_label = None
        self.i_img_label = None
        self.save_dir_label = None
        self.project_dir_label = None
        self.setWindowTitle("Current Project Information")
        self.setWindowIcon(QtGui.QIcon("UI/icon/info.svg"))
        self.setup_ui(project_info)

    def setup_ui(self, project_info):
        layout = QtWidgets.QFormLayout(self)

        # Display project information
        self.project_dir_label = QtWidgets.QLabel(project_info.get('project_dir', 'Unknown'))
        self.save_dir_label = QtWidgets.QLabel(project_info.get('save_dir', 'Unknown'))
        self.i_img_label = QtWidgets.QLabel(str(project_info.get('i_img', 'Unknown')))
        self.i_vid_label = QtWidgets.QLabel(str(project_info.get('i_vid', 'Unknown')))

        layout.addRow("Project Path:", self.project_dir_label)
        layout.addRow("Save Path:", self.save_dir_label)
        layout.addRow("Image Index:", self.i_img_label)
        layout.addRow("Video Index:", self.i_vid_label)

        # Close button
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addRow(button_box)
