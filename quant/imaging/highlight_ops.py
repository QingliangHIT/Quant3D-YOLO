"""高亮与标记算子：按类别高亮目标区域并叠加标记。"""

import os
import cv2
import numpy as np
from PyQt5 import QtWidgets, QtCore
from copy import deepcopy


def apply_highlight_operation(dock):
    """
    Highlight selected class areas (Adapt to `results_label` format)
    """
    selected_classes = dock.parent.yolo_dock.get_selected_classes() if dock.parent.annos_dock.show_filtered else None

    if isinstance(selected_classes, (list, tuple)) and len(selected_classes) < 1:
        QtWidgets.QMessageBox.warning(dock, "Warning", "Please select the category to process first.")
        return

    # Get the current `ImagesViewer` instance
    images_viewer = dock.parent.tab_widget.currentWidget()
    if not hasattr(images_viewer, 'image_cache') or not hasattr(images_viewer, 'yolo_results'):
        QtWidgets.QMessageBox.warning(dock, "Warning", "The current view does not support this operation")
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

    # Confirm the files to process.
    if dock.all_process_checkbox.isChecked():
        # Process all images.
        files_to_process = list(images_viewer.image_cache.items())
    else:
        # Process only the current image.
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
    progress_dialog = QtWidgets.QProgressDialog("Performing highlight operation...", "Cancel", 0,
                                                len(files_to_process),
                                                dock.parent)
    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setWindowTitle("Highlight operation")
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

                # Create highlight mask
                highlight_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)

                # Process each selected category
                # names = results_label.get("names", {})
                for mask_info in masks_data:
                    if len(mask_info) > 0:
                        points = mask_info[1:]
                        if len(points) >= 6 and len(points) % 2 == 0:  # At least 3 points
                            # Create polygon point array
                            pts = np.array([[points[i], points[i + 1]] for i in range(0, len(points), 2)],
                                           np.int32)

                            # Draw polygon on mask
                            cv2.fillPoly(highlight_mask, [pts], 1)

                # Apply highlight operation (increase brightness and contrast)
                if np.any(highlight_mask):
                    # Create highlight effect
                    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                    hsv[:, :, 1] = np.where(highlight_mask > 0,
                                            np.minimum(hsv[:, :, 1].astype(np.uint16) + 50, 255).astype(
                                                np.uint8),
                                            hsv[:, :, 1])
                    hsv[:, :, 2] = np.where(highlight_mask > 0,
                                            np.minimum(hsv[:, :, 2].astype(np.uint16) + 50, 255).astype(
                                                np.uint8),
                                            hsv[:, :, 2])
                    highlighted_img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

                    # Restore non-highlighted areas to the original image
                    mask_3d = np.stack([highlight_mask, highlight_mask, highlight_mask], axis=2)
                    img = np.where(mask_3d > 0, highlighted_img, img)

                    images_viewer.image_cache[file_path] = img
                    processed_count += 1

    # Processing complete
    progress_dialog.setValue(len(files_to_process))

    dock.parent.statusbar.showMessage(f"Dilation completed for {processed_count} images", 3000)

    # Update displayed image
    current_item = dock.parent.files_dock.list_widget.currentItem()
    if current_item:
        file_path = current_item.data(QtCore.Qt.UserRole)
        images_viewer.load_file(file_path)


def apply_mark_operation(dock):
    """
    Mark selected class on image (for results_label)
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
    progress_dialog = QtWidgets.QProgressDialog("Marking...", "Cancel", 0, len(files_to_process),
                                                dock.parent)
    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setWindowTitle("Mark")
    progress_dialog.show()

    # Process image
    processed_count = 0
    for i, (file_path, img) in enumerate(files_to_process):
        # Update progress
        progress_dialog.setValue(i)
        progress_dialog.setLabelText(f"Processing: {os.path.basename(file_path)}")

        # Update UI
        QtWidgets.QApplication.processEvents()

        # Check for cancel
        if progress_dialog.wasCanceled():
            break

        if file_path in images_viewer.yolo_results:
            results_label = deepcopy(images_viewer.yolo_results[file_path])
            results_label = dock.parent.plotter.filter_results_label(results_label, selected_classes)

            # Process mask marks
            if "masks" in results_label and results_label["masks"]:
                masks_data = results_label["masks"]
                names = results_label.get("names", {})

                # Process each selected class
                for mask_info in masks_data:
                    if len(mask_info) > 0:
                        class_id = int(mask_info[0])
                        class_name = names.get(class_id, f"class_{class_id}")

                        points = mask_info[1:]
                        if len(points) >= 6 and len(points) % 2 == 0:  # At least 3 points
                            # Create polygon points
                            pts = np.array([[points[i], points[i + 1]] for i in range(0, len(points), 2)],
                                           np.int32)

                            # Create mask image
                            mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
                            cv2.fillPoly(mask, [pts], 1)
                            mask = (mask * 255).astype(np.uint8)

                            # Draw mask outline
                            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            cv2.drawContours(img, contours, -1, (0, 255, 0), 2)

                            # Add label near outline
                            if contours:
                                # Get largest contour center
                                largest_contour = max(contours, key=cv2.contourArea)
                                M = cv2.moments(largest_contour)
                                if M["m00"] != 0:
                                    cx = int(M["m10"] / M["m00"])
                                    cy = int(M["m01"] / M["m00"])
                                    cv2.putText(img, class_name, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX,
                                                0.5, (0, 255, 0), 1, cv2.LINE_AA)

            # Process bounding box marks
            elif "boxes" in results_label and results_label["boxes"]:
                boxes_data = results_label["boxes"]
                names = results_label.get("names", {})

                # Process each selected class
                for box_info in boxes_data:
                    if len(box_info) >= 6:  # [x1, y1, x2, y2, conf, class_id]
                        x1, y1, x2, y2 = map(int, box_info[:4])
                        class_id = int(box_info[5])
                        class_name = names.get(class_id, f"class_{class_id}")

                        # Draw bbox if class is selected
                        if class_name in selected_classes:
                            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(img, class_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                        0.5, (0, 255, 0), 1, cv2.LINE_AA)

            images_viewer.image_cache[file_path] = img
            processed_count += 1

    # Done
    progress_dialog.setValue(len(files_to_process))

    dock.parent.statusbar.showMessage(f"Dilation completed for {processed_count} images", 3000)

    # Update displayed image
    current_item = dock.parent.files_dock.list_widget.currentItem()
    if current_item:
        file_path = current_item.data(QtCore.Qt.UserRole)
        images_viewer.load_file(file_path)
