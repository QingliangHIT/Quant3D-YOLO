"""三维控制面板：阈值/二值化参数、三维工具条与分割算子的调用入口。"""

import os
from PyQt5 import QtWidgets, QtCore, QtGui
from quant.core.config import IconSize
from quant.core.paths import icon_path
from quant.analysis import volume_info
from quant.imaging import highlight_ops, hole_ops, threshold_ops


class Control3DDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__("3D Control", parent)
        self.all_process = True
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        """Set up UI interface"""
        self.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)

        # Create main widget and layout
        self.widget = QtWidgets.QWidget()
        self.setWidget(self.widget)
        self.layout = QtWidgets.QVBoxLayout(self.widget)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 10, 10, 10)

        # Mask control section
        self.control_group = QtWidgets.QGroupBox("Process Control")
        self.control_layout = QtWidgets.QVBoxLayout(self.control_group)
        self.control_bt_layout = QtWidgets.QHBoxLayout()

        # Process all switch
        self.all_process_checkbox = QtWidgets.QCheckBox("Process All")
        self.all_process_checkbox.setChecked(True)
        self.control_bt_layout.addWidget(self.all_process_checkbox)
        self.binary_checkbox = QtWidgets.QCheckBox("Binarization")
        self.binary_checkbox.setChecked(True)
        self.control_bt_layout.addWidget(self.binary_checkbox)
        self.control_layout.addLayout(self.control_bt_layout)

        # Threshold input field
        self.threshold_layout = QtWidgets.QHBoxLayout()
        self.threshold_label = QtWidgets.QLabel("Threshold:")
        self.color_layout = QtWidgets.QHBoxLayout()
        self.color_label = QtWidgets.QLabel("Color:")

        self.threshold_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(255)
        self.threshold_slider.setValue(128)
        self.threshold_slider.setToolTip("Adjust segmentation threshold")
        self.color_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.color_slider.setMinimum(0)
        self.color_slider.setMaximum(255)
        self.color_slider.setValue(128)
        self.color_slider.setToolTip("Adjust binarization color value")

        self.threshold_value_label = QtWidgets.QLabel("128")
        self.threshold_value_label.setMinimumWidth(40)
        self.threshold_value_label.setAlignment(QtCore.Qt.AlignCenter)
        self.color_value_label = QtWidgets.QLabel("128")
        self.color_value_label.setMinimumWidth(40)
        self.color_value_label.setAlignment(QtCore.Qt.AlignCenter)
        self.threshold_layout.addWidget(self.threshold_label, 2)
        self.threshold_layout.addWidget(self.threshold_slider, 4)
        self.threshold_layout.addWidget(self.threshold_value_label, 1)
        self.color_layout.addWidget(self.color_label, 2)
        self.color_layout.addWidget(self.color_slider, 4)
        self.color_layout.addWidget(self.color_value_label, 1)

        self.control_layout.addLayout(self.threshold_layout)

        # Colormap options
        self.colormap_layout = QtWidgets.QHBoxLayout()
        # Colormap selection
        self.colormap_layout_label = QtWidgets.QLabel("Colormap:")
        self.colormap_combo = QtWidgets.QComboBox()
        self.colormap_combo.addItem("Viridis", "viridis")
        self.colormap_combo.addItem("Plasma", "plasma")
        self.colormap_combo.addItem("Inferno", "inferno")
        self.colormap_combo.addItem("Magma", "magma")
        self.colormap_combo.addItem("Jet", "jet")
        self.colormap_combo.addItem("Hot", "hot")
        self.colormap_combo.addItem("Gray", "gray")
        self.colormap_combo.setCurrentText("Viridis")

        self.colormap_layout.addWidget(self.colormap_layout_label)
        self.colormap_layout.addWidget(self.colormap_combo)
        self.control_layout.addLayout(self.colormap_layout)
        self.control_layout.addLayout(self.color_layout)

        # Add to main layout
        self.layout.addWidget(self.control_group)
        self.layout.addStretch()

    def create_toolbar(self):
        """Create and add toolbar to parent window"""
        self.toolbar_3d = QtWidgets.QToolBar("3D Control Tools", self.parent)
        self.toolbar_3d.setFont(QtGui.QFont("Times New Roman", 12))
        self.toolbar_3d.setIconSize(QtCore.QSize(IconSize, IconSize))
        self.toolbar_3d.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.toolbar_3d.setObjectName("3DControlToolBar")

        # 3D view button
        self.action_3d_view = QtWidgets.QAction(self.parent)
        self.action_3d_view.setIcon(QtGui.QIcon(icon_path("View3D.ico")))
        self.action_3d_view.setText("3D View")
        self.action_3d_view.setCheckable(True)
        self.action_3d_view.setToolTip("Show/Hide 3D view")
        self.toolbar_3d.addAction(self.action_3d_view)

        self.toolbar_3d.addSeparator()

        # Operation buttons
        self.action_hole = QtWidgets.QAction(self.parent)
        self.action_hole.setIcon(QtGui.QIcon(icon_path("Segmentation.ico")))
        self.action_hole.setText("Hole")
        self.action_hole.setToolTip("Apply hole operation to selected class areas")
        self.toolbar_3d.addAction(self.action_hole)

        self.action_highlight = QtWidgets.QAction(self.parent)
        self.action_highlight.setIcon(QtGui.QIcon(icon_path("Highlight.ico")))
        self.action_highlight.setText("Highlight")
        self.action_highlight.setToolTip("Highlight selected class areas")
        self.toolbar_3d.addAction(self.action_highlight)

        self.action_holeleave = QtWidgets.QAction(self.parent)
        self.action_holeleave.setIcon(QtGui.QIcon(icon_path("Leave.ico")))
        self.action_holeleave.setText("Show Hole")
        self.action_holeleave.setToolTip("Show only selected class areas")
        self.toolbar_3d.addAction(self.action_holeleave)

        self.action_mark = QtWidgets.QAction(self.parent)
        self.action_mark.setIcon(QtGui.QIcon(icon_path("Tag.ico")))
        self.action_mark.setText("Mark")
        self.action_mark.setToolTip("Mark selected class areas on image")
        self.toolbar_3d.addAction(self.action_mark)

        self.toolbar_3d.addSeparator()

        self.action_threshold = QtWidgets.QAction(self.parent)
        self.action_threshold.setIcon(QtGui.QIcon(icon_path("SegmentationThreshold.ico")))
        self.action_threshold.setText("Threshold Segmentation")
        self.action_threshold.setToolTip("Segment image based on input threshold")
        self.toolbar_3d.addAction(self.action_threshold)

        self.action_calcu_2d = QtWidgets.QAction(self.parent)
        self.action_calcu_2d.setIcon(QtGui.QIcon(icon_path("Information2D.ico")))
        self.action_calcu_2d.setText("2D Calculation")
        self.action_calcu_2d.setToolTip("Calculate features for current page")
        self.toolbar_3d.addAction(self.action_calcu_2d)

        self.action_calcu_3d = QtWidgets.QAction(self.parent)
        self.action_calcu_3d.setIcon(QtGui.QIcon(icon_path("Information3D.ico")))
        self.action_calcu_3d.setText("3D Calculation")
        self.action_calcu_3d.setToolTip("Calculate features for voxels")
        self.toolbar_3d.addAction(self.action_calcu_3d)

    def show_toolbar(self):
        """Show toolbar"""
        # Add to main window's top toolbar area
        if hasattr(self, 'toolbar_3d'):
            self.toolbar_3d.show()
        else:
            self.create_toolbar()
            self.setup_connections()
            self.parent.addToolBar(QtCore.Qt.TopToolBarArea, self.toolbar_3d)

    def hide_toolbar(self):
        """Hide toolbar"""
        if hasattr(self, 'toolbar_3d'):
            self.toolbar_3d.hide()

    def setup_connections(self):
        """Connect signals and slots"""
        # Toolbar button connections
        self.action_3d_view.triggered.connect(self.on_3d_view_toggled)
        self.action_hole.triggered.connect(self.apply_hole_operation)
        self.action_highlight.triggered.connect(self.apply_highlight_operation)
        self.action_holeleave.triggered.connect(self.apply_holeshow_operation)
        self.action_mark.triggered.connect(self.apply_mark_operation)
        self.action_threshold.triggered.connect(self.apply_threshold_operation)
        self.action_calcu_2d.triggered.connect(self.calculate_2d_info)
        self.action_calcu_3d.triggered.connect(self.calculate_3d_info)

        # Dock internal button connections
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        self.colormap_combo.currentIndexChanged.connect(self.on_colormap_changed)
        self.color_slider.valueChanged.connect(self.on_color_changed)

        # Other connections
        self.all_process_checkbox.stateChanged.connect(self.on_process_changed)

    def on_colormap_changed(self, index):
        """Handle colormap changes"""
        # Get current ImagesViewer instance
        images_viewer = self.parent.tab_widget.currentWidget()
        colormap = self.colormap_combo.currentData()
        if hasattr(images_viewer, 'plotter_3d') and images_viewer.plotter_3d is not None:
            self.parent.statusbar.showMessage(f"Colormap changed to: {self.colormap_combo.currentText()}", 2000)
            images_viewer.refresh_3d_view(colormap)

    def get_colormap(self):
        """
        Get currently selected colormap
        :return: Colormap name string
        """
        return self.colormap_combo.currentData()

    def on_threshold_changed(self, value):
        """Handle threshold changes"""
        self.threshold_value_label.setText(str(value))
        # Process current image in real-time
        self.apply_threshold_to_current_image(value)

    def on_color_changed(self, value):
        """Handle color changes"""
        self.color_value_label.setText(str(value))
        # Process current 3d view in real-time
        # self.color_changed.emit(value)

    def apply_threshold_to_current_image(self, threshold_value):
        return threshold_ops.apply_threshold_to_current_image(self, threshold_value)

    def on_3d_view_toggled(self, checked):
        """3D view toggle"""
        # Get current ImagesViewer instance
        images_viewer = self.parent.tab_widget.currentWidget()
        if checked:
            images_viewer.show_3d()
        else:
            images_viewer.hide_3d()

    def on_process_changed(self, state):
        """Mask display state change"""
        visible = state == QtCore.Qt.Checked
        self.all_process = visible
        # self.mask_visibility_changed.emit(visible)

    def apply_hole_operation(self):
        return hole_ops.apply_hole_operation(self)

    def apply_highlight_operation(self):
        return highlight_ops.apply_highlight_operation(self)

    def apply_holeshow_operation(self):
        return hole_ops.apply_holeshow_operation(self)

    def apply_mark_operation(self):
        return highlight_ops.apply_mark_operation(self)

    def apply_threshold_operation(self):
        return threshold_ops.apply_threshold_operation(self)

    def calculate_2d_info(self):
        volume_info.calculate_2d_info(self)

    @staticmethod
    def get_label_path(file_path, label_dir):
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        if len(label_dir) > 0:
            matched_files = []
            for label_file in label_dir:
                label_base = os.path.splitext(os.path.basename(label_file))[0]
                if label_base == base_name:
                    matched_files.append(label_file)
            if matched_files:
                for label_file in matched_files:
                    _, ext = os.path.splitext(label_file)
                    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", }:
                        return label_file
        return None

    def calculate_3d_info(self):
        return volume_info.calculate_3d_info(self)
