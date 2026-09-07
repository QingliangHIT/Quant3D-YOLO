"""体素信息统计：按阈值/掩码计算 2D 与 3D 目标信息。"""

import os
import cv2
import numpy as np
from PyQt5 import QtWidgets, QtCore


def calculate_2d_info(dock):
    """
    Calculate pore statistics in 2D images
    """
    current_widget = dock.parent.tab_widget.currentWidget()
    file_path, image = current_widget.img
    image = current_widget.image_cache[file_path] if file_path in current_widget.image_cache else image

    # Ensure image is grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Get scale factors
    dx = getattr(current_widget, 'dx', 1.0)
    dy = getattr(current_widget, 'dy', 1.0)

    if current_widget.mask_calcu is not None and isinstance(current_widget.mask_calcu, tuple) and isinstance(current_widget.mask_calcu[0], list):
        label_path = dock.get_label_path(file_path, current_widget.mask_calcu[0])
        if label_path is not None and os.path.exists(label_path):
            mask = cv2.imread(label_path, cv2.IMREAD_GRAYSCALE)
            mask = mask if current_widget.mask_calcu[1] else 255 - mask
        else:
            dock.parent.statusbar.showMessage(f"Failed to load label image: {label_path}", 3000)
            mask = np.ones_like(gray, dtype=np.uint8) * 255
    elif  current_widget.mask_calcu is not None and isinstance(current_widget.mask_calcu, tuple):
        mask = current_widget.mask_calcu[0]
        mask = mask if current_widget.mask_calcu[1] else 255 - mask
    else:
        mask = np.ones_like(gray, dtype=np.uint8) * 255

    mask = mask.squeeze()
    mask = (mask > 0).astype(np.uint8) * 255
    if mask.shape[:2] != gray.shape[:2]:
        mask = cv2.resize(mask, (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_NEAREST)

    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

    masked_image = cv2.bitwise_and(gray, mask)

    # Find pores (areas with value 0) within masked area
    pore_mask = np.zeros_like(gray, dtype=np.uint8)
    pore_mask[(masked_image == 0) & (mask == 255)] = 255

    # Calculate total pore area (pixels) - only within mask region
    pore_area_pixels = np.count_nonzero(pore_mask == 255)

    # Calculate total area of mask region
    mask_area = np.count_nonzero(mask == 255)

    # Calculate pore ratio (pore area as proportion of mask area)
    pore_ratio = pore_area_pixels / mask_area if mask_area > 0 else 0

    # Calculate total pore volume (assuming unit thickness)
    # Apply scale factors
    scaled_pore_area = pore_area_pixels * dx * dy
    scaled_mask_area = mask_area * dx * dy
    scaled_pore_volume = scaled_pore_area  # In 2D case, volume equals area

    return_info = \
        f"pore_ratio: {pore_ratio:.6f}" + "\n" + \
        f"pore_area: {pore_area_pixels}" + "\n" + \
        f"total_area: {mask_area}" + "\n" + \
        f"scaled_pore_area: {scaled_pore_area:.6f}" + "\n" + \
        f"scaled_total_area: {scaled_mask_area:.6f}" + "\n" + \
        f"scaled_pore_volume: {scaled_pore_volume:.6f}" + "\n" + \
        f"scale_factors: dx: {dx:.3f}, dy: {dy:.3f}"

    # Show information dialog
    msg_box = QtWidgets.QMessageBox(dock.parent)
    msg_box.setWindowTitle("Surface Measurement Information")
    msg_box.setText(str(return_info))
    msg_box.exec_()


def calculate_3d_info(dock):
    """
    Calculate pore statistics in 3D images
    """
    # Get current ImagesViewer instance
    images_viewer = dock.parent.tab_widget.currentWidget()

    if not hasattr(images_viewer, 'image_cache'):
        QtWidgets.QMessageBox.warning(dock, "Warning", "Current view does not support this operation")
        return

    # 检查 image_cache 是否为空，如果为空则自动加载所有图像
    if not images_viewer.image_cache:
        total_files = dock.parent.files_dock.list_widget.count()
        if total_files == 0:
            QtWidgets.QMessageBox.warning(dock, "Warning", "No files available to load. Please add images first.")
            return

        reply = QtWidgets.QMessageBox.question(
            dock,
            "Load Images",
            f"No cached images found. Load {total_files} images automatically?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # 显示加载进度
            progress_dialog = QtWidgets.QProgressDialog("Loading images...", "Cancel", 0, total_files, dock.parent)
            progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
            progress_dialog.setWindowTitle("Loading Images")
            progress_dialog.show()

            # 从文件管理器加载所有图像到缓存
            loaded_count = 0
            for i in range(total_files):
                progress_dialog.setValue(i)
                progress_dialog.setLabelText(f"Loading: {i + 1}/{total_files}")

                QtWidgets.QApplication.processEvents()

                if progress_dialog.wasCanceled():
                    progress_dialog.close()
                    return

                item = dock.parent.files_dock.list_widget.item(i)
                file_path = item.data(QtCore.Qt.UserRole)

                # 加载图像到缓存
                if file_path not in images_viewer.image_cache:
                    try:
                        img = cv2.imread(file_path)
                        if img is not None:
                            images_viewer.image_cache[file_path] = img
                            loaded_count += 1
                    except Exception as e:
                        print(f"Failed to load {file_path}: {str(e)}")
                        continue

            progress_dialog.setValue(total_files)
            progress_dialog.close()

            if loaded_count == 0:
                QtWidgets.QMessageBox.warning(dock, "Warning", "Failed to load any images from file list.")
                return
            else:
                dock.parent.statusbar.showMessage(f"Loaded {loaded_count} images automatically", 3000)
        else:
            return  # 用户取消操作

    # Get all images in the correct order
    images = []
    file_paths = []

    # Get images in order from file manager
    total_files = dock.parent.files_dock.list_widget.count()

    # Show progress dialog
    progress_dialog = QtWidgets.QProgressDialog("Preparing 3D calculation...", "Cancel", 0, total_files,
                                                dock.parent)
    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setWindowTitle("3D Calculation Preparation")
    progress_dialog.show()

    for i in range(total_files):
        # Update progress
        progress_dialog.setValue(i)

        item = dock.parent.files_dock.list_widget.item(i)
        file_path = item.data(QtCore.Qt.UserRole)
        if file_path in images_viewer.image_cache:
            img = images_viewer.image_cache[file_path]
            # Ensure image is grayscale
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            images.append(gray)
            file_paths.append(file_path)

        # Process events to update UI
        QtWidgets.QApplication.processEvents()

        # Check if user canceled operation
        if progress_dialog.wasCanceled():
            progress_dialog.close()
            dock.parent.statusbar.showMessage("3D calculation canceled", 3000)
            return

    # Complete preparation phase
    progress_dialog.setValue(total_files)
    progress_dialog.close()

    if not images:
        QtWidgets.QMessageBox.warning(dock, "Warning", "No valid images found for 3D calculation")
        return

    # Stack all images into 3D volume
    volume = np.stack(images, axis=0)

    # Get scale factors
    dx = getattr(images_viewer, 'dx', 1.0)
    dy = getattr(images_viewer, 'dy', 1.0)
    dz = getattr(images_viewer, 'dz', 1.0)

    # Get or create mask (similar to 2D version)
    mask_3d = None
    if hasattr(images_viewer, 'mask_calcu') and images_viewer.mask_calcu is not None:
        if isinstance(images_viewer.mask_calcu, tuple) and isinstance(images_viewer.mask_calcu[0], list):
            # Handle case where mask_calcu is (label_dir, mask_flag)
            label_dir = images_viewer.mask_calcu[0]
            mask_flag = images_viewer.mask_calcu[1]

            # 为每个图像文件匹配对应的掩码文件
            mask_list = []
            for file_path in file_paths:
                label_path = dock.get_label_path(file_path, label_dir)
                if label_path:
                    mask_2d = cv2.imread(label_path, cv2.IMREAD_GRAYSCALE)
                    # 确保是二维数组
                    if mask_2d is not None and len(mask_2d.shape) == 3:
                        # 如果是三维，只取一个通道
                        if mask_2d.shape[2] == 1:
                            mask_2d = mask_2d[:, :, 0]
                        else:
                            # 转换为灰度图
                            mask_2d = cv2.cvtColor(mask_2d, cv2.COLOR_BGR2GRAY)
                    # Apply mask flag
                    mask_2d = mask_2d if mask_flag else 255 - mask_2d
                    # 确保掩码尺寸与对应图像匹配
                    if mask_2d.shape[:2] != images[0].shape[:2]:
                        mask_2d = cv2.resize(mask_2d, (images[0].shape[1], images[0].shape[0]),
                                             interpolation=cv2.INTER_NEAREST)
                    mask_list.append(mask_2d)
                else:
                    # 如果找不到对应掩码，创建全白掩码
                    mask_2d = np.ones_like(images[0], dtype=np.uint8) * 255
                    mask_list.append(mask_2d)

            # 将掩码列表堆叠成3D掩码
            mask_3d = np.stack(mask_list, axis=0)

        elif isinstance(images_viewer.mask_calcu, tuple):
            # Handle case where mask_calcu is (mask, mask_flag)
            mask_2d = images_viewer.mask_calcu[0]
            mask_flag = images_viewer.mask_calcu[1]
            mask_2d = mask_2d if mask_flag else 255 - mask_2d
            # Ensure mask is the correct size and binary
            if mask_2d.shape[:2] != volume.shape[1:]:
                mask_2d = cv2.resize(mask_2d, (volume.shape[2], volume.shape[1]),
                                     interpolation=cv2.INTER_NEAREST)
            # Replicate mask across all slices
            mask_3d = np.stack([mask_2d] * len(images), axis=0)
    else:
        # If no mask provided, create a default mask covering the entire volume
        mask_3d = np.ones_like(volume, dtype=np.uint8) * 255

    # Ensure mask is binary
    mask_3d = (mask_3d > 0).astype(np.uint8) * 255

    # Apply mask to volume
    masked_volume = np.where(mask_3d == 255, volume, 255)  # Set non-masked areas to max value

    # Binarize the volume for pore detection (assuming pores are represented by lower values)
    # In many cases, pores would be 0 values in the image
    binary_volume = (masked_volume == 0).astype(np.uint8)

    # Apply mask to binary volume
    masked_binary_volume = binary_volume * (mask_3d // 255)

    # Calculate total pore volume (voxels) - only within mask region
    pore_volume_voxels = np.count_nonzero(masked_binary_volume)

    # Calculate total volume of mask region
    mask_volume_voxels = np.count_nonzero(mask_3d == 255)

    # Calculate pore ratio (pore volume as proportion of mask volume)
    pore_ratio = pore_volume_voxels / mask_volume_voxels if mask_volume_voxels > 0 else 0

    # Calculate surface area using morphological operations
    from scipy import ndimage

    # Find surface voxels (pore voxels that have non-pore neighbors)
    structuring_element = np.ones((3, 3, 3))
    eroded_pores = ndimage.binary_erosion(masked_binary_volume, structure=structuring_element)
    surface_voxels = masked_binary_volume - eroded_pores

    # Calculate surface area (number of surface voxels)
    surface_area_voxels = np.count_nonzero(surface_voxels)

    # Calculate scaled values
    scaled_pore_volume = pore_volume_voxels * dx * dy * dz
    scaled_mask_volume = mask_volume_voxels * dx * dy * dz
    scaled_surface_area = surface_area_voxels * dx * dy  # Surface area per slice

    # Calculate additional metrics
    # Number of connected pore components
    labeled_pores, num_components = ndimage.label(masked_binary_volume)
    # Average pore size
    avg_pore_size = scaled_pore_volume / num_components if num_components > 0 else 0

    return_info = \
        f"pore_ratio: {pore_ratio:.6f}" + "\n" + \
        f"pore_volume: {pore_volume_voxels} voxels" + "\n" + \
        f"pore_surface_area: {surface_area_voxels} voxels^2" + "\n" + \
        f"total_volume: {mask_volume_voxels} voxels" + "\n" + \
        f"scaled_pore_volume: {scaled_pore_volume:.6f} μm³" + "\n" + \
        f"scaled_total_volume: {scaled_mask_volume:.6f} μm³" + "\n" + \
        f"scaled_surface_area: {scaled_surface_area:.6f} μm²" + "\n" + \
        f"num_pore_components: {num_components}" + "\n" + \
        f"avg_pore_size: {avg_pore_size:.6f} μm³" + "\n" + \
        f"scale_factors: dx: {dx:.3f} μm, dy: {dy:.3f} μm, dz: {dz:.3f} μm"

    # Show information dialog
    msg_box = QtWidgets.QMessageBox(dock.parent)
    msg_box.setWindowTitle("3D Measurement Information")
    msg_box.setText(return_info)
    msg_box.exec_()
