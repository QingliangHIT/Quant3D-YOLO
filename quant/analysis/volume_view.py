"""三维体素视图：pyvista 窗口构建、刷新与关闭。"""

import os
import pyvista as pv
import matplotlib.colors as mcolors
from PyQt5 import QtWidgets, QtCore
import cv2
import numpy as np


def show_3d(view):
    # Show 3D visualization
    if not view.parent.files_dock.file_paths:
        view.parent.statusbar.showMessage("No images to display", 2000)
        if hasattr(view.parent, 'control3D_dock'):
            view.parent.control3D_dock.action_3d_view.setChecked(False)
        return

    try:
        image_stack = []
        total_files = len(view.parent.files_dock.file_paths)

        progress_dialog = QtWidgets.QProgressDialog("Preparing 3D data...", "Cancel", 0, total_files, view.parent)
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setWindowTitle("3D View Preparation")
        progress_dialog.show()

        for i, file_path in enumerate(view.parent.files_dock.file_paths):
            progress_dialog.setValue(i)
            progress_dialog.setLabelText(f"Loading: {os.path.basename(file_path)}")

            QtWidgets.QApplication.processEvents()

            if progress_dialog.wasCanceled():
                progress_dialog.close()
                view.parent.statusbar.showMessage("3D view display canceled", 2000)
                if hasattr(view.parent, 'control3D_dock'):
                    view.parent.control3D_dock.action_3d_view.setChecked(False)
                return
            else:
                if file_path in view.image_cache:
                    img = view.image_cache[file_path]
                    if len(img.shape) == 3:
                        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    else:
                        gray_img = img
                    image_stack.append(gray_img)
                else:
                    img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        image_stack.append(img)

        progress_dialog.setValue(total_files)
        progress_dialog.close()

        if not image_stack:
            view.parent.statusbar.showMessage("Failed to load image data for 3D display", 3000)
            if hasattr(view.parent, 'control3D_dock'):
                view.parent.control3D_dock.action_3d_view.setChecked(False)
            return
        shapes = {img.shape for img in image_stack}
        if len(shapes) > 1:
            view.parent.statusbar.showMessage("Images have different sizes, cannot stack into a volume", 4000)
            if hasattr(view.parent, 'control3D_dock'):
                view.parent.control3D_dock.action_3d_view.setChecked(False)
            return
        view.parent.statusbar.showMessage(f"3D view displayed ({len(image_stack)} slices)", 3000)

        volume = np.stack(image_stack, axis=0)
        grid = pv.wrap(volume)

        colormap = view.parent.control3D_dock.colormap_combo.currentData()
        view.plotter_3d = pv.Plotter()
        if view.parent.control3D_dock.binary_checkbox.isChecked():
            color_value = view.parent.control3D_dock.color_slider.value()
            hue = color_value / 255.0
            saturation = 1.0
            value = 1.0
            hsv_color = np.array([[hue, saturation, value]])
            rgb_color = mcolors.hsv_to_rgb(hsv_color)[0]
            custom_cmap = mcolors.ListedColormap([rgb_color])
            view.plotter_3d.add_volume(grid, cmap=custom_cmap, opacity="linear")
        else:
            # 下拉框尚未填充时 currentData() 为 None，pyvista 会直接抛错，退回默认色表
            view.plotter_3d.add_volume(grid, cmap=colormap or "viridis", opacity="linear")
        # view.plotter_3d.add_axes()
        # view.plotter_3d.show_grid()
        view.plotter_3d._before_close_callback = view.on_3d_window_close
        view.plotter_3d.show(title="3D Image Stack View", auto_close=True)

    except ImportError as e:
        QtWidgets.QMessageBox.warning(
            view.parent,
            "Missing Dependencies",
            f"The following libraries are required to use 3D view functionality:\npyvista, scikit-image, matplotlib\n\nError: {str(e)}"
        )
        view.parent.statusbar.showMessage("Missing 3D visualization dependencies", 3000)
        if hasattr(view.parent, 'control3D_dock'):
            view.parent.control3D_dock.action_3d_view.setChecked(False)
    except Exception as e:
        QtWidgets.QMessageBox.critical(
            view.parent,
            "3D View Error",
            f"Error occurred while displaying 3D view:\n{str(e)}"
        )
        view.parent.statusbar.showMessage("3D view display failed", 3000)
        if hasattr(view.parent, 'control3D_dock'):
            view.parent.control3D_dock.action_3d_view.setChecked(False)


