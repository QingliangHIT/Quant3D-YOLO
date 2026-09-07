"""批量视图动作：一键批量检测与整批结果按当前格式保存。"""

import os
import traceback
from copy import deepcopy
import cv2
import torch
from PyQt5 import QtWidgets, QtCore
from quant.core.config import JSON
from quant.core.gpu import print_gpu_memory_usage


def process_all_images(view, checked, save=False):
    # Process all images with optional saving
    try:
        save_type = "image"

        # Determine save format
        if view.action_save_txt.isChecked():
            save_type = "txt"
        elif view.action_save_json.isChecked():
            save_type = "json"
        elif view.action_save_mask.isChecked():
            save_type = "mask"

        yolo_params = view.parent.yolo_dock.get_parameters()
        task_type = yolo_params['task']

        total_files = len(view.parent.files_dock.file_paths)
        if total_files == 0:
            view.parent.statusbar.showMessage("No files to save", 2000)
            return
        ret = view.parent.load_model()
        if not ret:
            return
        os.makedirs(view._get_save_path(""), exist_ok=True)

        # Create progress dialog
        progress_dialog = QtWidgets.QProgressDialog("Saving all files...", "Cancel", 0, total_files, view.parent)
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setWindowTitle("Save All Files")
        progress_dialog.show()

        count, count_saved = 0, 0
        for i, file_path in enumerate(view.parent.files_dock.file_paths):
            if progress_dialog.wasCanceled():
                break

            progress_dialog.setValue(i)
            progress_dialog.setLabelText(f"Processing: {os.path.basename(file_path)}")

            QtWidgets.QApplication.processEvents()
            if file_path not in view.yolo_results and (save_type != "image" or not save):
                img = view.image_cache[file_path] if file_path in view.image_cache else cv2.imread(file_path,
                                                                                                   cv2.IMREAD_COLOR)
                if img is not None:
                    yolo_params = view.parent.yolo_dock.get_parameters()
                    results = view.parent.yolo_model(
                        img,
                        conf=yolo_params["conf_threshold"],
                        iou=yolo_params["iou_threshold"],
                        retina_masks=True,
                    )
                else:
                    continue

                if len(results) > 0:
                    results_label = view.result_to_label(results[0])
                    view.yolo_results[file_path] = results_label

                    ret = print_gpu_memory_usage(ret=True)
                    view.parent.statusbar.showMessage(ret, 2000)
                    del results
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                count += 1
            if save:
                if view.save_results_label(file_path, save_type, task_type):
                    count_saved += 1

        view.load_image()
        view.parent.statusbar.showMessage(f"Processed {count} images (save {count_saved})", 3000)
    except Exception as e:
        view.parent.statusbar.showMessage(f"Save failed: {str(e)}", 3000)
    finally:
        if 'progress_dialog' in locals():
            progress_dialog.close()


def save_results_label(view, file_path, save_type, task_type):
    # Save results in specified format
    if save_type == "image":
        format_type = "png"
    elif save_type == "mask":
        format_type = "png"
    elif save_type == "txt":
        format_type = "txt"
    elif save_type == "json":
        format_type = "json"
    else:
        format_type = "png"
    ext = "." + format_type
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    save_path = view._get_save_path(f"{base_name}{ext}")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    if save_type in {"mask", "txt", "json"}:
        selected_classes = view.parent.yolo_dock.get_selected_classes() if view.parent.annos_dock.show_filtered else None
        results_label = deepcopy(view.yolo_results[file_path])
        results_label = view.parent.plotter.filter_results_label(results_label, classes_names=selected_classes)
        if task_type != "segment":
            results_label['masks'] = []
        if task_type != "obb":
            results_label['obb'] = []
        if task_type != "pose":
            results_label['keypoints'] = []
        if format_type == "txt":
            return view._export_labels_to_txt(results_label, save_path), save_path
        elif format_type == "json":
            if JSON == "coco":
                return view._export_labels_to_json(results_label, save_path, "coco"), save_path
            else:
                return view._export_labels_to_json(results_label, save_path, "labelme"), save_path
        else:
            return view._export_mask(results_label, save_path), save_path
    else:
        return view._save_image(file_path, save_path), save_path


def save_with_current_format(view):
    # Save current image with selected format
    current_item = view.parent.files_dock.list_widget.currentItem()
    if not current_item:
        view.parent.statusbar.showMessage("No image selected", 2000)
        return

    file_path = current_item.data(QtCore.Qt.UserRole)
    if file_path not in view.yolo_results:
        view.parent.statusbar.showMessage("No YOLO results for current image", 2000)
        return
    save_type = "image"

    if view.action_save_txt.isChecked():
        save_type = "txt"
    elif view.action_save_json.isChecked():
        save_type = "json"
    elif view.action_save_mask.isChecked():
        save_type = "mask"

    yolo_params = view.parent.yolo_dock.get_parameters()
    task_type = yolo_params['task']
    ret, save_path = view.save_results_label(file_path, save_type, task_type)
    if ret:
        view.parent.statusbar.showMessage(f"File({save_type}) saved to: {save_path}", 3000)
    else:
        view.parent.statusbar.showMessage("Save failed", 3000)


def batch_detect(view):
    """对所有已打开图像执行批量检测。"""
    if not view.parent.files_dock.file_paths:
        view.parent.statusbar.showMessage("No images to detect", 2000)
        return

    # 先确保模型可用再建模态进度框：否则加载失败时 return 会把进度框永久留在屏上锁住界面
    if not view.parent.load_model():
        return

    yolo_params = view.parent.yolo_dock.get_parameters()
    file_paths = view.parent.files_dock.file_paths
    total_files = len(file_paths)

    progress_dialog = QtWidgets.QProgressDialog("Performing batch detection...", "Cancel", 0,
                                                total_files,
                                                view.parent)
    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
    progress_dialog.setWindowTitle("Batch Detection")
    progress_dialog.show()
    try:
        for i, file_path in enumerate(file_paths):
            if progress_dialog.wasCanceled():
                break

            progress_dialog.setValue(i)
            progress_dialog.setLabelText(f"Detecting: {os.path.basename(file_path)}")

            QtWidgets.QApplication.processEvents()
            img = view.image_cache[file_path] if file_path in view.image_cache else cv2.imread(file_path,
                                                                                               cv2.IMREAD_COLOR)
            if img is None:
                continue

            results = view.parent.yolo_model(
                img,
                conf=yolo_params["conf_threshold"],
                iou=yolo_params["iou_threshold"],
                retina_masks=True,
            )
            if len(results) > 0:
                view.yolo_results[file_path] = view.result_to_label(results[0])
            del results
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        progress_dialog.setValue(total_files)
        view.parent.statusbar.showMessage(f"Batch detection completed, processed {len(view.yolo_results)} images",
                                          3000)
        view.load_image()

    except Exception as e:
        view.parent.statusbar.showMessage(f"Batch detection error: {str(e)}", 5000)
        traceback.print_exc()
    finally:
        progress_dialog.close()
