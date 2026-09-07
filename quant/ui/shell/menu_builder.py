"""菜单与动作构建：集中创建主窗口的全部 QAction / QMenu。"""

from PyQt5 import QtGui, QtWidgets
from quant.core.paths import icon_path


def build_menu_items(window):
    """
    Set up menu items
    """
    # File menu
    window.action_open = QtWidgets.QAction(window)
    window.action_open.setIcon(QtGui.QIcon(icon_path("OpenFiles.ico")))
    window.action_open.setText("Open")
    window.action_open.setShortcut("Ctrl+O")

    # Add open folder action
    window.action_open_folder = QtWidgets.QAction(window)
    window.action_open_folder.setIcon(QtGui.QIcon(icon_path("OpenFolder.ico")))
    window.action_open_folder.setText("Open Folder")
    window.action_open_folder.setShortcut("Ctrl+Shift+O")

    window.action_exit = QtWidgets.QAction(window)
    window.action_exit.setIcon(QtGui.QIcon(icon_path("Exit.ico")))
    window.action_exit.setText("Exit")
    window.action_exit.setShortcut("Ctrl+Q")

    window.action_open_project = QtWidgets.QAction(window)
    window.action_open_project.setIcon(QtGui.QIcon(icon_path("SaveFile.ico")))  # Icon can be customized
    window.action_open_project.setText("Open")

    window.action_new_project = QtWidgets.QAction(window)
    window.action_new_project.setIcon(QtGui.QIcon(icon_path("SaveFile.ico")))  # Optional icon
    window.action_new_project.setText("New")
    window.action_new_project.setShortcut("Ctrl+N")

    window.action_current_project = QtWidgets.QAction(window)
    window.action_current_project.setIcon(QtGui.QIcon(icon_path("SaveFile.ico")))  # Prepare an icon
    window.action_current_project.setText("Current")

    window.action_save_project = QtWidgets.QAction(window)
    window.action_save_project.setIcon(QtGui.QIcon(icon_path("SaveFile.ico")))  # Optional icon
    window.action_save_project.setText("Save")
    window.action_save_project.setShortcut("Ctrl+Shift+S")

    window.action_load_project = QtWidgets.QAction(window)
    window.action_load_project.setIcon(QtGui.QIcon(icon_path("SaveFile.ico")))  # Optional icon
    window.action_load_project.setText("Load")
    window.action_load_project.setShortcut("Ctrl+Shift+L")

    window.action_load_label_paths = QtWidgets.QAction(window)
    window.action_load_label_paths.setIcon(QtGui.QIcon(icon_path("Label.ico")))  # Optional icon
    window.action_load_label_paths.setText("Load Label Paths")

    window.menu_file.addAction(window.action_open_project)
    window.menu_file.addAction(window.action_new_project)
    window.menu_file.addAction(window.action_save_project)
    window.menu_file.addAction(window.action_current_project)
    window.menu_file.addAction(window.action_load_project)
    window.menu_file.addSeparator()
    window.menu_file.addAction(window.action_open)
    window.menu_file.addAction(window.action_open_folder)
    window.menu_file.addSeparator()
    window.menu_file.addAction(window.action_load_label_paths)
    window.menu_file.addSeparator()
    window.menu_file.addAction(window.action_exit)

    # Edit menu
    window.action_undo = QtWidgets.QAction(window)
    window.action_undo.setIcon(QtGui.QIcon(icon_path("Last.ico")))
    window.action_undo.setText("Undo")
    window.action_undo.setShortcut("Ctrl+Z")

    window.action_redo = QtWidgets.QAction(window)
    window.action_redo.setIcon(QtGui.QIcon(icon_path("Next.ico")))
    window.action_redo.setText("Redo")
    window.action_redo.setShortcut("Ctrl+Y")

    window.action_zoom_in = QtWidgets.QAction(window)
    window.action_zoom_in.setIcon(QtGui.QIcon(icon_path("ZoomIn.ico")))
    window.action_zoom_in.setText("Zoom In")
    window.action_zoom_in.setShortcut("Ctrl+=")

    window.action_zoom_out = QtWidgets.QAction(window)
    window.action_zoom_out.setIcon(QtGui.QIcon(icon_path("ZoomOut.ico")))
    window.action_zoom_out.setText("Zoom Out")
    window.action_zoom_out.setShortcut("Ctrl+-")

    # Add new adaptive window action
    window.action_fit_window = QtWidgets.QAction("Fit Window", window)
    window.action_fit_window.setCheckable(True)
    window.action_fit_window.setChecked(True)
    window.action_fit_window.setIcon(QtGui.QIcon(icon_path("FitWindow.ico")))
    window.action_fit_window.setShortcut("Ctrl+F")

    window.menu_edit.addAction(window.action_undo)
    window.menu_edit.addAction(window.action_redo)
    window.menu_edit.addAction(window.action_zoom_in)
    window.menu_edit.addAction(window.action_zoom_out)
    window.menu_edit.addAction(window.action_fit_window)

    # View menu
    # Add hide/show image view and camera interface menu items
    window.action_toggle_image_view = QtWidgets.QAction("Image View", window)
    window.action_toggle_image_view.setIcon(QtGui.QIcon(icon_path("View.ico")))
    window.action_toggle_image_view.setCheckable(True)
    window.action_toggle_image_view.setChecked(True)

    window.action_toggle_images_view = QtWidgets.QAction("Images View", window)
    window.action_toggle_images_view.setIcon(QtGui.QIcon(icon_path("ViewPool.ico")))
    window.action_toggle_images_view.setCheckable(True)
    window.action_toggle_images_view.setChecked(False)

    window.action_toggle_camera_view = QtWidgets.QAction("Camera View", window)
    window.action_toggle_camera_view.setIcon(QtGui.QIcon(icon_path("Camera.ico")))
    window.action_toggle_camera_view.setCheckable(True)
    window.action_toggle_camera_view.setChecked(False)

    window.menu_view.addAction(window.action_toggle_image_view)
    window.menu_view.addAction(window.action_toggle_images_view)
    window.menu_view.addAction(window.action_toggle_camera_view)

    window.action_show_label = QtWidgets.QAction("Show Label")
    window.action_show_label.setIcon(QtGui.QIcon(icon_path("Label.ico")))
    window.action_show_label.setCheckable(True)

    window.action_show_yolo = QtWidgets.QAction("Show YOLO Results")
    window.action_show_yolo.setIcon(QtGui.QIcon(icon_path("LabelYOLO.ico")))
    window.action_show_yolo.setCheckable(True)

    window.action_show_calibration = QtWidgets.QAction(window)
    window.action_show_calibration.setIcon(QtGui.QIcon(icon_path("Calibration.ico")))
    window.action_show_calibration.setText("Show Calibration")
    window.action_show_calibration.setCheckable(True)
    window.menu_tools.addAction(window.action_show_label)
    window.menu_tools.addAction(window.action_show_yolo)
    window.menu_tools.addAction(window.action_show_calibration)
    window.menu_tools.addSeparator()
    # YOLO detection action
    window.action_yolo_detect = QtWidgets.QAction(window)
    window.action_yolo_detect.setIcon(QtGui.QIcon(icon_path("Detection.ico")))  # Can be replaced with a more suitable icon
    window.action_yolo_detect.setText("YOLO Detect")
    window.action_yolo_detect.setCheckable(True)
    window.menu_tools.addAction(window.action_yolo_detect)
    # Add point detection action
    window.action_yolo_point_detect = QtWidgets.QAction(window)
    window.action_yolo_point_detect.setIcon(QtGui.QIcon(icon_path("DetectionPoint.ico")))  # Can be replaced with a more suitable icon
    window.action_yolo_point_detect.setText("YOLO Point Detect")
    window.action_yolo_point_detect.setCheckable(True)
    window.menu_tools.addAction(window.action_yolo_point_detect)

    window.menu_calibration = QtWidgets.QMenu("Camera Calibration", window.menu_tools)
    window.menu_tools.addMenu(window.menu_calibration)
    window.menu_calibration.setIcon(QtGui.QIcon(icon_path("Calibration.ico")))
    window.menu_tools.addAction(window.menu_calibration.menuAction())

    window.action_mask_calcu = QtWidgets.QAction(window)
    window.action_mask_calcu.setIcon(QtGui.QIcon(icon_path("Label.ico")))  # 需要准备图标
    window.action_mask_calcu.setText("Mask for Calculation")
    window.menu_tools.addAction(window.action_mask_calcu)

    # Tools menu
    window.action_settings = QtWidgets.QAction(window)
    window.action_settings.setIcon(QtGui.QIcon(icon_path("Settings.ico")))
    window.action_settings.setText("Settings")
    window.menu_tools.addAction(window.action_settings)

    # Add fullscreen mode menu item
    window.action_fullscreen = QtWidgets.QAction(window)
    window.action_fullscreen.setIcon(QtGui.QIcon(icon_path("full.ico")))
    window.action_fullscreen.setText("Fullscreen")
    window.action_fullscreen.setCheckable(True)
    window.menu_view.addAction(window.action_fullscreen)

    # Calibration menu
    # Add calibration submenu items
    window.action_start_calibration = QtWidgets.QAction(window)
    window.action_start_calibration.setText("Start Calibration")

    window.action_realtime_detect = QtWidgets.QAction(window)
    window.action_realtime_detect.setText("Realtime detect")
    window.action_realtime_detect.setCheckable(True)

    window.action_corner_detector = QtWidgets.QAction(window)
    window.action_corner_detector.setText("Load Corner Detector")
    window.action_corner_detector.setCheckable(True)

    window.menu_calibration.addAction(window.action_realtime_detect)
    window.menu_calibration.addSeparator()
    window.menu_calibration.addAction(window.action_start_calibration)
    window.menu_calibration.addAction(window.action_corner_detector)
    # Help menu
    window.action_about = QtWidgets.QAction(window)
    window.action_about.setIcon(QtGui.QIcon(icon_path("About.ico")))
    window.action_about.setText("About")

    window.menu_help.addAction(window.action_about)
