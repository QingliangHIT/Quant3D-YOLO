"""视图切换状态机：单图 / 批量 / 相机三种页面的显示与隐藏协调。"""

from PyQt5 import QtCore, sip
from quant.ui.views.image_view import ImageViewer
from quant.ui.views.batch_image_view import ImagesViewer


def check_state(window):
    if isinstance(window.tab_widget.currentWidget(), (ImageViewer, ImagesViewer)):
        window.current_state = 1
        window.addDockWidget(QtCore.Qt.DockWidgetArea(1), window.files_dock)
        window.addDockWidget(QtCore.Qt.DockWidgetArea(2), window.info_dock)
        window.addDockWidget(QtCore.Qt.DockWidgetArea(2), window.annos_dock)
        window.addDockWidget(QtCore.Qt.DockWidgetArea(2), window.categories_dock)
        window.addDockWidget(QtCore.Qt.DockWidgetArea(1), window.yolo_dock)
        window.addDockWidget(QtCore.Qt.DockWidgetArea(1), window.control3D_dock)
        window.control3D_dock.hide()

        for dock in window.dock_dict:
            if dock in [window.dock_dict[i] for i in window.image_view_page_source]:
                dock.setVisible(True)
            else:
                dock.setVisible(False)
    elif window.tab_widget.currentWidget() == window.camera_page:
        window.current_state = 2
        window.addDockWidget(QtCore.Qt.DockWidgetArea(1), window.camera_files_dock)
        window.addDockWidget(QtCore.Qt.DockWidgetArea(2), window.info_dock)
        window.addDockWidget(QtCore.Qt.DockWidgetArea(2), window.camera_control_dock)
        for dock in window.dock_dict:
            if dock in [window.dock_dict[i] for i in window.camera_page_source]:
                dock.setVisible(True)
            else:
                dock.setVisible(False)
    else:
        window.current_state = 0
        for dock in window.dock_dict:
            window.removeDockWidget(dock)
        for dock in window.dock_dict:
            dock.setVisible(False)


def toggle_image_view(window):
    if window.action_toggle_images_view.isChecked() and window.action_toggle_image_view.isChecked():  # Switch
        window.action_toggle_images_view.setChecked(False)
        window._show_image_view()
        window._hide_images_view()
    elif window.action_toggle_image_view.isChecked():  # On
        # If no image page or page has been deleted, recreate and add
        window._show_image_view()

    elif window.action_toggle_images_view.isChecked():  # None
        # If no image page or page has been deleted, recreate and add
        window._show_image_view()
        window._hide_images_view()
    else:  # All off
        # Hide image page
        window._hide_image_view()
        window._hide_images_view()
    window.check_state()


def toggle_images_view(window):
    if window.action_toggle_image_view.isChecked() and window.action_toggle_images_view.isChecked():  # Switch
        window.action_toggle_image_view.setChecked(False)
        window._show_images_view()
        window._hide_image_view()
    elif window.action_toggle_image_view.isChecked():  # None
        # If no image page or page has been deleted, recreate and add
        window._show_images_view()
        window._hide_images_view()
    elif window.action_toggle_images_view.isChecked():  # On
        # If no image page or page has been deleted, recreate and add
        window._show_images_view()
    else:  # Off
        # Hide image page
        window._hide_image_view()
        window._hide_images_view()
    window.check_state()


def show_image_view(window):
    index = window.tab_widget.indexOf(window.image_view_page)
    if index == -1 or sip.isdeleted(window.image_view_page):
        window.image_view_page = ImageViewer(window)  # Recreate image page
        window.tab_widget.addTab(window.image_view_page, "Image")  # Add back to TabWidget
    index = window.tab_widget.indexOf(window.image_view_page)
    if index != -1:
        window.tab_widget.setTabVisible(index, True)
    if isinstance(window.image_view_page, ImagesViewer):
        window.image_view_page = ImageViewer(window)  # Recreate image page
        window.tab_widget.removeTab(index)
        window.tab_widget.addTab(window.image_view_page, "Image")  # Add back to TabWidget
    # Set as current page
    window.tab_widget.setCurrentWidget(window.image_view_page)
    window.image_view_page.show_label = window.action_show_label.isChecked()
    window.image_view_page.show_results = window.action_show_yolo.isChecked()
    if window.image_view_page.show_label:
        window.show_label()
    window.image_view_page.show_yolo_point_results = window.action_yolo_point_detect.isChecked()
    window.image_view_page.load_yolo_results = window.action_yolo_detect.isChecked()
    window.yolo_dock.patch_size_changed.connect(window.image_view_page.update_patch_rect)  # Add this line


def show_images_view(window):
    index = window.tab_widget.indexOf(window.images_view_page)
    if index == -1 or sip.isdeleted(window.images_view_page):
        window.images_view_page = ImagesViewer(window)  # Recreate image page
        window.tab_widget.addTab(window.images_view_page, "Images")  # Add back to TabWidget
    index = window.tab_widget.indexOf(window.images_view_page)
    if index != -1:
        window.tab_widget.setTabVisible(index, True)
    if isinstance(window.images_view_page, ImageViewer):
        window.images_view_page = ImagesViewer(window)  # Recreate image page
        window.tab_widget.removeTab(index)
        window.tab_widget.addTab(window.images_view_page, "Images")  # Add back to TabWidget
    # Set as current page
    window.tab_widget.setCurrentWidget(window.images_view_page)
    window.images_view_page.show_toolbar()
    if window.files_dock.file_paths:
        window.images_view_page.load_images(window.files_dock.file_paths)
    window.images_view_page.show_label = window.action_show_label.isChecked()
    window.images_view_page.show_results = window.action_show_yolo.isChecked()
    if window.images_view_page.show_label:
        window.show_label()
    window.images_view_page.load_yolo_results = window.action_yolo_detect.isChecked()
    window.images_view_page.show_yolo_point_results = window.action_yolo_point_detect.isChecked()
    window.yolo_dock.patch_size_changed.connect(window.images_view_page.update_patch_rect)  # Add this line


def hide_image_view(window):
    index = window.tab_widget.indexOf(window.image_view_page)
    if index != -1:
        window.tab_widget.removeTab(index)


def hide_images_view(window):
    index = window.tab_widget.indexOf(window.images_view_page)
    if index != -1:
        window.images_view_page.hide_toolbar()
        window.tab_widget.removeTab(index)


def toggle_camera_view(window):
    """Toggle camera interface display state"""
    if window.action_toggle_camera_view.isChecked():
        window.mode = 'mono'
        # Open camera page
        index = window.tab_widget.indexOf(window.camera_page)
        if index == -1 or sip.isdeleted(window.camera_page):
            window.tab_widget.addTab(window.camera_page, "Realtime")
        index = window.tab_widget.indexOf(window.camera_page)
        if index != -1:
            window.tab_widget.setCurrentWidget(window.camera_page)
            if not isinstance(window.camera_page.camera_index, int):
                window.camera_page.init_camera()
    else:
        # Close camera page
        index = window.tab_widget.indexOf(window.camera_page)
        if index != -1:
            window.tab_widget.removeTab(index)
            window.camera_page.stop_camera()  # Optional: stop camera resources
    window.check_state()
