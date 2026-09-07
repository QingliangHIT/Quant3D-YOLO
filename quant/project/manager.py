"""工程持久化管理：工程目录、配置读写与最近工程记录。"""

import configparser
import os
import os.path
import shutil

from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from quant.ui.dialogs.current_project_dialog import CurrentProjectDialog
from quant.ui.dialogs.new_project_dialog import NewProjectDialog


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

                with open(os.path.join(str(project_dir), 'config.ini'), 'w', encoding='utf-8') as f:
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
