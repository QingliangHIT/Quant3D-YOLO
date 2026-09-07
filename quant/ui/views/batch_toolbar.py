"""批量视图工具栏：检测/三维/保存动作构建、保存路径与保存格式开关。"""

import os
from PyQt5 import QtWidgets, QtCore, QtGui
from quant.core.config import IconSize
from quant.core.paths import icon_path


def build_toolbar(view):
    # Setup toolbar for image operations
    if hasattr(view, 'images_viewer_toolbar') and view.images_viewer_toolbar:
        return

    # Create toolbar
    view.images_viewer_toolbar = QtWidgets.QToolBar("Images Viewer Tools", view.parent)
    view.images_viewer_toolbar.setFont(QtGui.QFont("Times New Roman", 12))
    view.images_viewer_toolbar.setIconSize(QtCore.QSize(IconSize, IconSize))
    view.images_viewer_toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
    view.images_viewer_toolbar.setObjectName("imagesViewerToolBar")

    # Add to main window
    view.parent.addToolBar(QtCore.Qt.TopToolBarArea, view.images_viewer_toolbar)
    view.images_viewer_toolbar.hide()

    # Create actions
    view.action_batch_detect = QtWidgets.QAction(view.parent)
    view.action_batch_detect.setIcon(QtGui.QIcon(icon_path("DetectionBatch.ico")))
    view.action_batch_detect.setText("Batch Detect")
    view.action_batch_detect.setToolTip("Detect all images with one click")

    view.action_3d_view = QtWidgets.QAction(view.parent)
    view.action_3d_view.setIcon(QtGui.QIcon(icon_path("Tools3D.ico")))
    view.action_3d_view.setText("3D View")
    view.action_3d_view.setCheckable(True)
    view.action_3d_view.setToolTip("Show 3D view")

    view.action_reset_view = QtWidgets.QAction(view.parent)
    view.action_reset_view.setIcon(QtGui.QIcon(icon_path("Reset.ico")))
    view.action_reset_view.setText("Reset View")
    view.action_reset_view.setToolTip("Reset")

    view.action_save_view = QtWidgets.QAction(view.parent)
    view.action_save_view.setIcon(QtGui.QIcon(icon_path("SaveIMG.ico")))
    view.action_save_view.setText("Save View")
    view.action_save_view.setToolTip("Save current view")

    # Create save menu
    view.save_menu = QtWidgets.QMenu(view.parent)

    view.action_save_image = QtWidgets.QAction("Save as Image", view.parent)
    view.action_save_image.setCheckable(True)
    view.action_save_txt = QtWidgets.QAction("Save as TXT", view.parent)
    view.action_save_txt.setCheckable(True)
    view.action_save_json = QtWidgets.QAction("Save as JSON", view.parent)
    view.action_save_json.setCheckable(True)
    view.action_save_mask = QtWidgets.QAction("Save Mask", view.parent)
    view.action_save_mask.setCheckable(True)

    view.action_save_image.setChecked(True)

    view.action_auto_save = QtWidgets.QAction("Auto Save", view.parent)
    view.action_auto_save.setCheckable(True)
    view.action_save_all = QtWidgets.QAction("Save All", view.parent)

    # Add actions to menu
    view.save_menu.addAction(view.action_save_txt)
    view.save_menu.addAction(view.action_save_json)
    view.save_menu.addAction(view.action_save_mask)
    view.save_menu.addAction(view.action_save_image)
    view.save_menu.addAction(view.action_auto_save)
    view.save_menu.addSeparator()
    view.save_menu.addAction(view.action_save_all)

    # Add set save path action
    view.action_set_save_path = QtWidgets.QAction("Set Save Path", view.parent)
    view.save_menu.addSeparator()
    view.save_menu.addAction(view.action_set_save_path)

    # Connect menu to action
    view.action_save_view.setMenu(view.save_menu)

    # Add actions to toolbar
    view.images_viewer_toolbar.addAction(view.action_batch_detect)
    view.images_viewer_toolbar.addAction(view.action_reset_view)
    view.images_viewer_toolbar.addAction(view.action_save_view)
    view.images_viewer_toolbar.addSeparator()
    view.images_viewer_toolbar.addAction(view.action_3d_view)

    # Connect signals
    view.action_batch_detect.triggered.connect(lambda checked: view.process_all_images(checked, False))
    view.action_3d_view.triggered.connect(view.toggle_3d_view)
    view.action_reset_view.triggered.connect(view.reset_cache)
    view.action_set_save_path.triggered.connect(view._set_save_path)
    view.action_save_view.triggered.connect(view._save_with_current_format)
    view.action_save_image.triggered.connect(lambda checked: view._on_save_format_changed("image", checked))
    view.action_save_txt.triggered.connect(lambda checked: view._on_save_format_changed("txt", checked))
    view.action_save_json.triggered.connect(lambda checked: view._on_save_format_changed("json", checked))
    view.action_save_mask.triggered.connect(lambda checked: view._on_save_format_changed("mask", checked))
    view.action_auto_save.triggered.connect(view._on_auto_save_toggled)
    view.action_save_all.triggered.connect(lambda checked: view.process_all_images(checked, True))

    def set_save_button_popup_mode():
        save_button = view.images_viewer_toolbar.widgetForAction(view.action_save_view)
        if save_button:
            save_button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
            view.save_menu.setToolTipsVisible(True)

    view.images_viewer_toolbar.visibilityChanged.connect(lambda: set_save_button_popup_mode())


def set_save_path(view):
    # Set default save directory
    folder_path = QtWidgets.QFileDialog.getExistingDirectory(
        view.parent,
        "Select Default Save Path",
        view.default_save_path or "./'output'"
    )

    if folder_path:
        view.default_save_path = folder_path
        view.parent.statusbar.showMessage(f"Default save path set to: {folder_path}", 3000)


def get_save_path(view, file_name):
    # Get full save path
    if view.default_save_path:
        return os.path.join(view.default_save_path, file_name)
    else:
        view.default_save_path = "./output"
        return os.path.join(view.default_save_path, file_name)


def on_auto_save_toggled(view, checked):
    # Toggle auto save feature
    if checked:
        view.auto_save = True
        view.parent.statusbar.showMessage("Auto save enabled", 2000)
    else:
        view.auto_save = False
        view.parent.statusbar.showMessage("Auto save disabled", 2000)


def on_save_format_changed(view, format_type, checked):
    # Handle save format change
    if checked:
        if format_type != "image":
            view.action_save_image.setChecked(False)
        if format_type != "txt":
            view.action_save_txt.setChecked(False)
        if format_type != "json":
            view.action_save_json.setChecked(False)
        if format_type != "mask":
            view.action_save_mask.setChecked(False)

        format_names = {"image": "Image", "txt": "TXT", "json": "JSON", "mask": "Mask"}
        view.action_save_view.setToolTip(
            f"Save current results as {format_names.get(format_type, format_type)}")
    return False
