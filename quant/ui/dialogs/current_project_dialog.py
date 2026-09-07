"""当前工程信息对话框。"""

from PyQt5 import QtWidgets, QtGui
from quant.core.paths import icon_path


class CurrentProjectDialog(QtWidgets.QDialog):
    def __init__(self, project_info, parent=None):
        super().__init__(parent)
        self.i_vid_label = None
        self.i_img_label = None
        self.save_dir_label = None
        self.project_dir_label = None
        self.setWindowTitle("Current Project Information")
        self.setWindowIcon(QtGui.QIcon(icon_path("About.ico")))
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
