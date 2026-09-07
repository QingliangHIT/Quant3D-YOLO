"""孔洞算子：基于分割掩码的填孔（膨胀）与留孔处理。"""

import os
import cv2
import numpy as np
from PyQt5 import QtWidgets, QtCore
from copy import deepcopy


def apply_hole_operation(dock):
    """
    Apply dilation to the selected category region (adapted to results_label format)
    """
    selected_classes = dock.parent.yolo_dock.get_selected_classes() if dock.parent.annos_dock.show_filtered else None

    if isinstance(selected_classes, (list, tuple)) and len(selected_classes) < 1:
        QtWidgets.QMessageBox.warning(dock, "Warning", "Please select the category to process first")
        return

    # Get the current ImagesViewer instance
    images_viewer = dock.parent.tab_widget.currentWidget()
    if not hasattr(images_viewer, 'image_cache') or not hasattr(images_viewer, 'yolo_results'):
        QtWidgets.QMessageBox.warning(dock, "Warning", "The current view does not support this operation.")
        return

    # 检查 image_cache 是否为空，如果为空则根据处理范围临时加载
    if not images_viewer.image_cache:
        if dock.all_process_checkbox.isChecked():
            # 处理所有图像：加载文件管理器中的所有图像
            total_files = dock.parent.files_dock.list_widget.count()
            if total_files == 0:
                QtWidgets.QMessageBox.warning(dock, "Warning",
                                              "No files available to load. Please add images first.")
                return
            if len(images_viewer.image_cache) == 0:
                reply = QtWidgets.QMessageBox.question(
                    dock,
                    "Load Images",
                    f"No cached images found. Load {total_files} images temporarily?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                )

                if reply == QtWidgets.QMessageBox.Yes:
                    progress_dialog = QtWidgets.QProgressDialog("Loading images...", "Cancel", 0, total_files,
                                                                dock.parent)
                    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
                    progress_dialog.setWindowTitle("Loading Images")
                    progress_dialog.show()

                    for i in range(total_files):
                        progress_dialog.setValue(i)
                        progress_dialog.setLabelText(f"Loading: {i + 1}/{total_files}")

                        QtWidgets.QApplication.processEvents()

                        if progress_dialog.wasCanceled():
                            progress_dialog.close()
                            return

                        item = dock.parent.files_dock.list_widget.item(i)
                        file_path = item.data(QtCore.Qt.UserRole)

                        if file_path not in images_viewer.image_cache:
                            try:
                                img = cv2.imread(file_path)
                                if img is not None:
                                    images_viewer.image_cache[file_path] = img
                            except Exception as e:
                                print(f"Failed to load {file_path}: {str(e)}")
                                continue

                    progress_dialog.setValue(total_files)
                    progress_dialog.close()

                    if not images_viewer.image_cache:
                        QtWidgets.QMessageBox.warning(dock, "Warning", "Failed to load any images from file list.")
                        return
                else:
                    return
        else:
            # 处理单个图像：只加载当前选中的图像
            current_item = dock.parent.files_dock.list_widget.currentItem()
            if not current_item:
                QtWidgets.QMessageBox.warning(dock, "Warning", "No image selected")
                return

            file_path = current_item.data(QtCore.Qt.UserRole)
            if file_path not in images_viewer.image_cache:
                try:
                    img = cv2.imread(file_path)
                    if img is not None:
                        images_viewer.image_cache[file_path] = img
                    else:
                        QtWidgets.QMessageBox.warning(dock, "Warning", f"Failed to load image: {file_path}")
                        return
                except Exception as e:
                    QtWidgets.QMessageBox.warning(dock, "Warning", f"Error loading image: {str(e)}")
                    return

    # Confirm the file to process.
    if dock.all_process_checkbox.isChecked():
        # Process all images
        files_to_process = list(images_viewer.image_cache.items())
    else:
        # Process only the current image
        current_item = dock.parent.files_dock.list_widget.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.warning(dock, "Warning", "No image selected")
            return
        file_path = current_item.data(QtCore.Qt.UserRole)
        if file_path not in images_viewer.image_cache:
            QtWidgets.QMessageBox.warning(dock, "Warning", "The current image is not loaded")
            return
        files_to_process = [(file_path, images_viewer.image_cache[file_path])]

    # Show progress dialog
    progress_dialog = QtWidgets.QProgressDialog("Performing dilation...", "cancel", 0, len(files_to_process),
                                                dock.parent)
    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setWindowTitle("Dilation operation")
    progress_dialog.show()

    # Process image
    processed_count = 0
    for i, (file_path, img) in enumerate(files_to_process):
        # Update progress
        progress_dialog.setValue(i)
        progress_dialog.setLabelText(f"Processing: {os.path.basename(file_path)}")

        # Process events to update UI
        QtWidgets.QApplication.processEvents()

        # Check if the user canceled the operation
        if progress_dialog.wasCanceled():
            break

        if file_path in images_viewer.yolo_results:
            results_label = deepcopy(images_viewer.yolo_results[file_path])
            results_label = dock.parent.plotter.filter_results_label(results_label, selected_classes)
            # Check for mask data
            if "masks" in results_label and results_label["masks"]:
                # Get mask data
                masks_data = results_label["masks"]

                # Create dilation mask
                hole_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)

                # Process each selected category
                for mask_info in masks_data:
                    if len(mask_info) > 0:
                        points = mask_info[1:]
                        if len(points) >= 6 and len(points) % 2 == 0:  # At least 3 points

                            # Create polygon point array
                            pts = np.array([[points[i], points[i + 1]] for i in range(0, len(points), 2)],
                                           np.int32)

                            # Draw polygon on mask
                            cv2.fillPoly(hole_mask, [pts], 1)

                # Apply dilation (set selected area to black)
                if np.any(hole_mask):
                    img[hole_mask > 0] = [0, 0, 0]  # Set selected area to black
                    images_viewer.image_cache[file_path] = img
                    processed_count += 1

    # Processing complete
    progress_dialog.setValue(len(files_to_process))

    dock.parent.statusbar.showMessage(f"Dilation completed for {processed_count} images", 3000)
    # Update the currently displayed image
    current_item = dock.parent.files_dock.list_widget.currentItem()
    if current_item:
        file_path = current_item.data(QtCore.Qt.UserRole)
        images_viewer.load_file(file_path)


