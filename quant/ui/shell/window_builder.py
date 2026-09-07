"""窗口骨架装配：中央控件、菜单栏、工具栏、停靠窗与信号连接。"""

from PyQt5 import QtCore, QtGui, QtWidgets
from quant.ui.docks.files_dock import FilesDock
from quant.ui.docks.info_dock import InfoDock
from quant.ui.docks.annotation_dock import AnnoDock
from quant.ui.docks.category_dock import CategoriesDock
from quant.ui.docks.camera_control_dock import ControlDock
from quant.ui.docks.camera_files_dock import CameraFilesDock
from quant.ui.docks.detector_params_dock import YoloDock
from quant.ui.views.camera_view import CameraWindow
from quant.ui.widgets.tab_widget import CustomTabWidget
from quant.core.config import IconSize
from quant.core.paths import icon_path


def build_ui(window):
    """
    Set up user interface
    """
    # Window basic settings
    window.setObjectName("MainWindow")
    window.resize(1600, 900)
    window.setMinimumSize(QtCore.QSize(800, 600))

    # Set font
    font = QtGui.QFont()
    font.setFamily("Times New Roman")
    font.setPointSize(12)
    window.setFont(font)

    # Set window icon
    icon = QtGui.QIcon()
    icon.addPixmap(QtGui.QPixmap(icon_path("SOFT.ico")),
                   QtGui.QIcon.Normal, QtGui.QIcon.Off)
    window.setWindowIcon(icon)

    # Central widget
    window.centralwidget = QtWidgets.QWidget(window)
    window.centralwidget.setObjectName("centralwidget")
    window.horizontalLayout = QtWidgets.QHBoxLayout(window.centralwidget)
    window.horizontalLayout.setContentsMargins(0, 0, 0, 0)
    window.horizontalLayout.setSpacing(0)
    window.setCentralWidget(window.centralwidget)

    # Create QTabWidget for page switching
    window.tab_widget = CustomTabWidget(window)  # Replace with custom CustomTabWidget
    window.horizontalLayout.addWidget(window.tab_widget)

    # Create camera page
    window.camera_page = CameraWindow(window)
    # Menu bar
    window.setup_menubar()

    # Status bar
    window.statusbar = QtWidgets.QStatusBar(window)
    window.statusbar.setLayoutDirection(QtCore.Qt.LeftToRight)
    window.statusbar.setObjectName("statusbar")
    window.setStatusBar(window.statusbar)

    # Toolbars
    window.setup_toolbar()

    # Dock widgets
    window.setup_docks()

    window.retranslate_ui()
    QtCore.QMetaObject.connectSlotsByName(window)


def build_menubar(window):
    """
    Set up menu bar
    """
    window.menubar = QtWidgets.QMenuBar(window)
    window.menubar.setEnabled(True)
    window.menubar.setGeometry(QtCore.QRect(0, 0, 1600, 25))
    window.menubar.setFont(QtGui.QFont("Times New Roman", 12))
    window.menubar.setObjectName("menubar")

    # Create menus
    window.menu_file = QtWidgets.QMenu(window.menubar)
    window.menu_edit = QtWidgets.QMenu(window.menubar)
    window.menu_view = QtWidgets.QMenu(window.menubar)
    window.menu_tools = QtWidgets.QMenu(window.menubar)
    window.menu_help = QtWidgets.QMenu(window.menubar)

    # Set menu properties
    for menu in [window.menu_file, window.menu_edit, window.menu_view,
                 window.menu_tools, window.menu_help, ]:
        menu.setFont(QtGui.QFont("Times New Roman", 12))

    # Set menu titles
    window.menu_file.setTitle("File")
    window.menu_edit.setTitle("Edit")
    window.menu_view.setTitle("View")
    window.menu_tools.setTitle("Tools")
    window.menu_help.setTitle("Help")
    # window.menu_calibration.setTitle("Calibrator")
    # window.menu_controller.setTitle("Controller")

    # Add menu items
    window.setup_menu_items()

    # Add menus to menu bar
    window.menubar.addAction(window.menu_file.menuAction())
    window.menubar.addAction(window.menu_edit.menuAction())
    window.menubar.addAction(window.menu_view.menuAction())
    window.menubar.addAction(window.menu_tools.menuAction())
    window.menubar.addAction(window.menu_help.menuAction())
    # window.menu_tools.addAction(window.menu_calibration.menuAction())
    # window.menubar.addAction(window.menu_calibration.menuAction())
    # window.menubar.addAction(window.menu_controller.menuAction())


    window.setMenuBar(window.menubar)


def build_toolbar(window):
    """
    Set up toolbars
    """
    # Main toolbar
    window.toolBar = QtWidgets.QToolBar(window)
    window.toolBar.setFont(QtGui.QFont("Times New Roman", 12))
    window.toolBar.setIconSize(QtCore.QSize(IconSize, IconSize))
    window.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
    window.toolBar.setFloatable(True)
    window.toolBar.setObjectName("toolBar")

    # Right toolbar
    window.toolBar_right = QtWidgets.QToolBar(window)
    window.toolBar_right.setMovable(False)
    window.toolBar_right.setFloatable(False)
    window.toolBar_right.setObjectName("toolBar_right")

    # Add toolbars
    window.addToolBar(QtCore.Qt.TopToolBarArea, window.toolBar)
    window.addToolBar(QtCore.Qt.RightToolBarArea, window.toolBar_right)

    # Set toolbar buttons
    window.setup_toolbar_buttons()


