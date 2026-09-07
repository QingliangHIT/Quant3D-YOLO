"""单图视图：图像/标注/检测结果加载与右键测量菜单。"""

import os
from copy import deepcopy

import cv2
import torch
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from quant.analysis import measure
from quant.core.gpu import print_gpu_memory_usage
from quant.detection import box_query, model_service, point_detection
from quant.ui.views.base_view import Viewer


class ImageViewer(Viewer):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cache = False
        self.auto_save = False
        self.mask_calcu = None
        self.masks_calcu = None

    def load_file(self, file_path):
        # Load image from file path
        if file_path in self.image_cache:
            self.img = file_path, deepcopy(self.image_cache[file_path])
        else:
            self.img = file_path, cv2.imread(file_path, cv2.IMREAD_COLOR)
        # imread 失败时 self.img 仍是元组，必须判第二个元素
        if self.img[1] is None:
            self.img = None
            self.parent.statusbar.showMessage(
                f"Error: Failed to load image {os.path.basename(file_path)}", 3000)
            return {}

        detect_success = False
        # Run YOLO detection if enabled
        if self.show_detect_results and self.parent.detector is not None:
            # self.img 是元组，不能对其元素赋值，只能整体替换
            detect_success, detected = self.parent.detector.detect(self.img[1])
            self.img = file_path, detected

        # Load YOLO results if available
        if self.load_yolo_results:
            detect_success = self.load_yolo_results_for_current_image(file_path, self.img[1])

        height, width, fmt, label_success, results_success = self.load_image()
        self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

        # Prepare image info for display
        image_info = {
            "File": os.path.basename(file_path),
            "Width": width,
            "Height": height,
            "Format": fmt,
        }
        if self.show_detect_results:
            image_info["Detect Results"] = detect_success
        if self.show_label:
            image_info["Label Status"] = label_success
        if self.show_results:
            image_info["YOLO Status"] = results_success
        return image_info

    def load_image(self):
        # Load and process image with labels/results
        if self.img is None:
            return 0, 0, None, False, False
        file_path, img = self.img
        height, width = img.shape[:2]
        label_success, results_success = False, False
        selected_classes = self.parent.yolo_dock.get_selected_classes() if self.parent.annos_dock.show_filtered else None

        # Load ground truth labels if enabled
        if self.mask_calcu is not None and isinstance(self.mask_calcu, tuple) and isinstance(self.mask_calcu[0], list):
            self.mask_opacity = self.mask_calcu[2]
            label_success, img, labels, classes = (
                self.load_labels_for_current_image(file_path, img, self.mask_calcu[0],
                                                   selected_classes, self.mask_calcu[1]))
        elif self.mask_calcu is not None and isinstance(self.mask_calcu, tuple):
            mask = self.mask_calcu[0]
            self.mask_opacity = self.mask_calcu[2]
            if self.mask_calcu[1]:
                mask = 255 - mask
            ret, img = self.load_aval_mask(img, mask, self.mask_opacity)

        if self.show_label:
            if file_path in self.label_cache:
                img = self.label_cache[file_path]['img']
                labels = self.label_cache[file_path]['labels']
                classes = self.label_cache[file_path]['classes']
                label_success = True
            else:
                label_success, img, labels, classes = (
                    self.load_labels_for_current_image(file_path, img, self.parent.files_dock.label_paths,
                                                       selected_classes))
                if label_success:
                    self.label_cache[file_path] = {'img': img, 'labels': labels, 'classes': classes}
            self.parent.annos_dock.update_annot_info(labels, selected_classes)
            self.parent.categories_dock.update_content(classes, selected_classes)

        # Load detection results if enabled
        if self.show_results:
            if file_path in self.yolo_cache:
                img = self.yolo_cache[file_path]['img']
                labels = self.yolo_cache[file_path]['labels']
                classes = self.yolo_cache[file_path]['classes']
                results_success = True
            else:
                results_success, img, labels, classes = self.load_results_for_current_image(file_path, img,
                                                                                            selected_classes)
                if results_success:
                    self.yolo_cache[file_path] = {'img': img, 'labels': labels, 'classes': classes}
            self.parent.annos_dock.update_all_info(labels, selected_classes)
            self.parent.categories_dock.update_content(classes, selected_classes)

        self.img = file_path, img
        fmt = self.update_image(img)

        # Update patch rectangle in point detection mode
        if self.point_detection_mode and self.patch_rect_item:
            if self.parent.yolo_dock.patch_hide_timer and self.parent.yolo_dock.patch_hide_timer.isActive():
                yolo_params = self.parent.yolo_dock.get_parameters()
                patch_size_percent = yolo_params.get("patch_size", 50)
                self.update_patch_rect(patch_size_percent)
        return height, width, fmt, label_success, results_success

    def load_labels_for_current_image(self, file_path, img, label_dir, selected_classes, reverse=False):
        """
        Load corresponding label file for current image
        """
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        # label_dir = self.parent.files_dock.label_paths
        ret = False
        yolo_labels, labels, classes = None, [], {}

        if len(label_dir) > 0:
            matched_files = []
            for label_file in label_dir:
                label_base = os.path.splitext(os.path.basename(label_file))[0]
                if label_base == base_name:
                    matched_files.append(label_file)
            if matched_files:
                for label_file in matched_files:
                    _, ext = os.path.splitext(label_file)
                    try:
                        # Load different label formats
                        if ext == ".txt":
                            ret, yolo_labels = self.load_label_file_txt(img, label_file)
                        elif ext == ".json":
                            ret, yolo_labels = self.load_label_file_json(img, label_file)
                        elif ext == ".xml":
                            ret, yolo_labels = self.load_label_file_xml(img, label_file)
                        elif ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", }:
                            ret, img = self.load_mask(img, label_file, reverse=reverse)
                            yolo_labels = None
                        else:
                            ret = False
                    except Exception as e:
                        ret = False

        if yolo_labels:
            labels = self.parent.plotter.get_info_abels(yolo_labels)
            classes = self.parent.yolo_dock.get_classes_labels(yolo_labels)
            img = self.parent.plotter.process_mini(img, yolo_labels, selected_classes,
                                                   show_boxes=self.parent.annos_dock.show_boxes,
                                                   show_conf=self.parent.annos_dock.show_confidence,
                                                   show_labels=self.parent.annos_dock.show_labels)
        # if return_mask:
        #     mask = self.results_to_mask(yolo_labels)
        #     return ret, img, mask, classes, mask
        # else:
        return ret, img, labels, classes

    def load_results_for_current_image(self, file_path, img, selected_classes):
        # Load detection results for current image
        ret, info_labels, classes = False, [], {}
        if len(self.yolo_results) > 0:
            if file_path in self.yolo_results:
                results_label = deepcopy(self.yolo_results[file_path])
                results_label = self.parent.plotter.filter_results_label(results_label, selected_classes)
                info_labels = self.parent.plotter.get_info_abels(results_label)
                classes = self.parent.yolo_dock.get_classes_labels(results_label)
                img = self.parent.plotter.process_mini(img, results_label, selected_classes,
                                                       show_boxes=self.parent.annos_dock.show_boxes,
                                                       show_conf=self.parent.annos_dock.show_confidence,
                                                       show_labels=self.parent.annos_dock.show_labels)
                if self.auto_save:
                    self._save_with_current_format()
                ret = True
        return ret, img, info_labels, classes

    def _save_with_current_format(self):
        # Placeholder for auto-saving functionality
        pass

    def load_yolo_results_for_current_image(self, file_path, img):
        """对当前图像执行 YOLO 检测，结果写入 yolo_results 缓存。"""
        if file_path in self.yolo_results:
            return True

        model = self.parent.yolo_model
        if not model_service.is_ready(model, self.parent.yolo_model_name):
            self.parent.statusbar.showMessage("❌ YOLO model is not loaded", 5000)
            return False

        yolo_params = self.parent.yolo_dock.get_parameters()
        # Run detection
        results = model(
            img,
            conf=yolo_params["conf_threshold"],
            iou=yolo_params["iou_threshold"],
            retina_masks=True,
        )
        # Process and cache results
        self.yolo_results[file_path] = self.result_to_label(results[0])
        del results
        # Clear CUDA cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        self.parent.statusbar.showMessage(print_gpu_memory_usage(ret=True), 2000)
        return True

    def enable_point_detection_mode(self):
        """Enable point detection mode"""
        self.point_detection_mode = True
        self.graphics_view.setCursor(Qt.CrossCursor)
        self.parent.statusbar.showMessage("Point detection mode enabled - Click image for local detection", 3000)

    def disable_point_detection_mode(self):
        """Disable point detection mode"""
        self.point_detection_mode = False
        self.last_click_point = None
        self.graphics_view.setCursor(Qt.ArrowCursor)
        self.parent.statusbar.showMessage("Point detection mode disabled", 3000)
        self.hide_patch_rect()

    def handle_point_detection(self, event, super=False):
        """Handle point detection logic"""
        # Get click position in scene coordinates
        scene_pos = self.graphics_view.mapToScene(event.pos())

        # Get image item boundaries
        pixmap_rect = self.pixmap_item.boundingRect()
        pixmap_top_left = self.pixmap_item.mapToScene(pixmap_rect.topLeft())
        pixmap_bottom_right = self.pixmap_item.mapToScene(pixmap_rect.bottomRight())

        # Check if click is within image
        if pixmap_top_left.x() <= scene_pos.x() <= pixmap_bottom_right.x() and \
                pixmap_top_left.y() <= scene_pos.y() <= pixmap_bottom_right.y():

            # Calculate click position relative to image
            relative_x = scene_pos.x() - pixmap_top_left.x()
            relative_y = scene_pos.y() - pixmap_top_left.y()

            # Save click point
            self.last_click_point = (relative_x, relative_y)

            # Perform local detection
            if not super:
                self.perform_local_detection(relative_x, relative_y)
            else:
                self.perform_3d_detection(relative_x, relative_y)
        else:
            self.parent.statusbar.showMessage("Please click within the image area", 2000)

    def perform_3d_detection(self, point_x, point_y):
        point_detection.perform_3d_detection(self, point_x, point_y)

    def perform_local_detection(self, x, y):
        return point_detection.perform_local_detection(self, x, y)

    def boxes_overlap(self, box1, box2, threshold=0.3):
        return box_query.boxes_overlap(self, box1, box2, threshold)

    def find_nearest_box2(self, scene_pos, results_label):
        return box_query.find_nearest_box(self, scene_pos, results_label)

    def extract_single_label(self, results_label, box_idx):
        return box_query.extract_single_label(self, results_label, box_idx)

    def delete_detection(self, box_idx):
        """Delete detection result at specified index"""
        file_path = self.img[0]

        # Check if file path exists in yolo_results
        if file_path not in self.yolo_results:
            return

        # Get current label data
        labels = self.yolo_results[file_path]

        # Delete specified bounding box data
        if "boxes" in labels and box_idx < len(labels["boxes"]):
            labels["boxes"].pop(box_idx)

        # Delete corresponding mask if exists
        if "masks" in labels and box_idx < len(labels["masks"]):
            labels["masks"].pop(box_idx)

        # Delete corresponding keypoints if exists
        if "keypoints" in labels and box_idx < len(labels["keypoints"]):
            labels["keypoints"].pop(box_idx)

        # Delete corresponding obb if exists
        if "obb" in labels and box_idx < len(labels["obb"]):
            labels["obb"].pop(box_idx)

        # Update yolo_results
        self.yolo_results[file_path] = labels

        # Reload image to update display
        if file_path in self.yolo_cache:
            del self.yolo_cache[file_path]
        self.load_file(file_path)

        # Update status bar
        self.parent.statusbar.showMessage(f"Deleted detection result {box_idx}", 2000)

    def measure_2d_object_info(self, img, box_idx):
        return measure.measure_2d_object_info(self, img, box_idx)

    def measure_3d_object_info(self, img, box_idx):
        return measure.measure_3d_object_info(self, img, box_idx)

    def total_2d_info(self):
        return measure.total_2d_info(self)

    def total_3d_info(self):
        return measure.total_3d_info(self)

    # ===== Mouse Interaction Methods =====
    def on_context_menu(self, point):
        """Handle context menu request"""
        # Only enable this feature in point detection mode

        if not (self.show_label or self.show_results) or self.img is None:
            return

        # Get mouse position in scene coordinates
        scene_pos = self.graphics_view.mapToScene(point)

        # Check if there are detection results
        if self.img[0] not in self.yolo_results and self.img[0] in self.yolo_cache:
            del self.yolo_cache[self.img[0]]
            self.load_file(self.img[0])

        if self.img[0] in self.yolo_results:
            results_label = self.yolo_results[self.img[0]]

            # If there are bounding boxes
            if "boxes" in results_label and results_label["boxes"] is not None:
                self.context_menu = QtWidgets.QMenu(self)
                # Find nearest detection box
                nearest_box_idx = self.find_nearest_box2(scene_pos, results_label)
                if nearest_box_idx is not None:
                    new_label = self.extract_single_label(results_label, nearest_box_idx)
                    img = self.parent.plotter.process_mini(self.img[1], new_label)
                    self.update_image(img)
                    self.context_menu.setTitle(f"{nearest_box_idx}")
                    id_action = self.context_menu.addAction(f"Select: {nearest_box_idx}")
                    measure_action = self.context_menu.addAction("Measure Object Information")
                    measure3d_action = self.context_menu.addAction("Measure 3D Object Information")
                    total_2d_action = self.context_menu.addAction("Measure Surface Information")
                    total_3d_action = self.context_menu.addAction("Measure Voxel Information")
                    delete_action = self.context_menu.addAction("Delete Nearest Detection Result")
                    delete_action.triggered.connect(lambda: self.delete_detection(nearest_box_idx))
                    measure_action.triggered.connect(lambda: self.measure_2d_object_info(img, nearest_box_idx))
                    measure3d_action.triggered.connect(lambda: self.measure_3d_object_info(img, nearest_box_idx))
                    total_2d_action.triggered.connect(self.total_2d_info)
                    total_3d_action.triggered.connect(self.total_3d_info)
                    self.context_menu.aboutToHide.connect(self.load_image)
                else:
                    total_2d_action = self.context_menu.addAction("Measure Surface Information")
                    total_3d_action = self.context_menu.addAction("Measure Voxel Information")
                    total_2d_action.triggered.connect(self.total_2d_info)
                    total_3d_action.triggered.connect(self.total_3d_info)
                self.context_menu.exec_(self.graphics_view.mapToGlobal(point))