def apply_holeshow_operation(dock):
    """
    Show mask of selected class, set background to black (for results_label)
    """
    selected_classes = dock.parent.yolo_dock.get_selected_classes() if dock.parent.annos_dock.show_filtered else None

    if isinstance(selected_classes, (list, tuple)) and len(selected_classes) < 1:
        QtWidgets.QMessageBox.warning(dock, "Warning", "Please select a class to process")
        return

    # Get current ImagesViewer instance
    images_viewer = dock.parent.tab_widget.currentWidget()
    if not hasattr(images_viewer, 'image_cache') or not hasattr(images_viewer, 'yolo_results'):
        QtWidgets.QMessageBox.warning(dock, "Warning", "Operation not supported in current view")
        return

    # 检查 image_cache 是否为空，如果为空则根据处理范围临时加载
    if not images_viewer.image_cache:
        if dock.all_process_checkbox.isChecked():
            # 处理所有图像：加载文件管理器中的所有图像
            total_files = dock.parent.files_dock.list_widget.count()
            if total_files == 0:
                QtWidgets.QMessageBox.warning(dock, "Warning",
                                              "No files available to load. Please add images first.")
                return
            if len(images_viewer.image_cache) == 0:
                reply = QtWidgets.QMessageBox.question(
                    dock,
                    "Load Images",
                    f"No cached images found. Load {total_files} images temporarily?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                )

                if reply == QtWidgets.QMessageBox.Yes:
                    progress_dialog = QtWidgets.QProgressDialog("Loading images...", "Cancel", 0, total_files,
                                                                dock.parent)
                    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
                    progress_dialog.setWindowTitle("Loading Images")
                    progress_dialog.show()

                    for i in range(total_files):
                        progress_dialog.setValue(i)
                        progress_dialog.setLabelText(f"Loading: {i + 1}/{total_files}")

                        QtWidgets.QApplication.processEvents()

                        if progress_dialog.wasCanceled():
                            progress_dialog.close()
                            return

                        item = dock.parent.files_dock.list_widget.item(i)
                        file_path = item.data(QtCore.Qt.UserRole)

                        if file_path not in images_viewer.image_cache:
                            try:
                                img = cv2.imread(file_path)
                                if img is not None:
                                    images_viewer.image_cache[file_path] = img
                            except Exception as e:
                                print(f"Failed to load {file_path}: {str(e)}")
                                continue

                    progress_dialog.setValue(total_files)
                    progress_dialog.close()

                    if not images_viewer.image_cache:
                        QtWidgets.QMessageBox.warning(dock, "Warning", "Failed to load any images from file list.")
                        return
                else:
                    return
        else:
            # 处理单个图像：只加载当前选中的图像
            current_item = dock.parent.files_dock.list_widget.currentItem()
            if not current_item:
                QtWidgets.QMessageBox.warning(dock, "Warning", "No image selected")
                return

            file_path = current_item.data(QtCore.Qt.UserRole)
            if file_path not in images_viewer.image_cache:
                try:
                    img = cv2.imread(file_path)
                    if img is not None:
                        images_viewer.image_cache[file_path] = img
                    else:
                        QtWidgets.QMessageBox.warning(dock, "Warning", f"Failed to load image: {file_path}")
                        return
                except Exception as e:
                    QtWidgets.QMessageBox.warning(dock, "Warning", f"Error loading image: {str(e)}")
                    return

    # Confirm files to process
    if dock.all_process_checkbox.isChecked():
        # Process all images
        files_to_process = list(images_viewer.image_cache.items())
    else:
        # Process current image only
        current_item = dock.parent.files_dock.list_widget.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.warning(dock, "Warning", "No image selected")
            return
        file_path = current_item.data(QtCore.Qt.UserRole)
        if file_path not in images_viewer.image_cache:
            QtWidgets.QMessageBox.warning(dock, "Warning", "Image not loaded")
            return
        files_to_process = [(file_path, images_viewer.image_cache[file_path])]

    # Show progress dialog
    progress_dialog = QtWidgets.QProgressDialog("Showing mask...", "Cancel", 0, len(files_to_process),
                                                dock.parent)
    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setWindowTitle("Show Mask")
    progress_dialog.show()

    # Process image
    processed_count = 0
    for i, (file_path, img) in enumerate(files_to_process):
        # Update progress
        progress_dialog.setValue(i)
        progress_dialog.setLabelText(f"Processing: {os.path.basename(file_path)}")

        # Update UI
        QtWidgets.QApplication.processEvents()

        #  Check for cancel
        if progress_dialog.wasCanceled():
            break

        if file_path in images_viewer.yolo_results:
            results_label = deepcopy(images_viewer.yolo_results[file_path])
            results_label = dock.parent.plotter.filter_results_label(results_label, selected_classes)

            # Check for mask data
            if "masks" in results_label and results_label["masks"]:
                # Get mask data
                masks_data = results_label["masks"]

                # Create mask for keep operation
                show_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)

                for mask_info in masks_data:
                    if len(mask_info) > 0:
                        points = mask_info[1:]
                        if len(points) >= 6 and len(points) % 2 == 0:  # At least 3 points
                            # Create polygon points
                            pts = np.array([[points[i], points[i + 1]] for i in range(0, len(points), 2)],
                                           np.int32)

                            # Draw polygon on mask
                            cv2.fillPoly(show_mask, [pts], 1)

                # Apply keep operation (set non-selected to white)
                if np.any(show_mask):
                    # Generate image containing only mask
                    # Set mask to white, background black
                    mask_img = np.zeros_like(img)
                    mask_img[show_mask > 0] = [128, 128, 128]  # White mask
                    images_viewer.image_cache[file_path] = mask_img
                    processed_count += 1

    # Done
    progress_dialog.setValue(len(files_to_process))

    dock.parent.statusbar.showMessage(f"Dilation completed for {processed_count} images", 3000)

    # Update the currently displayed image
    current_item = dock.parent.files_dock.list_widget.currentItem()
    if current_item:
        file_path = current_item.data(QtCore.Qt.UserRole)
        images_viewer.load_file(file_path)