def refresh_3d_view(view, colormap="viridis"):
    # Refresh 3D view with new colormap
    images_viewer = view.parent.tab_widget.currentWidget()
    if images_viewer is None:
        view.parent.statusbar.showMessage("No active image view", 2000)
        return

    plotter_3d = getattr(images_viewer, "plotter_3d", None)
    if plotter_3d is not None:
        try:
            plotter_3d.close()
        except Exception:  # noqa: BLE001 - 关闭 pyvista 窗口的失败不影响后续重建
            pass
        images_viewer.plotter_3d = None

    if not view.parent.files_dock.file_paths:
        view.parent.statusbar.showMessage("No images to display", 2000)
        return

    try:
        image_stack = []
        for file_path in view.parent.files_dock.file_paths:
            if file_path in images_viewer.image_cache:
                img = images_viewer.image_cache[file_path]
                if len(img.shape) == 3:
                    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                else:
                    gray_img = img
                image_stack.append(gray_img)
            else:
                img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    image_stack.append(img)

        if not image_stack:
            view.parent.statusbar.showMessage("Failed to load image data for 3D display", 3000)
            return
        if len({img.shape for img in image_stack}) > 1:
            view.parent.statusbar.showMessage("Images have different sizes, cannot stack into a volume", 4000)
            return

        volume = np.stack(image_stack, axis=0)
        grid = pv.wrap(volume)

        images_viewer.plotter_3d = pv.Plotter()
        images_viewer.plotter_3d.add_volume(grid, cmap=colormap, opacity="linear")
        # view.plotter_3d.add_axes()
        # view.plotter_3d.show_grid()
        images_viewer.plotter_3d._before_close_callback = images_viewer.on_3d_window_close

        images_viewer.plotter_3d.show(title="3D Image Stack View", auto_close=True)

        view.parent.statusbar.showMessage(f"3D view refreshed with {colormap} colormap", 3000)

    except ImportError as e:
        QtWidgets.QMessageBox.warning(
            view.parent,
            "Missing Dependencies",
            f"The following libraries are required to use 3D view functionality:\npyvista, scikit-image, matplotlib\n\nError: {str(e)}"
        )
        view.parent.statusbar.showMessage("Missing 3D visualization dependencies", 3000)
    except Exception as e:
        QtWidgets.QMessageBox.critical(
            view.parent,
            "3D View Error",
            f"Error occurred while displaying 3D view:\n{str(e)}"
        )
        view.parent.statusbar.showMessage("3D view display failed", 3000)


def hide_3d(view):
    # Hide 3D view
    plotter_3d = getattr(view, "plotter_3d", None)
    if plotter_3d is not None:
        try:
            plotter_3d.close()
        except Exception:  # noqa: BLE001 - pyvista 关闭异常不应阻断界面复位
            pass
        view.plotter_3d = None
        view.parent.statusbar.showMessage("3D view closed", 2000)


def toggle_3d_view(view, checked):
    # Toggle 3D view
    if checked:
        view.parent.control3D_dock.show()
        view.parent.control3D_dock.show_toolbar()
    else:
        view.parent.control3D_dock.hide()
        view.parent.control3D_dock.hide_toolbar()
        view.parent.statusbar.showMessage("3D mode closed", 2000)


def on_3d_window_close(view):
    # Handle 3D window close
    view.plotter_3d = None
    if hasattr(view.parent, 'control3D_dock'):
        view.parent.control3D_dock.action_3d_view.setChecked(False)
    view.parent.statusbar.showMessage("3D view closed", 2000)
