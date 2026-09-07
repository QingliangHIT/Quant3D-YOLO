"""阈值分割算子：对当前图像或整批图像按灰度阈值二值化并生成掩码。"""

import os
import cv2
from PyQt5 import QtWidgets, QtCore


def apply_threshold_to_current_image(dock, threshold_value):
    """
    Apply threshold segmentation to currently displayed image
    """
    # Get current ImagesViewer instance
    images_viewer = dock.parent.tab_widget.currentWidget()
    if not hasattr(images_viewer, 'img') or images_viewer.img is None:
        return

    try:
        # Get current image
        file_path, img = images_viewer.img

        # Convert to grayscale image (if needed)
        if len(img.shape) == 3:
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray_img = img

        # Apply threshold segmentation
        if dock.binary_checkbox.isChecked():
            # Apply threshold segmentation
            _, binary_img = cv2.threshold(gray_img, threshold_value, 255, cv2.THRESH_BINARY)
        else:
            gray_img[gray_img < threshold_value] = 0
            binary_img = gray_img
        # Convert binary image to 3-channel to maintain consistency
        if len(img.shape) == 3:
            result_img = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2BGR)
        else:
            result_img = binary_img

        # Update display
        images_viewer.update_image(result_img)

    except Exception as e:
        dock.parent.statusbar.showMessage(f"Threshold segmentation processing error: {str(e)}", 5000)


def apply_threshold_operation(dock):
    """
    Apply threshold segmentation operation
    """
    # Get threshold
    threshold_value = dock.threshold_slider.value()

    # Get current ImagesViewer instance
    images_viewer = dock.parent.tab_widget.currentWidget()
    if not hasattr(images_viewer, 'image_cache'):
        QtWidgets.QMessageBox.warning(dock, "Warning", "Current view does not support this operation")
        return

    # 检查 image_cache 是否为空，如果为空则根据处理范围临时加载
    if hasattr(images_viewer, 'image_cache'):
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

    # Determine files to process
    if dock.all_process_checkbox.isChecked():
        # Process all images
        files_to_process = list(images_viewer.image_cache.items())
    else:
        # Process only current image
        current_item = dock.parent.files_dock.list_widget.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.warning(dock, "Warning", "No image selected")
            return
        file_path = current_item.data(QtCore.Qt.UserRole)
        if file_path not in images_viewer.image_cache:
            QtWidgets.QMessageBox.warning(dock, "Warning", "Current image not loaded")
            return
        files_to_process = [(file_path, images_viewer.image_cache[file_path])]

    # Show progress dialog
    progress_dialog = QtWidgets.QProgressDialog("Performing threshold segmentation...", "Cancel", 0,
                                                len(files_to_process),
                                                dock.parent)
    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setWindowTitle("Threshold Segmentation")
    progress_dialog.show()

    # Process threshold segmentation on images
    processed_count = 0
    for i, (file_path, img) in enumerate(files_to_process):
        # Update progress
        progress_dialog.setValue(i)
        progress_dialog.setLabelText(f"Processing: {os.path.basename(file_path)}")

        # Process events to update UI
        QtWidgets.QApplication.processEvents()

        # Check if user canceled operation
        if progress_dialog.wasCanceled():
            break

        try:
            # Convert to grayscale image (if needed)
            if len(img.shape) == 3:
                gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray_img = img
            if dock.binary_checkbox.isChecked():
                # Apply threshold segmentation
                _, binary_img = cv2.threshold(gray_img, threshold_value, 255, cv2.THRESH_BINARY)
            else:
                binary_img = gray_img.copy()
                binary_img[binary_img < threshold_value] = 0
            # Convert binary image to 3-channel to maintain consistency
            if len(img.shape) == 3:
                result_img = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2BGR)
            else:
                result_img = binary_img

            # Update image in cache
            images_viewer.image_cache[file_path] = result_img
            processed_count += 1

        except Exception as e:
            dock.parent.statusbar.showMessage(f"Error processing image {os.path.basename(file_path)}: {str(e)}",
                                              5000)
            continue

    # Complete processing
    progress_dialog.setValue(len(files_to_process))
    progress_dialog.close()

    if processed_count > 0:
        dock.parent.statusbar.showMessage(f"Completed threshold segmentation for {processed_count} images", 3000)
    else:
        dock.parent.statusbar.showMessage("No images were processed", 3000)

    # Update currently displayed image if it was processed
    current_item = dock.parent.files_dock.list_widget.currentItem()
    if current_item:
        file_path = current_item.data(QtCore.Qt.UserRole)
        if file_path in images_viewer.image_cache:
            images_viewer.load_file(file_path)
