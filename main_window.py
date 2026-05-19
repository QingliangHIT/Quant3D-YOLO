import os
import cv2
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import sip
from PyQt5.QtCore import Qt
from UI.dock.dock_file import FilesDock
from UI.dock.dock_info import InfoDock
from UI.dock.dock_anno import AnnoDock
from UI.dock.dock_categories import CategoriesDock
from UI.dock.dock_camera import ControlDock, CameraFilesDock
from UI.dock.dock_yolo import YoloDock
from UI.dock.dock_contrl3d import Control3DDock
from UI.tools.tool_calibration import CalibrationSettingsDialog, CalibrationDetector, CalibrationDialog
from UI.viewer.viewerCamera import CameraWindow
from UI.viewer.viewerImage import ImageViewer
from UI.viewer.viewerImages import ImagesViewer
from UI.customTab import CustomTabWidget
from UI.dialog.dialog_setting import SettingsDialog, MaskControlDialog
from UI.control.project_manager import ProjectManager
from UI.tools.tool_pulseControl import PulseControlDialog
from UI.tools.tool_plot_yolo import YOLOPlotter
from UI.tools.utils import *
from UI.control.config import IconSize
from UI.tools.utils import *


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.yolo_model = None
        self.yolo_model_name = None
        self.images_view_page = None
        self.plotter = None
        self.current_state = 0
        self.detector = None
        self.settings_dialog = None
        self.control3D_dock = None
        self.image_view_page = None
        self.images_view_page = None
        self.setup_variables()
        # Initialize settings
        self.setup_ui()
        self.project_manager = ProjectManager(self)  # Initialize project manager
        if not getattr(self, 'current_project_dir', None):
            self.statusbar.showMessage("⚠️ Please create or open a project first", 3000)

        self.control3D_dock = Control3DDock(self)
        self.setup_connections()
        QtWidgets.QApplication.processEvents()
        self.action_toggle_images_view.setChecked(True)
        self.toggle_images_view()
        self.check_state()
        self.change_theme('浅色')
        self.action_show_label.setChecked(True)
        self.action_show_yolo.setChecked(True)
        self.show_label()
        self.show_yolo()

    def check_state(self):
        if isinstance(self.tab_widget.currentWidget(), (ImageViewer, ImagesViewer)):
            self.current_state = 1
            self.addDockWidget(QtCore.Qt.DockWidgetArea(1), self.files_dock)
            self.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.info_dock)
            self.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.annos_dock)
            self.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.categories_dock)
            self.addDockWidget(QtCore.Qt.DockWidgetArea(1), self.yolo_dock)
            self.addDockWidget(QtCore.Qt.DockWidgetArea(1), self.control3D_dock)
            self.control3D_dock.hide()

            for dock in self.dock_dict:
                if dock in [self.dock_dict[i] for i in self.image_view_page_source]:
                    dock.setVisible(True)
                else:
                    dock.setVisible(False)
        elif self.tab_widget.currentWidget() == self.camera_page:
            self.current_state = 2
            self.addDockWidget(QtCore.Qt.DockWidgetArea(1), self.camera_files_dock)
            self.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.info_dock)
            self.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.camera_control_dock)
            for dock in self.dock_dict:
                if dock in [self.dock_dict[i] for i in self.camera_page_source]:
                    dock.setVisible(True)
                else:
                    dock.setVisible(False)
        else:
            self.current_state = 0
            for dock in self.dock_dict:
                self.removeDockWidget(dock)
            for dock in self.dock_dict:
                dock.setVisible(False)

    def setup_variables(self):
        """
        Set application variables
        """
        self.current_file = None
        self.is_modified = False
        # Add mouse drag related variables
        self.mouse_pressed = False
        self.last_mouse_pos = None
        # Added: fixed size mode state variable
        self.is_fixed_size = True

    def setup_ui(self):
        """
        Set up user interface
        """
        # Window basic settings
        self.setObjectName("MainWindow")
        self.resize(1600, 900)
        self.setMinimumSize(QtCore.QSize(800, 600))

        # Set font
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(12)
        self.setFont(font)

        # Set window icon
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("./UI/icons/ico/SOFT.ico"),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)

        # Central widget
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.setCentralWidget(self.centralwidget)

        # Create QTabWidget for page switching
        self.tab_widget = CustomTabWidget(self)  # Replace with custom CustomTabWidget
        self.horizontalLayout.addWidget(self.tab_widget)

        # Create camera page
        self.camera_page = CameraWindow(self)
        # Menu bar
        self.setup_menubar()

        # Status bar
        self.statusbar = QtWidgets.QStatusBar(self)
        self.statusbar.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        # Toolbars
        self.setup_toolbar()

        # Dock widgets
        self.setup_docks()

        self.retranslate_ui()
        QtCore.QMetaObject.connectSlotsByName(self)

    def setup_menubar(self):
        """
        Set up menu bar
        """
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setEnabled(True)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1600, 25))
        self.menubar.setFont(QtGui.QFont("Times New Roman", 12))
        self.menubar.setObjectName("menubar")

        # Create menus
        self.menu_file = QtWidgets.QMenu(self.menubar)
        self.menu_edit = QtWidgets.QMenu(self.menubar)
        self.menu_view = QtWidgets.QMenu(self.menubar)
        self.menu_tools = QtWidgets.QMenu(self.menubar)
        self.menu_help = QtWidgets.QMenu(self.menubar)

        # Set menu properties
        for menu in [self.menu_file, self.menu_edit, self.menu_view,
                     self.menu_tools, self.menu_help, ]:
            menu.setFont(QtGui.QFont("Times New Roman", 12))

        # Set menu titles
        self.menu_file.setTitle("File")
        self.menu_edit.setTitle("Edit")
        self.menu_view.setTitle("View")
        self.menu_tools.setTitle("Tools")
        self.menu_help.setTitle("Help")
        # self.menu_calibration.setTitle("Calibrator")
        # self.menu_controller.setTitle("Controller")

        # Add menu items
        self.setup_menu_items()

        # Add menus to menu bar
        self.menubar.addAction(self.menu_file.menuAction())
        self.menubar.addAction(self.menu_edit.menuAction())
        self.menubar.addAction(self.menu_view.menuAction())
        self.menubar.addAction(self.menu_tools.menuAction())
        self.menubar.addAction(self.menu_help.menuAction())
        # self.menu_tools.addAction(self.menu_calibration.menuAction())
        # self.menubar.addAction(self.menu_calibration.menuAction())
        # self.menubar.addAction(self.menu_controller.menuAction())


        self.setMenuBar(self.menubar)

    def setup_toolbar(self):
        """
        Set up toolbars
        """
        # Main toolbar
        self.toolBar = QtWidgets.QToolBar(self)
        self.toolBar.setFont(QtGui.QFont("Times New Roman", 12))
        self.toolBar.setIconSize(QtCore.QSize(IconSize, IconSize))
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.toolBar.setFloatable(True)
        self.toolBar.setObjectName("toolBar")

        # Right toolbar
        self.toolBar_right = QtWidgets.QToolBar(self)
        self.toolBar_right.setMovable(False)
        self.toolBar_right.setFloatable(False)
        self.toolBar_right.setObjectName("toolBar_right")

        # Add toolbars
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.addToolBar(QtCore.Qt.RightToolBarArea, self.toolBar_right)

        # Set toolbar buttons
        self.setup_toolbar_buttons()

    def setup_docks(self):
        """
        Set up dock widgets
        """
        # Files dock widget
        self.files_dock = FilesDock(self)

        # Info dock widget
        self.info_dock = InfoDock(self)

        # Annotations dock widget
        self.annos_dock = AnnoDock(self)

        # Categories dock widget
        self.categories_dock = CategoriesDock(self)

        # Camera control dock widget
        self.camera_control_dock = ControlDock(self)

        # Camera files dock widget
        self.camera_files_dock = CameraFilesDock(self)

        # YOLO parameters dock widget
        self.yolo_dock = YoloDock(self)

        # Add dock widgets
        self.dock_dict = [self.files_dock, self.info_dock, self.annos_dock, self.categories_dock, self.camera_control_dock, self.camera_files_dock, self.yolo_dock]
        self.image_view_page_source = [0, 1, 2, 3]
        self.camera_page_source = [1, 4, 5]

    def setup_menu_items(self):
        """
        Set up menu items
        """
        # File menu
        self.action_open = QtWidgets.QAction(self)
        self.action_open.setIcon(QtGui.QIcon("UI/icons/ico/OpenFiles.ico"))
        self.action_open.setText("Open")
        self.action_open.setShortcut("Ctrl+O")

        # Add open folder action
        self.action_open_folder = QtWidgets.QAction(self)
        self.action_open_folder.setIcon(QtGui.QIcon("UI/icons/ico/OpenFolder.ico"))
        self.action_open_folder.setText("Open Folder")
        self.action_open_folder.setShortcut("Ctrl+Shift+O")

        self.action_exit = QtWidgets.QAction(self)
        self.action_exit.setIcon(QtGui.QIcon("UI/icons/ico/Exit.ico"))
        self.action_exit.setText("Exit")
        self.action_exit.setShortcut("Ctrl+Q")

        self.action_open_project = QtWidgets.QAction(self)
        self.action_open_project.setIcon(QtGui.QIcon("UI/icons/ico/SaveFile.ico"))  # Icon can be customized
        self.action_open_project.setText("Open")

        self.action_new_project = QtWidgets.QAction(self)
        self.action_new_project.setIcon(QtGui.QIcon("UI/icons/ico/SaveFile.ico"))  # Optional icon
        self.action_new_project.setText("New")
        self.action_new_project.setShortcut("Ctrl+N")

        self.action_current_project = QtWidgets.QAction(self)
        self.action_current_project.setIcon(QtGui.QIcon("UI/icons/ico/SaveFile.ico"))  # Prepare an icon
        self.action_current_project.setText("Current")

        self.action_save_project = QtWidgets.QAction(self)
        self.action_save_project.setIcon(QtGui.QIcon("UI/icons/ico/SaveFile.ico"))  # Optional icon
        self.action_save_project.setText("Save")
        self.action_save_project.setShortcut("Ctrl+Shift+S")

        self.action_load_project = QtWidgets.QAction(self)
        self.action_load_project.setIcon(QtGui.QIcon("UI/icons/ico/SaveFile.ico"))  # Optional icon
        self.action_load_project.setText("Load")
        self.action_load_project.setShortcut("Ctrl+Shift+L")

        self.action_load_label_paths = QtWidgets.QAction(self)
        self.action_load_label_paths.setIcon(QtGui.QIcon("UI/icons/ico/Label.ico"))  # Optional icon
        self.action_load_label_paths.setText("Load Label Paths")

        self.menu_file.addAction(self.action_open_project)
        self.menu_file.addAction(self.action_new_project)
        self.menu_file.addAction(self.action_save_project)
        self.menu_file.addAction(self.action_current_project)
        self.menu_file.addAction(self.action_load_project)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_open)
        self.menu_file.addAction(self.action_open_folder)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_load_label_paths)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_exit)

        # Edit menu
        self.action_undo = QtWidgets.QAction(self)
        self.action_undo.setIcon(QtGui.QIcon(r"UI/icons/ico/Last.ico"))
        self.action_undo.setText("Undo")
        self.action_undo.setShortcut("Ctrl+Z")

        self.action_redo = QtWidgets.QAction(self)
        self.action_redo.setIcon(QtGui.QIcon("UI/icons/ico/Next.ico"))
        self.action_redo.setText("Redo")
        self.action_redo.setShortcut("Ctrl+Y")

        self.action_zoom_in = QtWidgets.QAction(self)
        self.action_zoom_in.setIcon(QtGui.QIcon("UI/icons/ico/ZoomIn.ico"))
        self.action_zoom_in.setText("Zoom In")
        self.action_zoom_in.setShortcut("Ctrl+=")

        self.action_zoom_out = QtWidgets.QAction(self)
        self.action_zoom_out.setIcon(QtGui.QIcon("UI/icons/ico/ZoomOut.ico"))
        self.action_zoom_out.setText("Zoom Out")
        self.action_zoom_out.setShortcut("Ctrl+-")

        # Add new adaptive window action
        self.action_fit_window = QtWidgets.QAction("Fit Window", self)
        self.action_fit_window.setCheckable(True)
        self.action_fit_window.setChecked(True)
        self.action_fit_window.setIcon(QtGui.QIcon("UI/icons/ico/FitWindow.ico"))
        self.action_fit_window.setShortcut("Ctrl+F")

        self.menu_edit.addAction(self.action_undo)
        self.menu_edit.addAction(self.action_redo)
        self.menu_edit.addAction(self.action_zoom_in)
        self.menu_edit.addAction(self.action_zoom_out)
        self.menu_edit.addAction(self.action_fit_window)

        # View menu
        # Add hide/show image view and camera interface menu items
        self.action_toggle_image_view = QtWidgets.QAction("Image View", self)
        self.action_toggle_image_view.setIcon(QtGui.QIcon("UI/icons/ico/View.ico"))
        self.action_toggle_image_view.setCheckable(True)
        self.action_toggle_image_view.setChecked(True)

        self.action_toggle_images_view = QtWidgets.QAction("Images View", self)
        self.action_toggle_images_view.setIcon(QtGui.QIcon("UI/icons/ico/ViewPool.ico"))
        self.action_toggle_images_view.setCheckable(True)
        self.action_toggle_images_view.setChecked(False)

        self.action_toggle_camera_view = QtWidgets.QAction("Camera View", self)
        self.action_toggle_camera_view.setIcon(QtGui.QIcon("UI/icons/ico/Camera.ico"))
        self.action_toggle_camera_view.setCheckable(True)
        self.action_toggle_camera_view.setChecked(False)

        self.action_toggle_stereo_view = QtWidgets.QAction("Stereo Camera", self)
        self.action_toggle_stereo_view.setIcon(QtGui.QIcon("UI/icons/ico/StereoCamera.ico"))
        self.action_toggle_stereo_view.setCheckable(True)
        self.action_toggle_stereo_view.setChecked(False)

        self.menu_view.addAction(self.action_toggle_image_view)
        self.menu_view.addAction(self.action_toggle_images_view)
        self.menu_view.addAction(self.action_toggle_camera_view)
        self.menu_view.addAction(self.action_toggle_stereo_view)

        self.action_show_label = QtWidgets.QAction("Show Label")
        self.action_show_label.setIcon(QtGui.QIcon("UI/icons/ico/Label.ico"))
        self.action_show_label.setCheckable(True)

        self.action_show_yolo = QtWidgets.QAction("Show YOLO Results")
        self.action_show_yolo.setIcon(QtGui.QIcon("UI/icons/ico/LabelYOLO.ico"))
        self.action_show_yolo.setCheckable(True)

        self.action_show_calibration = QtWidgets.QAction(self)
        self.action_show_calibration.setIcon(QtGui.QIcon("UI/icons/ico/Calibration.ico"))
        self.action_show_calibration.setText("Show Calibration")
        self.action_show_calibration.setCheckable(True)
        self.menu_tools.addAction(self.action_show_label)
        self.menu_tools.addAction(self.action_show_yolo)
        self.menu_tools.addAction(self.action_show_calibration)
        self.menu_tools.addSeparator()
        # YOLO detection action
        self.action_yolo_detect = QtWidgets.QAction(self)
        self.action_yolo_detect.setIcon(QtGui.QIcon("UI/icons/ico/Detection.ico"))  # Can be replaced with a more suitable icon
        self.action_yolo_detect.setText("YOLO Detect")
        self.action_yolo_detect.setCheckable(True)
        self.menu_tools.addAction(self.action_yolo_detect)
        # Add point detection action
        self.action_yolo_point_detect = QtWidgets.QAction(self)
        self.action_yolo_point_detect.setIcon(QtGui.QIcon("UI/icons/ico/DetectionPoint.ico"))  # Can be replaced with a more suitable icon
        self.action_yolo_point_detect.setText("YOLO Point Detect")
        self.action_yolo_point_detect.setCheckable(True)
        self.menu_tools.addAction(self.action_yolo_point_detect)

        self.menu_calibration = QtWidgets.QMenu("Camera Calibration", self.menu_tools)
        self.menu_tools.addMenu(self.menu_calibration)
        self.menu_calibration.setIcon(QtGui.QIcon("UI/icons/ico/Calibration.ico"))
        self.menu_tools.addAction(self.menu_calibration.menuAction())

        self.action_mask_calcu = QtWidgets.QAction(self)
        self.action_mask_calcu.setIcon(QtGui.QIcon("UI/icons/ico/Label.ico"))  # 需要准备图标
        self.action_mask_calcu.setText("Mask for Calculation")
        self.menu_tools.addAction(self.action_mask_calcu)

        # Tools menu
        self.action_settings = QtWidgets.QAction(self)
        self.action_settings.setIcon(QtGui.QIcon("UI/icons/ico/Settings.ico"))
        self.action_settings.setText("Settings")
        self.menu_tools.addAction(self.action_settings)

        # Add fullscreen mode menu item
        self.action_fullscreen = QtWidgets.QAction(self)
        self.action_fullscreen.setIcon(QtGui.QIcon("UI/icons/ico/full.ico"))
        self.action_fullscreen.setText("Fullscreen")
        self.action_fullscreen.setCheckable(True)
        self.menu_view.addAction(self.action_fullscreen)

        # Calibration menu
        # Add calibration submenu items
        self.action_start_calibration = QtWidgets.QAction(self)
        self.action_start_calibration.setText("Start Calibration")

        self.action_realtime_detect = QtWidgets.QAction(self)
        self.action_realtime_detect.setText("Realtime detect")
        self.action_realtime_detect.setCheckable(True)

        self.action_corner_detector = QtWidgets.QAction(self)
        self.action_corner_detector.setText("Load Corner Detector")
        self.action_corner_detector.setCheckable(True)

        self.action_pulse_control = QtWidgets.QAction(self)
        self.action_pulse_control.setIcon(QtGui.QIcon("UI/icons/ico/SaveFile.ico"))
        self.action_pulse_control.setText("Pulse Control")

        self.menu_calibration.addAction(self.action_realtime_detect)
        self.menu_calibration.addSeparator()
        self.menu_calibration.addAction(self.action_start_calibration)
        self.menu_calibration.addAction(self.action_corner_detector)
        self.menu_calibration.addAction(self.action_pulse_control)
        # Help menu
        self.action_about = QtWidgets.QAction(self)
        self.action_about.setIcon(QtGui.QIcon("UI/icons/ico/About.ico"))
        self.action_about.setText("About")

        self.menu_help.addAction(self.action_about)

    def setup_toolbar_buttons(self):
        """
        Set up toolbar buttons
        """
        # Main toolbar buttons
        self.toolBar.addAction(self.action_open)
        self.toolBar.addAction(self.action_open_folder)
        self.toolBar.addAction(self.action_save_project)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.action_undo)
        self.toolBar.addAction(self.action_redo)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.action_fit_window)
        self.toolBar.addAction(self.action_zoom_in)
        self.toolBar.addAction(self.action_zoom_out)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.action_toggle_image_view)
        self.toolBar.addAction(self.action_toggle_images_view)
        self.toolBar.addAction(self.action_toggle_camera_view)
        self.toolBar.addAction(self.action_toggle_stereo_view)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.action_show_calibration)
        self.toolBar.addAction(self.action_show_label)
        self.toolBar.addAction(self.action_show_yolo)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.action_yolo_detect)
        self.toolBar.addAction(self.action_yolo_point_detect)

        # Right toolbar buttons
        self.toolBar_right.addAction(self.action_settings)
        # Right toolbar, add elastic space
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.toolBar_right.insertWidget(self.action_settings, spacer)
        self.toolBar_right.addAction(self.action_about)

    def setup_connections(self):
        """
        Set up signal and slot connections
        """
        self.action_new_project.triggered.connect(self.project_manager.new_project)
        self.action_open_project.triggered.connect(self.project_manager.open_project)
        self.action_save_project.triggered.connect(self.project_manager.save_project)
        self.action_current_project.triggered.connect(self.project_manager.show_current_project_info)
        self.action_load_project.triggered.connect(self.load_save_dir)
        self.action_exit.triggered.connect(self.close)
        self.action_about.triggered.connect(self.show_about_dialog)
        self.action_open.triggered.connect(self.load_image)
        self.action_open_folder.triggered.connect(self.load_folder)

        self.action_redo.triggered.connect(lambda: self.files_dock.prev_image(None))
        self.action_undo.triggered.connect(lambda: self.files_dock.next_image(None))
        self.action_zoom_in.triggered.connect(self.zoom_in)
        self.action_zoom_out.triggered.connect(self.zoom_out)

        self.action_toggle_image_view.triggered.connect(self.toggle_image_view)
        self.action_toggle_images_view.triggered.connect(self.toggle_images_view)
        self.action_toggle_camera_view.triggered.connect(self.toggle_camera_view)
        self.action_toggle_stereo_view.triggered.connect(self.toggle_stereo_view)
        self.action_fullscreen.triggered.connect(self.toggle_fullscreen)

        self.action_fit_window.triggered.connect(self.toggle_fit_window)

        self.tab_widget.currentChanged.connect(self.check_state)
        self.action_settings.triggered.connect(self.show_settings_dialog)

        self.action_corner_detector.triggered.connect(self.load_corner_detection)

        self.action_load_label_paths.triggered.connect(self.files_dock.load_all_labels)
        self.action_show_label.triggered.connect(self.show_label)
        self.action_show_yolo.triggered.connect(self.show_yolo)
        self.action_mask_calcu.triggered.connect(self.load_mask_calcu)

        self.action_show_calibration.triggered.connect(self.show_detect_results)
        self.action_realtime_detect.triggered.connect(self.realtime_detect)
        self.action_pulse_control.triggered.connect(self.show_pulse_control_dialog)
        self.action_start_calibration.triggered.connect(self.show_calibrator_dialog)
        self.action_yolo_detect.triggered.connect(self.toggle_yolo_detection)
        self.action_yolo_point_detect.triggered.connect(self.toggle_yolo_point_detection)
        # Connect YOLO parameters dock signals
        self.yolo_dock.yolo_model_changed.connect(self.on_yolo_model_changed)
        self.yolo_dock.yolo_conf_threshold_changed.connect(self.on_yolo_conf_threshold_changed)
        self.yolo_dock.yolo_iou_threshold_changed.connect(self.on_yolo_iou_threshold_changed)
        self.yolo_dock.class_filter_changed.connect(self.reload_img_view)

    def show_calibrator_dialog(self):
        if not hasattr(self, "calibrator_dialog"):
            folder_path = str(os.path.join(self.project_manager.current_project_dir, self.project_manager.save_dir))
            self.calibrator_dialog = CalibrationDialog(self, self.detector, square_size=40, image_dir=folder_path)
        self.calibrator_dialog.show()

    def zoom_in(self):
        """放大当前视图"""
        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, 'zoom_in'):
            current_widget.zoom_in()
            self.statusbar.showMessage("Zoomed in", 1000)

    def zoom_out(self):
        """缩小当前视图"""
        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, 'zoom_out'):
            current_widget.zoom_out()
            self.statusbar.showMessage("Zoomed out", 1000)

    def load_mask_calcu(self):
        control_dialog = MaskControlDialog(self)
        control_dialog.exec_()

    def _load_single_mask_file(self, current_widget):
        """加载单个掩码文件"""
        mask_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Mask File",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.tif);;All Files (*)"
        )

        if mask_file:
            try:
                mask = cv2.imread(mask_file, cv2.IMREAD_GRAYSCALE)
                if mask is not None:
                    # 将掩码赋值给当前widget
                    current_widget.mask_calcu = get_img_color(~mask, 3 + self.plotter.offset), mask, mask_file

                    # 更新显示
                    if hasattr(current_widget, 'img'):
                        current_widget.load_image()

                    self.statusbar.showMessage(f"✅ Mask loaded: {os.path.basename(mask_file)}", 3000)
                else:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Warning",
                        "Failed to load mask file. Please check the file format."
                    )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error",
                    f"Error loading mask file:\n{str(e)}"
                )

    def _load_mask_from_directory(self, current_widget):
        """从目录加载掩码文件"""
        # 选择目录
        mask_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Mask Directory"
        )

        if not mask_dir:
            return  # 用户取消

        # 获取目录中的所有掩码文件
        mask_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']
        mask_files = [
            os.path.join(mask_dir, f) for f in os.listdir(mask_dir)
            if any(f.lower().endswith(ext) for ext in mask_extensions)
        ]

        if not mask_files:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "No mask files found in the selected directory."
            )
            return

        # 将掩码文件路径列表存储到 mask_calcu
        current_widget.mask_calcu = mask_files
        self.statusbar.showMessage(f"✅ Loaded {len(mask_files)} mask files from directory", 3000)

    def _load_detection_results(self, current_widget):
        """从检测结果加载掩码"""
        # 检查是否有检测结果
        if not hasattr(current_widget, 'yolo_results') or not current_widget.yolo_results:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "No detection results available. Run detection first."
            )
            return

        # 获取当前图像的路径
        current_image_path = current_widget.img[0] if hasattr(current_widget, 'img') and current_widget.img else None

        if not current_image_path or current_image_path not in current_widget.yolo_results:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "No detection results for current image."
            )
            return

        # 从检测结果创建掩码
        detection_result = current_widget.yolo_results[current_image_path]

        # 根据检测结果创建掩码
        if hasattr(detection_result, 'masks') and detection_result.masks is not None:
            # 如果有分割掩码
            masks = detection_result.masks.data.cpu().numpy()
            if len(masks) > 0:
                # 合并所有掩码
                combined_mask = np.zeros(masks[0].shape, dtype=np.uint8)
                for mask in masks:
                    combined_mask = np.maximum(combined_mask, (mask * 255).astype(np.uint8))

                # 创建掩码元组并赋值
                current_widget.mask_calcu = get_img_color(~combined_mask,
                                                          3 + self.plotter.offset), combined_mask, f"detection_result_{current_image_path}"
                self.statusbar.showMessage("✅ Mask loaded from detection results", 3000)

                # 更新显示
                if hasattr(current_widget, 'img'):
                    current_widget.load_image()
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Warning",
                    "No masks found in detection results."
                )
        else:
            # 如果只有边界框，可以创建边界框对应的掩码
            if hasattr(detection_result, 'boxes') and detection_result.boxes is not None:
                boxes = detection_result.boxes.xyxy.cpu().numpy()
                img_height, img_width = current_widget.img[1].shape[:2] if hasattr(current_widget,
                                                                                   'img') and current_widget.img else (
                    480, 640)

                mask = np.zeros((img_height, img_width), dtype=np.uint8)
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box)
                    mask[y1:y2, x1:x2] = 255

                current_widget.mask_calcu = get_img_color(~mask,
                                                          3 + self.plotter.offset), mask, f"detection_boxes_{current_image_path}"
                self.statusbar.showMessage("✅ Mask loaded from detection boxes", 3000)

                # 更新显示
                if hasattr(current_widget, 'img'):
                    current_widget.load_image()
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Warning",
                    "No masks or bounding boxes in detection results."
                )

    def _load_labels(self, current_widget):
        """从标签文件加载掩码"""
        # 选择标签文件
        label_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Label File",
            "",
            "Label Files (*.txt *.json *.xml *.yaml *.yml);;All Files (*)"
        )

        if not label_file:
            return  # 用户取消

        try:
            # 根据标签格式处理不同类型的标签文件
            if label_file.endswith('.txt'):
                # YOLO格式的标签
                mask = self._create_mask_from_yolo_labels(label_file, current_widget)
            elif label_file.endswith(('.json', '.xml', '.yaml', '.yml')):
                # 其他格式标签处理
                mask = self._create_mask_from_other_labels(label_file, current_widget)
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Warning",
                    "Unsupported label format."
                )
                return

            if mask is not None:
                # 创建掩码元组并赋值
                current_widget.mask_calcu = get_img_color(~mask, 3 + self.plotter.offset), mask, label_file
                self.statusbar.showMessage(f"✅ Mask loaded from label file: {os.path.basename(label_file)}", 3000)

                # 更新显示
                if hasattr(current_widget, 'img'):
                    current_widget.load_image()
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Warning",
                    "Failed to create mask from label file."
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Error loading label file:\n{str(e)}"
            )

    def _create_mask_from_yolo_labels(self, label_file, current_widget):
        """从YOLO格式标签创建掩码"""
        # 获取图像尺寸
        img_height, img_width = current_widget.img[1].shape[:2] if hasattr(current_widget,
                                                                           'img') and current_widget.img else (480, 640)

        mask = np.zeros((img_height, img_width), dtype=np.uint8)

        try:
            with open(label_file, 'r') as f:
                lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:  # 至少有类别ID和4个坐标点
                    # 解析YOLO格式的边界框
                    cls_id = int(parts[0])
                    x_center = float(parts[1]) * img_width
                    y_center = float(parts[2]) * img_height
                    width = float(parts[3]) * img_width
                    height = float(parts[4]) * img_height

                    # 计算边界框坐标
                    x1 = int(x_center - width / 2)
                    y1 = int(y_center - height / 2)
                    x2 = int(x_center + width / 2)
                    y2 = int(y_center + height / 2)

                    # 在掩码上绘制边界框区域
                    mask[y1:y2, x1:x2] = 255

            return mask
        except Exception as e:
            print(f"Error processing YOLO labels: {e}")
            return None

    def _create_mask_from_other_labels(self, label_file, current_widget):
        """从其他格式标签创建掩码（预留方法）"""
        # 根据需要实现其他标签格式的处理
        # 例如JSON格式的COCO标签、Pascal VOC的XML标签等
        QtWidgets.QMessageBox.information(
            self,
            "Info",
            "Other label formats are not implemented yet. Only YOLO .txt format is supported."
        )
        return None

    def _process_mask_file(self, mask_file, current_widget):
        """处理掩码文件加载"""
        try:
            mask = cv2.imread(mask_file, cv2.IMREAD_GRAYSCALE)
            if mask is not None:
                # 将掩码赋值给当前widget
                current_widget.mask_calcu = get_img_color(~mask, 3 + self.plotter.offset), mask, mask_file

                # 更新显示
                if hasattr(current_widget, 'img'):
                    current_widget.load_image()

                self.statusbar.showMessage(f"✅ Mask loaded: {os.path.basename(mask_file)}", 3000)
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Warning",
                    "Failed to load mask file. Please check the file format."
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Error loading mask file:\n{str(e)}"
            )

    def load_model(self):
        # Check if ultralytics is installed
        try:
            import ultralytics
            from ultralytics import YOLO
        except ImportError:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Dependency",
                "Using YOLO detection requires installing the ultralytics library.\nPlease run: pip install ultralytics"
            )
            # Reset state
            return False

        yolo_params = self.yolo_dock.get_parameters()
        # Check if model is already loaded, if not load it
        if not self.yolo_model or not self.yolo_model_name or \
                self.yolo_model_name != yolo_params["model"]:
            try:
                # Try to load model
                model_path = f"{yolo_params['model']}.pt"  # Use pretrained model by default
                # self.yolo_model = YOLO(model_path, task=yolo_params["task"])
                self.yolo_model = YOLO(model_path)
                self.yolo_model_name = yolo_params["model"]
                # Get class names
                if hasattr(self.yolo_model, 'names'):
                    names = self.yolo_model.names
                else:
                    names = {i: f"class_{i}" for i in range(1000)}  # Default class names
                if hasattr(self.yolo_model, 'task'):
                    self.yolo_dock.task_combo.setCurrentText(self.yolo_model.task)
                    yolo_params["task"] = self.yolo_model.task
                self.yolo_dock.update_content(names)
                self.plotter = YOLOPlotter(yolo_params["task"], names)
                self.statusbar.showMessage(f"✅ Loaded YOLO model: {model_path}", 3000)
            except Exception as e:
                self.statusbar.showMessage(f"❌ Model loading failed: {str(e)}", 5000)
                return False
        return True

    def toggle_yolo_detection(self):
        """Toggle YOLO detection display state"""
        """Toggle YOLO detection display state"""
        if not self.yolo_model or not self.yolo_model_name:
            ret = self.load_model()
            if ret:
                if hasattr(self.yolo_model, 'task'):
                    self.yolo_dock.task_combo.setCurrentText(self.yolo_model.task)
                self.statusbar.showMessage(f"Load YOLO Model (Task: {self.yolo_model.task})", 3000)
            else:
                self.action_yolo_detect.setChecked(False)
        current_widget = self.tab_widget.currentWidget()
        current_widget.load_yolo_results = self.action_yolo_detect.isChecked()
        if self.action_yolo_detect.isChecked():
            # If YOLO detection is enabled, ensure YOLO dock is visible
            self.yolo_dock.setVisible(True)
            self.image_view_page_source.append(6)
        else:
            if 6 in self.image_view_page_source:
                self.image_view_page_source.remove(6)
            # self.check_state()
            self.yolo_dock.setVisible(False)
        self.check_state()
        self.files_dock.reload_current_image()
        self.statusbar.showMessage("YOLO Detection: " + ("ON" if self.action_yolo_detect.isChecked() else "OFF"), 3000)

    def toggle_yolo_point_detection(self):
        """Toggle point detection state"""
        if not self.yolo_model or not self.yolo_model_name:
            ret = self.load_model()
            if ret:
                if hasattr(self.yolo_model, 'task'):
                    self.yolo_dock.task_combo.setCurrentText(self.yolo_model.task)
                self.statusbar.showMessage(f"Load YOLO Model (Task: {self.yolo_model.task})", 3000)
            else:
                self.action_yolo_point_detect.setChecked(False)

        current_widget = self.tab_widget.currentWidget()
        current_widget.show_yolo_point_results = self.action_yolo_point_detect.isChecked()

        if self.action_yolo_point_detect.isChecked():
            # Enable point detection mode
            self.yolo_dock.setVisible(True)
            self.image_view_page_source.append(6)
            current_widget.enable_point_detection_mode()
            # if self.images_view_page is not None:
            self.statusbar.showMessage("Point Detection Mode: ON - Click image for local detection", 2000)
        else:
            self.yolo_dock.setVisible(False)
            if 6 in self.image_view_page_source:
                self.image_view_page_source.remove(6)
            # Disable point detection mode
            current_widget.disable_point_detection_mode()
            self.statusbar.showMessage("Point Detection Mode: OFF", 2000)
        self.check_state()


    def on_yolo_model_changed(self, message):
        """When YOLO model changes"""
        if message[0] == "model":
            ret = self.load_model()
            if ret:
                if hasattr(self.yolo_model, 'task'):
                    self.yolo_dock.task_combo.setCurrentText(self.yolo_model.task)
                self.statusbar.showMessage(f"Load YOLO Model (Task: {self.yolo_model.task})", 3000)
            else:
                return
        if message[0] == "task":
            # Get class names
            yolo_params = self.yolo_dock.get_parameters()
            if not self.yolo_model or not self.yolo_model_name or \
                self.yolo_model_name != yolo_params["model"]:
                ret = self.load_model()
                if not ret:
                    return
            if hasattr(self.yolo_model, 'names'):
                names = self.yolo_model.names
            else:
                names = {i: f"class_{i}" for i in range(1000)}  # Default class names
            self.yolo_dock.update_content(names)
            self.plotter = YOLOPlotter(message[1], names)
            self.statusbar.showMessage(f"YOLO Task changed to: {message[1]}", 2000)
        # Here you can add model loading logic

    def on_yolo_conf_threshold_changed(self, conf_threshold):
        """When confidence threshold changes"""
        self.statusbar.showMessage(f"YOLO Confidence Threshold: {conf_threshold}", 2000)
        # Here you can add re-detection logic

    def on_yolo_iou_threshold_changed(self, iou_threshold):
        """When IOU threshold changes"""
        self.statusbar.showMessage(f"YOLO IOU Threshold: {iou_threshold}", 2000)
        # Here you can add re-detection logic

    def show_pulse_control_dialog(self):
        if not hasattr(self, "pulse_control_dialog"):
            self.pulse_control_dialog = PulseControlDialog(self)
        self.pulse_control_dialog.show()

    def show_label(self):
        if self.yolo_model and hasattr(self.yolo_model, 'names'):
            names = self.yolo_model.names
            task = self.yolo_model.task
        else:
            names = {i: f"class_{i}" for i in range(1000)}  # Default class names
            task = 'segment'
        self.plotter = YOLOPlotter(task, names)
        current_widget = self.tab_widget.currentWidget()
        current_widget.show_label = self.action_show_label.isChecked()
        current_widget.label_cache.clear()
        # self.annos_dock.show_filtered = False
        # self.annos_dock.update_label_button_icon()
        self.files_dock.reload_current_image()

    def show_yolo(self):
        if self.yolo_model and hasattr(self.yolo_model, 'names'):
            names = self.yolo_model.names
            task = self.yolo_model.task
        else:
            names = {i: f"class_{i}" for i in range(1000)}  # Default class names
            task = 'segment'
        self.plotter = YOLOPlotter(task, names)
        current_widget = self.tab_widget.currentWidget()
        current_widget.show_results = self.action_show_yolo.isChecked()
        # self.annos_dock.show_filtered = True
        # self.annos_dock.update_label_button_icon()
        self.files_dock.reload_current_image()

    def show_detect_results(self):
        current_widget = self.tab_widget.currentWidget()
        current_widget.show_detect_results = self.action_show_calibration.isChecked()
        # self.image_view_page.update_image_with_detect_results()
        if self.detector is None:
            self.detector = CalibrationDetector()
        self.files_dock.reload_current_image()

    def realtime_detect(self):
        self.camera_page.realtime_detect = self.action_realtime_detect.isChecked()
        self.statusbar.showMessage("⚠️ Real-time detection will take effect next time...", 3000)

    def load_label_files_from_directory(self):
        current_widget = self.tab_widget.currentWidget()

        if not current_widget.pixmap_item:
            self.statusbar.showMessage("⚠️ Please load an image first", 3000)
            return

        # Open folder selection dialog
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Label Folder")
        if not folder_path:
            return

        # Get current image filename (for matching labels)
        current_image_path = current_widget.label_file_path  # Or get path from pixmap_item
        base_name = os.path.splitext(os.path.basename(current_image_path))[0]

        # Find matching label files
        label_extensions = ('.txt', '.json', '.xml')
        matched_labels = []

        for file in os.listdir(folder_path):
            full_path = os.path.join(folder_path, file)
            filename = os.path.splitext(file)[0]
            if os.path.isfile(full_path) and file.lower().endswith(label_extensions) and filename == base_name:
                matched_labels.append(full_path)

        if len(matched_labels) == 0:
            self.statusbar.showMessage("❌ No matching label files found", 3000)
            return

        # Load first matching label file (or multiple based on requirements)
        for label_file in matched_labels:
            current_widget.load_label_file(label_file)
            self.statusbar.showMessage(f"✅ Loaded label file: {label_file}", 3000)

    def load_corner_detection(self):
        # Get calibration parameters
        if self.action_corner_detector.isChecked():
            dialog = CalibrationSettingsDialog(self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                settings = dialog.get_settings()
                self.statusbar.showMessage("Calibration Settings: " + str(settings), 3000)
                # Optional: save these settings for later use
                self.calibration_settings = settings
                self.inner_corners = self.calibration_settings['inner_corners']
                self.pattern_type = self.calibration_settings['pattern_type']
                # self.square_size = self.calibration_settings['square_size']
            # if not hasattr(self, 'calibration_settings'):
            #     QtWidgets.QMessageBox.warning(self, "Warning", "Please set calibration parameters first.")
            #     return
            if hasattr(self, 'inner_corners') and hasattr(self, 'pattern_type'):
                self.detector = CalibrationDetector(self.inner_corners, self.pattern_type)
                self.statusbar.showMessage("Corner Detection: ON", 2000)
        else:
            self.detector = None
            self.statusbar.showMessage("Corner Detection: OFF", 2000)

    def change_theme(self, theme):
        if theme == "Light":
            style = """
                * {
                    font-family: "Times New Roman";
                    font-size: 12pt;
                }
                QWidget {
                    background-color: white;
                    color: black;
                }
                QMenuBar, QToolBar {
                    background-color: #f0f0f0;
                    font-size: 12pt;
                }
                QPushButton {
                    background-color: #dcdcdc;
                    border: 1px solid #bbb;
                    padding: 5px;
                    font-size: 12pt;
                }
                QLabel {
                    color: black;
                    font-size: 12pt;
                }
                QDockWidget, QTabBar::tab {
                    background-color: #f0f0f0;
                    font-size: 12pt;
                }
                QListWidget, QTreeWidget, QTextEdit {
                    background-color: white;
                    color: black;
                    alternate-background-color: #f9f9f9;
                }
                QProgressBar {
                    border: 1px solid #bbb;
                    background-color: #e0e0e0;
                }
                QProgressBar::chunk {
                    background-color: #00c700;
                }
                QLineEdit {
                    background-color: white;
                    color: black;
                    border: 1px solid #bbb;
                }
            """
        elif theme == "Dark":
            style = """
                * {
                    font-family: "Times New Roman";
                    font-size: 12pt;
                }
                QWidget {
                    background-color: #2b2b2b;
                    color: #e0e0e0;
                }
                QMenuBar, QToolBar {
                    background-color: #3c3c3c;
                    font-size: 12pt;
                }
                QPushButton {
                    background-color: #4a4a4a;
                    border: 1px solid #555;
                    padding: 5px;
                    font-size: 12pt;
                }
                QLabel {
                    color: #e0e0e0;
                    font-size: 12pt;
                }
                QDockWidget, QTabBar::tab {
                    background-color: #3c3c3c;
                    font-size: 12pt;
                }
                QListWidget, QTreeWidget, QTextEdit {
                background-color: #363636;
                    color: #e0e0e0;
                    alternate-background-color: #404040;
                    border: 1px solid #555;
                }
                QListWidget::item:selected {
                    background-color: #3d6b99;
                }
                QListWidget::item {
                    background-color: #404040;
                }
                QTreeWidget::item:selected {
                    background-color: #3d6b99;
                }
                QProgressBar {
                    border: 1px solid #555;
                    background-color: #404040;
                }
                QProgressBar::chunk {
                    background-color: #55aa55;
                }
                QLineEdit {
                    background-color: #363636;
                    color: #e0e0e0;
                    border: 1px solid #555;
                }
                QHeaderView::section {
                    background-color: #3c3c3c;
                    color: #e0e0e0;
                    border: 1px solid #555;
                }
                QTabWidget::pane {
                    border: 1px solid #555;
                }
                QTabBar::tab {
                    background-color: #3c3c3c;
                    color: #e0e0e0;
                    border: 1px solid #555;
                }
                QTabBar::tab:selected {
                    background-color: #4a4a4a;
                }
            """
        else:
            style = ""

        self.setStyleSheet(style)

    def change_language(self, theme):
        print("Language changed to:", theme)

    def change_left_camera(self, camera_index):
        """
        Switch left camera index
        """
        if self.camera_page:
            self.camera_page.camera_index = camera_index

    def change_right_camera(self, camera_index2):
        """
        Switch left camera index
        """
        if self.camera_page:
            self.camera_page.camera_index2 = camera_index2

    def toggle_image_view(self):
        if self.action_toggle_images_view.isChecked() and self.action_toggle_image_view.isChecked():  # Switch
            self.action_toggle_images_view.setChecked(False)
            self._show_image_view()
            self._hide_images_view()
        elif self.action_toggle_image_view.isChecked():  # On
            # If no image page or page has been deleted, recreate and add
            self._show_image_view()

        elif self.action_toggle_images_view.isChecked():  # None
            # If no image page or page has been deleted, recreate and add
            self._show_image_view()
            self._hide_images_view()
        else:  # All off
            # Hide image page
            self._hide_image_view()
            self._hide_images_view()
        self.check_state()

    def toggle_images_view(self):
        if self.action_toggle_image_view.isChecked() and self.action_toggle_images_view.isChecked():  # Switch
            self.action_toggle_image_view.setChecked(False)
            self._show_images_view()
            self._hide_image_view()
        elif self.action_toggle_image_view.isChecked():  # None
            # If no image page or page has been deleted, recreate and add
            self._show_images_view()
            self._hide_images_view()
        elif self.action_toggle_images_view.isChecked():  # On
            # If no image page or page has been deleted, recreate and add
            self._show_images_view()
        else:  # Off
            # Hide image page
            self._hide_image_view()
            self._hide_images_view()
        self.check_state()

    def reload_img_view(self):
        current_widget = self.tab_widget.currentWidget()
        file_path = current_widget.img[0]
        if file_path in current_widget.yolo_cache:
            del current_widget.yolo_cache[file_path]
        current_widget.load_file(file_path)

    def _show_image_view(self):
        index = self.tab_widget.indexOf(self.image_view_page)
        if index == -1 or sip.isdeleted(self.image_view_page):
            self.image_view_page = ImageViewer(self)  # Recreate image page
            self.tab_widget.addTab(self.image_view_page, "Image")  # Add back to TabWidget
        index = self.tab_widget.indexOf(self.image_view_page)
        if index != -1:
            self.tab_widget.setTabVisible(index, True)
        if isinstance(self.image_view_page, ImagesViewer):
            self.image_view_page = ImageViewer(self)  # Recreate image page
            self.tab_widget.removeTab(index)
            self.tab_widget.addTab(self.image_view_page, "Image")  # Add back to TabWidget
        # Set as current page
        self.tab_widget.setCurrentWidget(self.image_view_page)
        self.image_view_page.show_label = self.action_show_label.isChecked()
        self.image_view_page.show_results = self.action_show_yolo.isChecked()
        if self.image_view_page.show_label:
            self.show_label()
        self.image_view_page.show_yolo_point_results = self.action_yolo_point_detect.isChecked()
        self.image_view_page.load_yolo_results = self.action_yolo_detect.isChecked()
        self.yolo_dock.patch_size_changed.connect(self.image_view_page.update_patch_rect)  # Add this line

    def _show_images_view(self):
        index = self.tab_widget.indexOf(self.images_view_page)
        if index == -1 or sip.isdeleted(self.images_view_page):
            self.images_view_page = ImagesViewer(self)  # Recreate image page
            self.tab_widget.addTab(self.images_view_page, "Images")  # Add back to TabWidget
        index = self.tab_widget.indexOf(self.images_view_page)
        if index != -1:
            self.tab_widget.setTabVisible(index, True)
        if isinstance(self.images_view_page, ImageViewer):
            self.images_view_page = ImagesViewer(self)  # Recreate image page
            self.tab_widget.removeTab(index)
            self.tab_widget.addTab(self.images_view_page, "Images")  # Add back to TabWidget
        # Set as current page
        self.tab_widget.setCurrentWidget(self.images_view_page)
        self.images_view_page.show_toolbar()
        if self.files_dock.file_paths:
            self.images_view_page.load_images(self.files_dock.file_paths)
        self.images_view_page.show_label = self.action_show_label.isChecked()
        self.images_view_page.show_results = self.action_show_yolo.isChecked()
        if self.images_view_page.show_label:
            self.show_label()
        self.images_view_page.load_yolo_results = self.action_yolo_detect.isChecked()
        self.images_view_page.show_yolo_point_results = self.action_yolo_point_detect.isChecked()
        self.yolo_dock.patch_size_changed.connect(self.images_view_page.update_patch_rect)  # Add this line

    def _hide_image_view(self):
        index = self.tab_widget.indexOf(self.image_view_page)
        if index != -1:
            self.tab_widget.removeTab(index)

    def _hide_images_view(self):
        index = self.tab_widget.indexOf(self.images_view_page)
        if index != -1:
            self.images_view_page.hide_toolbar()
            self.tab_widget.removeTab(index)

    def toggle_camera_view(self):
        """Toggle camera interface display state"""
        if self.action_toggle_camera_view.isChecked() and not self.action_toggle_stereo_view.isChecked():
            self.mode = 'mono'
            # Open camera page
            index = self.tab_widget.indexOf(self.camera_page)
            if index == -1 or sip.isdeleted(self.camera_page):
                self.tab_widget.addTab(self.camera_page, "Realtime")
            index = self.tab_widget.indexOf(self.camera_page)
            if index != -1:
                self.tab_widget.setCurrentWidget(self.camera_page)
                if not isinstance(self.camera_page.camera_index, int) or not isinstance(self.camera_page.camera_index2,
                                                                                        int):
                    self.camera_page.init_camera()

        elif not self.action_toggle_stereo_view.isChecked():
            # Close camera page
            index = self.tab_widget.indexOf(self.camera_page)
            if index != -1:
                self.tab_widget.removeTab(index)
                # self.tab_widget.setTabVisible(index, False)
                self.camera_page.stop_camera()  # Optional: stop camera resources
        else:
            self.mode = 'stereo'
        self.check_state()

    def toggle_stereo_view(self):
        """Toggle camera interface display state"""
        if self.action_toggle_stereo_view.isChecked():
            self.mode = 'stereo'
            # Open camera page
            index = self.tab_widget.indexOf(self.camera_page)
            if index == -1 or sip.isdeleted(self.camera_page):
                self.tab_widget.addTab(self.camera_page, "Realtime")
            index = self.tab_widget.indexOf(self.camera_page)
            if index != -1:
                self.tab_widget.setCurrentWidget(self.camera_page)
                if not isinstance(self.camera_page.camera_index, int) or not isinstance(self.camera_page.camera_index2,
                                                                                        int):
                    self.camera_page.init_camera()

        elif not self.action_toggle_camera_view.isChecked():
            # Close camera page
            index = self.tab_widget.indexOf(self.camera_page)
            if index != -1:
                self.tab_widget.removeTab(index)
                # self.tab_widget.setTabVisible(index, False)
                self.camera_page.stop_camera()  # Optional: stop camera resources
        else:
            self.mode = 'mono'
        self.check_state()

    def toggle_fullscreen(self):
        """
        Toggle fullscreen mode
        """
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def toggle_fit_window(self):
        """
        Toggle fixed image size mode
        """
        self.is_fixed_size = not self.is_fixed_size
        if self.is_fixed_size:
            self.statusbar.showMessage("Fixed size mode enabled.", 2000)
            # self.action_fit_window.setIcon(QtGui.QIcon("icon/full_width_active.svg"))
        else:
            self.statusbar.showMessage("Fixed size mode disabled.", 2000)

    def retranslate_ui(self):
        """
        Set UI text translations
        """
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("MainWindow", "Quantv3.0"))

    def show_about_dialog(self):
        """
        Show about dialog
        """
        QtWidgets.QMessageBox.about(
            self,
            "About Quant",
            """<h1>Quant</h1>
            <p>Version 2.0.0</p>
            <p>Copyright © 2025. All rights reserved.</p>
            <hr>
            <p><b>Email:</b> 1349978767@qq.com</p>
            """
        )

    def closeEvent(self, event):
        """
        Override close event
        """
        self.project_manager.save_project()
        if self.is_modified:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Confirm Close",
                "The document has been modified. Do you want to save your changes?",
                QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Save
            )

            if reply == QtWidgets.QMessageBox.Save:
                self.save_file()
                event.accept()
            elif reply == QtWidgets.QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def load_image(self):
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Open Image Files", "",
                                                               "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_paths:
            self.files_dock.update_file_list(file_paths, add=True)
            current_widget = self.tab_widget.currentWidget()
            if isinstance(current_widget, ImagesViewer):
                current_widget.load_images(file_paths)
            self.statusbar.showMessage(f"Loaded {len(file_paths)} file(s)", 2000)

    def load_file(self, file_path):
        self.statusbar.showMessage(f"Loaded file: {file_path}", 2000)
        current_widget = self.tab_widget.currentWidget()
        image_info = current_widget.load_file(file_path)
        self.info_dock.set_info(image_info)

    def get_memory_usage(self):
        """
        Get memory usage and show in status bar
        """
        current_widget = self.tab_widget.currentWidget()

        # Get memory usage for each cache
        occup1 = get_dict_memory_usage(current_widget.yolo_results)
        occup2 = get_dict_memory_usage(current_widget.image_cache)
        occup3 = get_dict_memory_usage(current_widget.label_cache)
        occup4 = get_dict_memory_usage(current_widget.yolo_cache)

        # Calc total memory usage
        total_memory = occup1 + occup2 + occup3 + occup4

        # Auto select unit for display
        def format_memory_size(size_bytes):
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 ** 2:
                return f"{size_bytes / 1024:.2f} KB"
            elif size_bytes < 1024 ** 3:
                return f"{size_bytes / (1024 ** 2):.2f} MB"
            else:
                return f"{size_bytes / (1024 ** 3):.2f} GB"

        # Format each part memory usage
        yolo_results_size = format_memory_size(occup1)
        image_cache_size = format_memory_size(occup2)
        label_cache_size = format_memory_size(occup3)
        yolo_cache_size = format_memory_size(occup4)
        total_size = format_memory_size(total_memory)

        # Build display info
        memory_info = (f"Memory Usage - "
                       f"YOLO Results: {yolo_results_size}, "
                       f"Image Cache: {image_cache_size}, "
                       f"Label Cache: {label_cache_size}, "
                       f"YOLO Cache: {yolo_cache_size}, "
                       f"Total: {total_size}")

        # Show memory info in status bar
        self.statusbar.showMessage(memory_info, 5000)  # 显示5秒

        # Also print details to console
        print(f"Memory Usage Details:")
        print(f"  YOLO Results: {yolo_results_size} ({occup1} bytes)")
        print(f"  Image Cache: {image_cache_size} ({occup2} bytes)")
        print(f"  Label Cache: {label_cache_size} ({occup3} bytes)")
        print(f"  YOLO Cache: {yolo_cache_size} ({occup4} bytes)")
        print(f"  Total: {total_size} ({total_memory} bytes)")

    def load_folder(self):
        """
        Load folder and display image files in it
        """
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Open Folder", "")

        if folder_path:
            # Get image files in folder
            image_files = []
            for file in os.listdir(folder_path):
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    image_files.append(os.path.join(folder_path, file))

            # If no image files found, show warning
            if not image_files:
                QtWidgets.QMessageBox.warning(self, "Load Folder", "No image files found in the selected folder.")
                return

            # Update file list (optional)

            # Perform different operations based on current image viewer type
            current_widget = self.tab_widget.currentWidget()
            if isinstance(current_widget, ImagesViewer):
                # If ImagesViewer, load all images
                current_widget.load_images(image_files)
                self.files_dock.update_file_list(image_files, show=True)
            else:
                # current_widget.load_images(image_files)
                self.files_dock.update_file_list(image_files, show=True)

            # Optional: update status bar information
            self.statusbar.showMessage(f"Loaded {len(image_files)} images from folder.", 2000)

    def load_save_dir(self):
        pro_dir = self.project_manager.current_project_dir
        if not pro_dir:
            pro_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Open Folder", "")
        if os.path.exists(os.path.join(pro_dir, "config.ini")):
            self.project_manager.current_project_dir = pro_dir
            self.project_manager.load_config()
            self.statusbar.showMessage(f"Open project: {pro_dir}", 3000)
        else:
            QtWidgets.QMessageBox.warning(self, "Load Folder", "No config.ini found in the selected folder.")
            return
        folder_path = str(os.path.join(self.project_manager.current_project_dir, self.project_manager.save_dir))
        if folder_path:
            # Get image files in folder
            image_files = []
            image_files2 = []
            video_files = []
            video_files2 = []
            for file in os.listdir(folder_path):
                if file.lower().endswith((".png", ".jpg", ".bmp")):
                    if not file.endswith("_r.png") and not file.endswith("_r.jpg") and not file.endswith("_r.bmp"):
                        image_files2.append(os.path.join(folder_path, file))
                    image_files.append(os.path.join(folder_path, file))
                elif file.lower().endswith((".mp4", ".avi")):
                    if not file.endswith("_r.avi") and not file.endswith("_r.mp4"):
                        video_files2.append(os.path.join(folder_path, file))
                    video_files.append(os.path.join(folder_path, file))

            # If no image files found, show warning
            if not image_files:
                QtWidgets.QMessageBox.warning(self, "Load Folder", "No image files found in the project folder.")
                return

            # Update file list (optional)
            self.files_dock.update_file_list(image_files)
            self.project_manager.i_img = len(image_files2)
            self.project_manager.i_vid = len(video_files2)
            # Optional: update status bar information
            self.statusbar.showMessage(f"Loaded {len(image_files)} images from project folder.", 2000)

    def save_file(self):
        """
        Save file
        """
        if self.current_file:
            # Implement save logic
            self.is_modified = False
            self.statusbar.showMessage("File saved successfully.", 2000)
        else:
            self.save_file_as()

    def save_file_as(self):
        """
        Save as file
        """
        pass

    def set_icon_opacity(self, pixmap, opacity):
        """
        Set QPixmap opacity
        """
        image = pixmap.toImage()
        painter = QtGui.QPainter(image)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_DestinationIn)
        painter.fillRect(image.rect(), QtGui.QColor(0, 0, 0, int(opacity * 255)))
        painter.end()
        return QtGui.QPixmap.fromImage(image)

    def change_mask_opacity(self, opacity):
        current_widget = self.tab_widget.currentWidget()
        current_widget.mask_opacity = opacity
        if isinstance(current_widget, (ImageViewer, ImagesViewer)) and current_widget.img:
            current_widget.load_file(current_widget.img[0])
        self.statusbar.showMessage(f"Mask Opacity: {int(opacity * 100)}%", 2000)

    def show_settings_dialog(self):
        if not self.settings_dialog:
            self.settings_dialog = SettingsDialog(self)
            # if self.camera_page.camera_available is None:
            #     self.camera_page.init_camera()
            self.settings_dialog.set_available_cameras(self.camera_page.camera_available)
            # Ensure signals and slots are correctly connected
            self.settings_dialog.theme_changed.connect(self.change_theme)
            self.settings_dialog.language_changed.connect(self.change_language)
            self.settings_dialog.left_camera_changed.connect(self.change_left_camera)
            self.settings_dialog.right_camera_changed.connect(self.change_right_camera)
            self.settings_dialog.mask_opacity_changed.connect(self.change_mask_opacity)

        self.settings_dialog.show()

    def keyPressEvent(self, event):
        """
        Handle global keyboard shortcuts
        """
        # Get current active widget
        current_widget = self.tab_widget.currentWidget()

        # Check if image viewing related page
        if isinstance(current_widget, (ImageViewer, ImagesViewer)):
            # Handle 'a' key - previous image
            if event.key() == QtCore.Qt.Key_A and not event.modifiers():
                self.files_dock.prev_image(event)
                event.accept()
                return
            # Handle 'd' key - next image
            elif event.key() == QtCore.Qt.Key_D and not event.modifiers():
                self.files_dock.next_image(event)
                event.accept()
                return
            # Handle 'w' key - first image
            elif event.key() == QtCore.Qt.Key_W and not event.modifiers():
                self.files_dock.to_first_image(event)
                event.accept()
                return
            # Handle 's' key - last image
            elif event.key() == QtCore.Qt.Key_S and not event.modifiers():
                self.files_dock.to_last_image(event)
                event.accept()
                return

            # Handle 'm' key - memory
            elif event.key() == QtCore.Qt.Key_M and event.modifiers():
                self.get_memory_usage()
                event.accept()
                return
            # Handle 'c' key - color offset
            elif event.key() == QtCore.Qt.Key_C and event.modifiers():
                if hasattr(self, 'plotter'):
                    self.plotter.offset += 1
                    self.statusbar.showMessage(f"Color Offset: {self.plotter.offset}", 2000)
                event.accept()
                return
            # Handle 'c' key with modifiers
            elif event.key() == QtCore.Qt.Key_C and event.modifiers() (Qt.ControlModifier | Qt.ShiftModifier):
                if hasattr(self, 'plotter'):
                    self.plotter.offset -= 1
                    self.statusbar.showMessage(f"Color Offset: {self.plotter.offset}", 2000)
                event.accept()
                return

            elif event.key() == Qt.Key_R and event.modifiers() == Qt.ControlModifier:
                # Ctrl + 0 reset view
                current_widget.reset_view()
            elif event.key() == Qt.Key_R and event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
                # Ctrl + Shift + R reset results
                current_widget.reset_results()
            else:
                super().keyPressEvent(event)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