def build_docks(window):
    """
    Set up dock widgets
    """
    # Files dock widget
    window.files_dock = FilesDock(window)

    # Info dock widget
    window.info_dock = InfoDock(window)

    # Annotations dock widget
    window.annos_dock = AnnoDock(window)

    # Categories dock widget
    window.categories_dock = CategoriesDock(window)

    # Camera control dock widget
    window.camera_control_dock = ControlDock(window)

    # Camera files dock widget
    window.camera_files_dock = CameraFilesDock(window)

    # YOLO parameters dock widget
    window.yolo_dock = YoloDock(window)

    # Add dock widgets
    window.dock_dict = [window.files_dock, window.info_dock, window.annos_dock, window.categories_dock, window.camera_control_dock, window.camera_files_dock, window.yolo_dock]
    window.image_view_page_source = [0, 1, 2, 3]
    window.camera_page_source = [1, 4, 5]


def build_toolbar_buttons(window):
    """
    Set up toolbar buttons
    """
    # Main toolbar buttons
    window.toolBar.addAction(window.action_open)
    window.toolBar.addAction(window.action_open_folder)
    window.toolBar.addAction(window.action_save_project)
    window.toolBar.addSeparator()
    window.toolBar.addAction(window.action_undo)
    window.toolBar.addAction(window.action_redo)
    window.toolBar.addSeparator()
    window.toolBar.addAction(window.action_fit_window)
    window.toolBar.addAction(window.action_zoom_in)
    window.toolBar.addAction(window.action_zoom_out)
    window.toolBar.addSeparator()
    window.toolBar.addAction(window.action_toggle_image_view)
    window.toolBar.addAction(window.action_toggle_images_view)
    window.toolBar.addAction(window.action_toggle_camera_view)
    window.toolBar.addSeparator()
    window.toolBar.addAction(window.action_show_calibration)
    window.toolBar.addAction(window.action_show_label)
    window.toolBar.addAction(window.action_show_yolo)
    window.toolBar.addSeparator()
    window.toolBar.addAction(window.action_yolo_detect)
    window.toolBar.addAction(window.action_yolo_point_detect)

    # Right toolbar buttons
    window.toolBar_right.addAction(window.action_settings)
    # Right toolbar, add elastic space
    spacer = QtWidgets.QWidget()
    spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
    window.toolBar_right.insertWidget(window.action_settings, spacer)
    window.toolBar_right.addAction(window.action_about)


def connect_signals(window):
    """
    Set up signal and slot connections
    """
    window.action_new_project.triggered.connect(window.project_manager.new_project)
    window.action_open_project.triggered.connect(window.project_manager.open_project)
    window.action_save_project.triggered.connect(window.project_manager.save_project)
    window.action_current_project.triggered.connect(window.project_manager.show_current_project_info)
    window.action_load_project.triggered.connect(window.load_save_dir)
    window.action_exit.triggered.connect(window.close)
    window.action_about.triggered.connect(window.show_about_dialog)
    window.action_open.triggered.connect(window.load_image)
    window.action_open_folder.triggered.connect(window.load_folder)

    window.action_redo.triggered.connect(lambda: window.files_dock.prev_image(None))
    window.action_undo.triggered.connect(lambda: window.files_dock.next_image(None))
    window.action_zoom_in.triggered.connect(window.zoom_in)
    window.action_zoom_out.triggered.connect(window.zoom_out)

    window.action_toggle_image_view.triggered.connect(window.toggle_image_view)
    window.action_toggle_images_view.triggered.connect(window.toggle_images_view)
    window.action_toggle_camera_view.triggered.connect(window.toggle_camera_view)
    window.action_fullscreen.triggered.connect(window.toggle_fullscreen)

    window.action_fit_window.triggered.connect(window.toggle_fit_window)

    window.tab_widget.currentChanged.connect(window.check_state)
    window.action_settings.triggered.connect(window.show_settings_dialog)

    window.action_corner_detector.triggered.connect(window.load_corner_detection)

    window.action_load_label_paths.triggered.connect(window.files_dock.load_all_labels)
    window.action_show_label.triggered.connect(window.show_label)
    window.action_show_yolo.triggered.connect(window.show_yolo)
    window.action_mask_calcu.triggered.connect(window.load_mask_calcu)

    window.action_show_calibration.triggered.connect(window.show_detect_results)
    window.action_realtime_detect.triggered.connect(window.realtime_detect)
    window.action_start_calibration.triggered.connect(window.show_calibrator_dialog)
    window.action_yolo_detect.triggered.connect(window.toggle_yolo_detection)
    window.action_yolo_point_detect.triggered.connect(window.toggle_yolo_point_detection)
    # Connect YOLO parameters dock signals
    window.yolo_dock.yolo_model_changed.connect(window.on_yolo_model_changed)
    window.yolo_dock.yolo_conf_threshold_changed.connect(window.on_yolo_conf_threshold_changed)
    window.yolo_dock.yolo_iou_threshold_changed.connect(window.on_yolo_iou_threshold_changed)
    window.yolo_dock.class_filter_changed.connect(window.reload_img_view)


def retranslate_ui(window):
    """
    Set UI text translations
    """
    _translate = QtCore.QCoreApplication.translate
    window.setWindowTitle(_translate("MainWindow", "Quantv3.0"))
