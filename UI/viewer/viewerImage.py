import os

import numpy as np
import torch
from copy import deepcopy
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from UI.tools.tool_plot_yolo import *
from UI.viewer.viewer import Viewer
from ultralytics.engine.results import Boxes, Masks, Keypoints, OBB
from ultralytics.utils import ops
from UI.tools.utils import print_gpu_memory_usage


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
        if self.img is None:
            self.parent.statusbar.showMessage("Error: Failed to load image", 2000)
            return {}

        detect_success = False
        # Run YOLO detection if enabled
        if self.show_detect_results:
            detect_success, self.img[1] = self.parent.detector.detect(self.img[1])

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
        """
        Perform YOLO detection on current image
        """
        if file_path not in self.yolo_results:
            if self.parent.yolo_model and self.parent.yolo_model_name:
                yolo_params = self.parent.yolo_dock.get_parameters()
                # Run detection
                results = self.parent.yolo_model(
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
                ret = print_gpu_memory_usage(ret=True)
                self.parent.statusbar.showMessage(ret, 2000)
                return True
            else:
                self.parent.statusbar.showMessage(f"❌ YOLO detection failed", 5000)
                import traceback
                traceback.print_exc()
                return False
        else:
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
        """
        Perform 3D detection across all images to find targets containing specified point
        """
        yolo_params = self.parent.yolo_dock.get_parameters()
        detection_count = 0
        new_yolo_results = {}

        # Iterate through all images
        for file_path in self.parent.files_dock.file_paths:
            if self.yolo_cache and file_path in self.yolo_cache:
                img = self.yolo_cache[file_path]['img']
            else:
                img = self.image_cache[file_path] if file_path in self.image_cache else cv2.imread(file_path,
                                                                                                   cv2.IMREAD_COLOR)

            # Perform detection
            results = self.parent.yolo_model(
                img,
                conf=yolo_params["conf_threshold"],
                iou=yolo_params["iou_threshold"],
                retina_masks=True,
            )
            print_gpu_memory_usage()

            # Filter targets containing click point
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                # Find boxes containing click point
                contained_box_indices = []
                for i, (x1, y1, x2, y2) in enumerate(boxes):
                    if x1 <= point_x <= x2 and y1 <= point_y <= y2:
                        contained_box_indices.append(i)

                # If found boxes containing click point
                if contained_box_indices:
                    # Select appropriate box
                    if len(contained_box_indices) == 1:
                        selected_index = contained_box_indices[0]
                    else:
                        # Select box closest to click point center
                        min_distance = float('inf')
                        selected_index = 0
                        for i in contained_box_indices:
                            x1, y1, x2, y2 = boxes[i]
                            center_x = (x1 + x2) / 2
                            center_y = (y1 + y2) / 2
                            distance = ((point_x - center_x) ** 2 + (point_y - center_y) ** 2) ** 0.5
                            if distance < min_distance:
                                min_distance = distance
                                selected_index = i

                    # Keep only selected box
                    selected_boxes = boxes[[selected_index]]
                    confidences = results[0].boxes.conf.cpu().numpy()[[selected_index]]
                    class_ids = results[0].boxes.cls.cpu().numpy().astype(int)[[selected_index]]

                    # Process other possible data (masks, keypoints, obb)
                    selected_masks = None
                    selected_keypoints = None
                    selected_obb = None

                    if results[0].masks is not None:
                        masks = results[0].masks.data.cpu().numpy()
                        if selected_index < len(masks):
                            selected_masks = masks[[selected_index]]

                    if results[0].keypoints is not None:
                        keypoints = results[0].keypoints.data.cpu().numpy()
                        if selected_index < len(keypoints):
                            selected_keypoints = keypoints[[selected_index]]

                    if results[0].obb is not None:
                        obb = results[0].obb.data.cpu().numpy()
                        if selected_index < len(obb):
                            selected_obb = obb[[selected_index]]

                    # Create new result object
                    new_result = results[0].__class__(
                        orig_img=results[0].orig_img,
                        path=results[0].path,
                        names=results[0].names
                    )

                    # Set boxes
                    boxes_data = np.concatenate([
                        selected_boxes,
                        confidences.reshape(-1, 1),
                        class_ids.reshape(-1, 1)
                    ], axis=1)
                    new_result.boxes = Boxes(
                        boxes=torch.from_numpy(boxes_data),
                        orig_shape=results[0].orig_shape
                    )

                    # Set masks
                    if selected_masks is not None:
                        new_result.masks = Masks(
                            torch.from_numpy(selected_masks),
                            orig_shape=results[0].orig_shape
                        )

                    # Set keypoints
                    if selected_keypoints is not None:
                        new_result.keypoints = Keypoints(
                            torch.from_numpy(selected_keypoints),
                            orig_shape=results[0].orig_shape
                        )

                    # Set obb
                    if selected_obb is not None:
                        new_result.obb = OBB(
                            torch.from_numpy(selected_obb),
                            orig_shape=results[0].orig_shape
                        )

                    # Merge with original results
                    detection_count += 1
                    new_yolo_results[file_path] = [new_result]
                    new_label = self.result_to_label(new_result)
                    self.merge_results_label(file_path, new_label)
                    labels = self.parent.plotter.get_info_abels(new_label)
                    classes = self.parent.yolo_dock.get_classes_labels(new_label)

                    if self.yolo_cache and file_path in self.yolo_cache:
                        classes_old = self.yolo_cache[file_path]['classes']
                        labels_old = self.yolo_cache[file_path]['labels']
                        for class_name, count in classes.items():
                            classes_old[class_name] = classes_old.get(class_name, 0) + count
                        labels = labels_old + labels
                        classes = classes_old

                    selected_classes = self.parent.yolo_dock.get_selected_classes() if self.parent.annos_dock.show_filtered else None

                    new_result[0].orig_img = img
                    img = self.parent.plotter.process_mini(img, new_label, selected_classes,
                                                           show_boxes=self.parent.annos_dock.show_boxes,
                                                           show_conf=self.parent.annos_dock.show_confidence,
                                                           show_labels=self.parent.annos_dock.show_labels)
                    self.yolo_cache[file_path] = {'img': img, 'labels': labels, 'classes': classes}
                    del results
                    # Clear CUDA cache
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                else:
                    # If no box contains click point, keep original results unchanged
                    pass

        self.load_image()
        self.parent.statusbar.showMessage(f"✅ 3D detection completed: Detected {detection_count} targets", 3000)

    def perform_local_detection(self, x, y):
        """Perform local detection around clicked point"""
        if not hasattr(self, "img"):
            return
        try:
            # Get detection area size
            yolo_params = self.parent.yolo_dock.get_parameters()
            patch_size_percent = yolo_params.get("patch_size", 50)
            max_detections = yolo_params.get("max_detections", 50)

            file_path, img = self.img
            # Calculate actual patch size based on image size and percentage
            img_height, img_width = img.shape[:2]
            patch_size = int(min(img_width, img_height) * patch_size_percent / 100)
            patch_size = min(patch_size, img_width, img_height)  # Prevent exceeding image boundaries
            if patch_size > 0:
                # Calculate detection area boundaries
                half_size = patch_size // 2
                x1 = max(0, int(x - half_size))
                y1 = max(0, int(y - half_size))
                x2 = min(img.shape[1], int(x + half_size))
                y2 = min(img.shape[0], int(y + half_size))

                # Extract local image
                patch_img = img[y1:y2, x1:x2]
            else:
                x1 = 0
                y1 = 0
                x2 = img.shape[1]
                y2 = img.shape[0]
                patch_img = img

            if patch_img.size == 0:
                self.parent.statusbar.showMessage("Unable to extract local image", 2000)
                return

            # Perform detection
            results = self.parent.yolo_model(
                patch_img,
                conf=yolo_params["conf_threshold"],
                iou=yolo_params["iou_threshold"],
                verbose=False,
                retina_masks=True,
            )
            ret = print_gpu_memory_usage(ret=True)

            if len(results) > 0:
                result = results[0]
                masks = None
                keypoints = None
                obb = None

                # Draw detection results on original image
                if result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)
                    if result.keypoints is not None:
                        keypoints = result.keypoints.data.cpu().numpy()
                    if result.masks is not None:
                        masks = result.masks.data.cpu().numpy()
                    if result.obb is not None:
                        obb = result.obb.data.cpu().numpy()

                    # Handle max detection count
                    if max_detections == 1 and len(boxes) > 0:
                        # Find nearest detection box
                        distances = []
                        for i in range(len(boxes)):
                            px1, py1, px2, py2 = boxes[i]
                            center_x = (px1 + px2) / 2
                            center_y = (py1 + py2) / 2
                            distance = np.sqrt((x - (center_x + x1)) ** 2 + (y - (center_y + y1)) ** 2)
                            distances.append(distance)

                        # Find nearest detection box
                        closest_idx = np.argmin(distances)

                        # Keep only nearest detection box
                        boxes = boxes[[closest_idx]]
                        confidences = confidences[[closest_idx]]
                        class_ids = class_ids[[closest_idx]]
                        if keypoints is not None:
                            keypoints = keypoints[[closest_idx]]
                        if masks is not None:
                            masks = masks[[closest_idx]]

                    # If max detection count is set, sort by confidence and take top N
                    elif max_detections > 1 and len(boxes) > max_detections:
                        # Sort by confidence
                        # Keep only top N detections with highest confidence
                        boxes = boxes[:max_detections]
                        confidences = confidences[:max_detections]
                        class_ids = class_ids[:max_detections]
                        if keypoints is not None:
                            keypoints = keypoints[:max_detections]
                        if masks is not None:
                            masks = masks[:max_detections]

                    # Convert detection box coordinates to original image coordinate system
                    boxes[:, [0, 2]] += x1  # x coordinate offset
                    boxes[:, [1, 3]] += y1  # y coordinate offset

                    # Update boxes in result
                    result.boxes = Boxes(
                        boxes=torch.from_numpy(
                            np.concatenate([boxes, confidences.reshape(-1, 1), class_ids.reshape(-1, 1)], axis=1)),
                        orig_shape=img.shape[:2])

                    # Process masks
                    if masks is not None:
                        patch_masks = ops.scale_image(masks.transpose(1, 2, 0),
                                                      (patch_img.shape[0], patch_img.shape[1], masks.shape[-1]))
                        orig_masks = np.zeros((img.shape[0], img.shape[1], masks.shape[0]))
                        orig_masks[y1:y2, x1:x2, :] = patch_masks[:, :, :]
                        if 'imgsz' in self.parent.yolo_model.overrides:
                            sz = self.parent.yolo_model.overrides['imgsz']
                        else:
                            sz = self.parent.yolo_model.ckpt['train_args']['imgsz']
                        orig_masks = orig_masks.transpose(2, 0, 1)
                        result.masks = Masks(
                            torch.from_numpy(orig_masks),
                            orig_shape=img.shape[:2])

                    # Process keypoints
                    if keypoints is not None:
                        # Convert keypoint coordinates to original image coordinate system
                        if len(keypoints.shape) >= 3:
                            keypoints[:, :, 0] += x1  # x coordinate offset
                            keypoints[:, :, 1] += y1  # y coordinate offset
                            result.keypoints = Keypoints(
                                torch.from_numpy(keypoints),
                                orig_shape=img.shape[:2])

                    # Process OBB (oriented bounding box)
                    if obb is not None:
                        # OBB format is usually [x_center, y_center, width, height, angle]
                        # Convert OBB coordinates to original image coordinate system
                        obb[:, 0] += x1  # x_center offset
                        obb[:, 1] += y1  # y_center offset
                        result.obb = OBB(
                            torch.from_numpy(obb),
                            orig_shape=img.shape[:2]
                        )

                    detection_count = len(result.boxes)
                    result.orig_img = img
                    # Draw detection boxes
                    classes = self.parent.yolo_dock.get_classes(results)
                    labels = self.parent.plotter.get_info(results)
                    new_results_label = self.result_to_label(result)

                    if file_path in self.yolo_cache:
                        classes_old = self.yolo_cache[file_path]['classes']
                        labels_old = self.yolo_cache[file_path]['labels']
                        for class_name, count in classes.items():
                            classes_old[class_name] = classes_old.get(class_name, 0) + count
                        labels = labels_old + labels
                        classes = classes_old

                    self.merge_results_label(file_path, new_results_label)
                    selected_classes = self.parent.yolo_dock.get_selected_classes() if self.parent.annos_dock.show_filtered else None

                    self.parent.annos_dock.update_all_info(labels, selected_classes)
                    self.parent.categories_dock.update_content(classes, selected_classes)

                    # Update displayed image
                    results[0].orig_img = self.img[1]
                    img = self.parent.plotter.process_mini(img, new_results_label, selected_classes,
                                                           show_boxes=self.parent.annos_dock.show_boxes,
                                                           show_conf=self.parent.annos_dock.show_confidence,
                                                           show_labels=self.parent.annos_dock.show_labels)
                    self.img = file_path, img
                    self.update_image(img)
                    self.yolo_cache[file_path] = {'img': img, 'labels': labels, 'classes': classes}
                    del results
                    # Clear CUDA cache
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    self.parent.statusbar.showMessage(
                        f"✅ Local detection completed: Detected {detection_count} targets({ret})", 3000)
                else:
                    self.parent.statusbar.showMessage("✅ Local detection completed: No targets detected", 3000)
            else:
                self.parent.statusbar.showMessage("✅ Local detection completed: No targets detected", 3000)

        except Exception as e:
            self.parent.statusbar.showMessage(f"❌ Local detection failed: {str(e)}", 5000)
            import traceback
            traceback.print_exc()

    def boxes_overlap(self, box1, box2, threshold=0.3):
        """Check if two bounding boxes overlap"""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2

        # Calculate overlap area
        x_left = max(x1_min, x2_min)
        y_top = max(y1_min, y2_min)
        x_right = min(x1_max, x2_max)
        y_bottom = min(y1_max, y2_max)

        if x_right <= x_left or y_bottom <= y_top:
            return False

        # Calculate overlap area
        overlap_area = (x_right - x_left) * (y_bottom - y_top)

        # Calculate area of both boxes
        area1 = (x1_max - x1_min) * (y1_max - y1_min)
        area2 = (x2_max - x2_min) * (y2_max - y2_min)

        # Calculate IoU
        iou = overlap_area / (area1 + area2 - overlap_area) if (area1 + area2 - overlap_area) > 0 else 0

        return iou >= threshold

    def find_nearest_box(self, scene_pos, results):
        """Find nearest bounding box and return a new results object with only that box"""
        if results.boxes is None:
            return None, None

        # Convert scene coordinates to image coordinates
        img_x, img_y = scene_pos.x(), scene_pos.y()

        target_idx = None

        # If masks exist, check if point is inside any mask first
        if hasattr(results, 'masks') and results.masks is not None and results.masks.data is not None:
            masks = results.masks.data.cpu().numpy()
            # Check if point is inside any mask
            for i in range(len(masks)):
                mask = masks[i]
                # Check if point is in mask
                if 0 <= int(img_y) < mask.shape[0] and 0 <= int(img_x) < mask.shape[1]:
                    if mask[int(img_y), int(img_x)] > 0:
                        target_idx = i
                        break

        # If no mask contains the point, use bounding box method
        if target_idx is None and hasattr(results,
                                          'boxes') and results.boxes is not None and results.boxes.xyxy is not None:
            box_coords = results.boxes.xyxy.cpu().numpy()

            # Calculate distance to each box center
            min_distance = float('inf')
            nearest_idx = None

            for i, (x1, y1, x2, y2) in enumerate(box_coords):
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                distance = ((img_x - center_x) ** 2 + (img_y - center_y) ** 2) ** 0.5

                if distance < min_distance:
                    min_distance = distance
                    nearest_idx = i

            # If nearest distance is less than threshold
            if min_distance < 50:
                target_idx = nearest_idx

        if target_idx is not None:
            # Create new result with only selected box
            new_result = results.__class__(
                orig_img=results.orig_img,
                path=results.path,
                names=results.names
            )

            # Copy selected box data
            boxes_data = results.boxes.data.cpu().numpy()
            selected_box = boxes_data[[target_idx]]

            new_result.boxes = Boxes(
                boxes=torch.from_numpy(selected_box),
                orig_shape=results.boxes.orig_shape
            )

            # Copy corresponding masks if exist
            if hasattr(results, 'masks') and results.masks is not None:
                masks_data = results.masks.data.cpu().numpy()
                if target_idx < len(masks_data):
                    selected_mask = masks_data[[target_idx]]
                    new_result.masks = Masks(
                        torch.from_numpy(selected_mask),
                        orig_shape=results.masks.orig_shape
                    )

            # Copy corresponding keypoints if exist
            if hasattr(results, 'keypoints') and results.keypoints is not None:
                keypoints_data = results.keypoints.data.cpu().numpy()
                if target_idx < len(keypoints_data):
                    selected_keypoints = keypoints_data[[target_idx]]
                    new_result.keypoints = Keypoints(
                        torch.from_numpy(selected_keypoints),
                        orig_shape=results.keypoints.orig_shape
                    )

            # Copy corresponding obb if exist
            if hasattr(results, 'obb') and results.obb is not None:
                obb_data = results.obb.data.cpu().numpy()
                if target_idx < len(obb_data):
                    selected_obb = obb_data[[target_idx]]
                    new_result.obb = OBB(
                        torch.from_numpy(selected_obb),
                        orig_shape=results.obb.orig_shape
                    )

            return target_idx, new_result

        return None, None

    def find_nearest_box2(self, scene_pos, results_label):
        """
        Find nearest bounding box in label format dictionary and return index of the box
        """
        # Check if boxes exist in results_label
        if "boxes" not in results_label or not results_label["boxes"]:
            return None

        # Convert scene coordinates to image coordinates
        img_x, img_y = scene_pos.x(), scene_pos.y()

        target_idx = None
        boxes = results_label["boxes"]

        # If masks exist, check if point is inside any mask first
        if "masks" in results_label and results_label["masks"]:
            masks = results_label["masks"]
            # Check if point is inside any mask
            for i, mask_data in enumerate(masks):
                if len(mask_data) < 3:  # Need at least class_id and two points
                    continue

                class_id = mask_data[0]
                points = mask_data[1:]

                if len(points) < 6 or len(points) % 2 != 0:  # Need at least 3 points
                    continue

                # Create polygon points
                poly_points = []
                for j in range(0, len(points), 2):
                    poly_points.append([points[j], points[j + 1]])

                # Convert to numpy array for point in polygon test
                if len(poly_points) >= 3:
                    poly_points = np.array(poly_points, dtype=np.int32)
                    # Check if point is inside polygon
                    if cv2.pointPolygonTest(poly_points, (img_x, img_y), False) >= 0:
                        target_idx = i
                        break

        # If no mask contains the point or no masks exist, use bounding box method
        if target_idx is None:
            # Calculate distance to each box center
            min_distance = float('inf')
            nearest_idx = None

            for i, box_data in enumerate(boxes):
                # Box format: [x1, y1, x2, y2, conf, class_id]
                if len(box_data) >= 4:
                    x1, y1, x2, y2 = box_data[0], box_data[1], box_data[2], box_data[3]
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    distance = ((img_x - center_x) ** 2 + (img_y - center_y) ** 2) ** 0.5

                    if distance < min_distance:
                        min_distance = distance
                        nearest_idx = i

            # If nearest distance is less than threshold
            if min_distance < 50:
                target_idx = nearest_idx

        return target_idx

    def extract_single_label(self, results_label, box_idx):
        """
        Extract a single object's label data from results_label by index

        :param results_label: Original label dictionary
        :param box_idx: Index of the box to extract
        :return: New label dictionary containing only the selected object
        """
        new_label = {
            "file_path": results_label.get("file_path", ""),
            "boxes": [],
            "masks": [],
            "keypoints": [],
            "obb": [],
            "names": results_label.get("names", {})
        }

        # Copy the selected box
        if "boxes" in results_label and box_idx < len(results_label["boxes"]):
            new_label["boxes"].append(results_label["boxes"][box_idx])

        # Copy the corresponding mask if exists
        if "masks" in results_label and box_idx < len(results_label["masks"]):
            new_label["masks"].append(results_label["masks"][box_idx])

        # Copy the corresponding keypoints if exists
        if "keypoints" in results_label and box_idx < len(results_label["keypoints"]):
            new_label["keypoints"].append(results_label["keypoints"][box_idx])

        # Copy the corresponding obb if exists
        if "obb" in results_label and box_idx < len(results_label["obb"]):
            new_label["obb"].append(results_label["obb"][box_idx])

        return new_label

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
        """Measure 2D object information using label dictionary format"""
        if self.img[0] not in self.yolo_results:
            return
        self.update_image(img)
        results_label = self.yolo_results[self.img[0]]

        # Get bounding box coordinates
        if "boxes" in results_label and results_label["boxes"] is not None:
            boxes = results_label["boxes"]
            if box_idx < len(boxes):
                box_data = boxes[box_idx]
                # Box format: [x1, y1, x2, y2, conf, class_id]
                x1, y1, x2, y2 = box_data[0], box_data[1], box_data[2], box_data[3]
                width = x2 - x1
                height = y2 - y1
                bbox_area = width * height

                # Get class information
                class_id = int(box_data[5]) if len(box_data) > 5 else 0
                class_name = "Unknown"
                if "names" in results_label:
                    class_name = results_label["names"].get(class_id, f"class_{class_id}")
                elif hasattr(self.parent, 'yolo_model') and hasattr(self.parent.yolo_model, 'names'):
                    class_name = self.parent.yolo_model.names.get(class_id, f"class_{class_id}")

                # Calculate confidence
                confidence = box_data[4] if len(box_data) > 4 else 0.0

                # Calculate mask area (if mask exists)
                mask_area = 0
                has_mask = False
                if "masks" in results_label and box_idx < len(results_label["masks"]):
                    has_mask = True
                    mask_data = results_label["masks"][box_idx]
                    # Calculate approximate mask area by counting points
                    if len(mask_data) > 1:
                        points = mask_data[1:]  # Skip class_id
                        if len(points) >= 6 and len(points) % 2 == 0:
                            # Create a mask from polygon points
                            img_h, img_w = self.img[1].shape[:2]
                            mask = np.zeros((img_h, img_w), dtype=np.uint8)
                            poly_points = []
                            for i in range(0, len(points), 2):
                                poly_points.append([int(points[i]), int(points[i + 1])])
                            if len(poly_points) >= 3:
                                poly_points = np.array(poly_points, dtype=np.int32)
                                cv2.fillPoly(mask, [poly_points], 1)
                                mask_area = np.count_nonzero(mask)

                # Get scale information (if exists)
                dx = getattr(self, 'dx', 1.0)
                dy = getattr(self, 'dy', 1.0)

                # Calculate scaled area
                scaled_bbox_area = bbox_area * dx * dy
                scaled_mask_area = mask_area * dx * dy if has_mask else 0

                # Build display information
                info_text = f"Object Class: {class_name}\n"
                info_text += f"Confidence: {confidence:.2f}\n"
                info_text += f"Bounding Box: ({x1:.1f}, {y1:.1f}) - ({x2:.1f}, {y2:.1f})\n"
                info_text += f"Width: {width:.1f} pixels ({width * dx:.1f} u)\n"
                info_text += f"Height: {height:.1f} pixels ({height * dy:.1f} u)\n"
                info_text += f"Bounding Box Area: {bbox_area:.1f} pixels²\n"

                if has_mask:
                    info_text += f"Mask Area: {mask_area:.1f} pixels²\n"

                # Add scale information
                info_text += f"Scale Factor: dx={dx:.3f}, dy={dy:.3f}\n"
                info_text += f"Scaled Bounding Box Area: {scaled_bbox_area:.3f} units²\n"
                if has_mask:
                    info_text += f"Scaled Mask Area: {scaled_mask_area:.3f} units²\n"

                # Display information dialog
                msg_box = QtWidgets.QMessageBox(self.parent)
                msg_box.setWindowTitle("2D Object Measurement Information")
                msg_box.setText(info_text)
                msg_box.finished.connect(self.load_image)
                msg_box.exec_()

    def measure_3d_object_info(self, img, box_idx):
        """Measure 3D object information using label dictionary format"""
        # Find targets containing same area in all images
        target_boxes = []  # Store matching target boxes from all images

        # Get current image target box coordinates
        if self.img[0] not in self.yolo_results:
            return

        self.update_image(img)
        current_results_label = self.yolo_results[self.img[0]]
        if "boxes" not in current_results_label or not current_results_label["boxes"]:
            return

        current_boxes = current_results_label["boxes"]
        if box_idx >= len(current_boxes):
            return

        # Get current target box
        current_box = current_boxes[box_idx]
        x1, y1, x2, y2 = current_box[0], current_box[1], current_box[2], current_box[3]

        # Find matching targets in all images
        for file_path in self.parent.files_dock.file_paths:
            if file_path in self.yolo_results:
                results_label = self.yolo_results[file_path]
                if "boxes" in results_label and results_label["boxes"]:
                    boxes = results_label["boxes"]
                    # Find targets overlapping with current target
                    for i, box in enumerate(boxes):
                        # Simple overlap check
                        box_x1, box_y1, box_x2, box_y2 = box[0], box[1], box[2], box[3]
                        if self.boxes_overlap((x1, y1, x2, y2), (box_x1, box_y1, box_x2, box_y2)):
                            target_boxes.append({
                                'file_path': file_path,
                                'box_index': i,
                                'box_coords': box,
                                'results_label': results_label
                            })
                            break  # Take only one matching target per image

        if not target_boxes:
            QtWidgets.QMessageBox.warning(self.parent, "Measurement Information",
                                          "No matching targets found in other images")
            return

        # Calculate 3D measurement information
        # Area calculation
        areas = []
        mask_areas = []  # Store mask areas
        has_masks = False

        for target in target_boxes:
            box_data = target['box_coords']
            x1, y1, x2, y2 = box_data[0], box_data[1], box_data[2], box_data[3]
            area = (x2 - x1) * (y2 - y1)
            areas.append(area)

            # If mask exists, calculate mask area
            results_label = target['results_label']
            if "masks" in results_label:
                has_masks = True
                masks = results_label["masks"]
                box_index = target['box_index']
                if box_index < len(masks):
                    mask_data = masks[box_index]
                    # Calculate approximate mask area
                    if len(mask_data) > 1:
                        points = mask_data[1:]  # Skip class_id
                        if len(points) >= 6 and len(points) % 2 == 0:
                            # Create a mask from polygon points
                            img_h, img_w = self.img[1].shape[:2]  # Use current image shape as approximation
                            mask = np.zeros((img_h, img_w), dtype=np.uint8)
                            poly_points = []
                            for i in range(0, len(points), 2):
                                poly_points.append([int(points[i]), int(points[i + 1])])
                            if len(poly_points) >= 3:
                                poly_points = np.array(poly_points, dtype=np.int32)
                                cv2.fillPoly(mask, [poly_points], 1)
                                mask_area = np.count_nonzero(mask)
                                mask_areas.append(mask_area)
                            else:
                                mask_areas.append(0)
                        else:
                            mask_areas.append(0)
                    else:
                        mask_areas.append(0)
                else:
                    mask_areas.append(0)
            else:
                mask_areas.append(0)

        min_area = min(areas) if areas else 0
        max_area = max(areas) if areas else 0
        avg_area = sum(areas) / len(areas) if areas else 0

        min_mask_area = min(mask_areas) if mask_areas else 0
        max_mask_area = max(mask_areas) if mask_areas else 0
        avg_mask_area = sum(mask_areas) / len(mask_areas) if mask_areas else 0

        # Number of layers is number of found targets
        layers = len(target_boxes)

        # Get scale information (if exists)
        dx = getattr(self, 'dx', 1.0)
        dy = getattr(self, 'dy', 1.0)
        dz = getattr(self, 'dz', 1.0)

        # Volume estimation (average area × layers × dz)
        volume_bbox = avg_area * layers * dx * dy * dz
        volume_mask = avg_mask_area * layers * dx * dy * dz if has_masks else 0

        # Get class information
        class_name = "Unknown"
        if target_boxes:
            first_target = target_boxes[0]
            results_label = first_target['results_label']
            box_index = first_target['box_index']
            if "boxes" in results_label and box_index < len(results_label["boxes"]):
                box_data = results_label["boxes"][box_index]
                if len(box_data) > 5:  # Has class_id
                    class_id = int(box_data[5])
                    if "names" in results_label:
                        class_name = results_label["names"].get(class_id, f"class_{class_id}")
                    elif hasattr(self.parent, 'yolo_model') and hasattr(self.parent.yolo_model, 'names'):
                        class_name = self.parent.yolo_model.names.get(class_id, f"class_{class_id}")

        # Build display information
        info_text = f"Object Class: {class_name}\n"
        info_text += f"Layers: {layers}\n"
        info_text += f"Bounding Box Area Range: {min_area:.1f} - {max_area:.1f} pixels²\n"
        info_text += f"Average Bounding Box Area: {avg_area:.1f} pixels²\n"

        if has_masks:
            info_text += f"Mask Area Range: {min_mask_area:.1f} - {max_mask_area:.1f} pixels²\n"
            info_text += f"Average Mask Area: {avg_mask_area:.1f} pixels²\n"

        # Add scale information
        info_text += f"Scale Factor: dx={dx:.3f}, dy={dy:.3f}, dz={dz:.3f}\n"
        info_text += f"Estimated Volume (Bounding Box): {volume_bbox:.3f} units³\n"
        if has_masks:
            info_text += f"Estimated Volume (Mask): {volume_mask:.3f} units³\n"

        # Display information dialog
        msg_box = QtWidgets.QMessageBox(self.parent)
        msg_box.setWindowTitle("3D Object Measurement Information")
        msg_box.setText(info_text)
        msg_box.finished.connect(self.load_image)
        msg_box.exec_()

    def total_2d_info(self):
        """
        Statistics of all 2D targets in current image, including area-related information
        And display measurement results, supporting class filtering
        """
        if self.img[0] not in self.yolo_results:
            return

        results_label = self.yolo_results[self.img[0]]

        # Get bounding box coordinates
        if "boxes" in results_label and results_label["boxes"] is not None:
            boxes = results_label["boxes"]

            # Get selected class list
            selected_classes = []
            if hasattr(self.parent, 'yolo_dock') and self.parent.yolo_dock and \
                    hasattr(self.parent.yolo_dock, 'get_selected_classes'):
                classes = self.parent.yolo_dock.get_selected_classes()
                if "names" in results_label and hasattr(self.parent.plotter, 'index'):
                    index = self.parent.plotter.index
                    selected_classes = [int(index[name]) for name in classes if name in index]

            # Initialize statistics variables
            total_objects = 0
            total_bbox_area = 0
            total_mask_area = 0
            has_masks = "masks" in results_label and results_label["masks"] is not None

            # Get scale information (if exists)
            dx = getattr(self, 'dx', 1.0)
            dy = getattr(self, 'dy', 1.0)

            # Statistics information of all targets
            for i, box_data in enumerate(boxes):
                # Check if it's a selected class
                class_id = int(box_data[5]) if len(box_data) > 5 else i
                if selected_classes and class_id not in selected_classes:
                    continue  # Skip unselected classes

                total_objects += 1
                x1, y1, x2, y2 = box_data[0], box_data[1], box_data[2], box_data[3]
                width = x2 - x1
                height = y2 - y1
                bbox_area = width * height
                total_bbox_area += bbox_area

                # Calculate mask area (if mask exists)
                if has_masks and "masks" in results_label and i < len(results_label["masks"]):
                    mask_data = results_label["masks"][i]
                    # Calculate approximate mask area
                    if len(mask_data) > 1:
                        points = mask_data[1:]  # Skip class_id
                        if len(points) >= 6 and len(points) % 2 == 0:
                            # Create a mask from polygon points
                            img_h, img_w = self.img[1].shape[:2]
                            mask = np.zeros((img_h, img_w), dtype=np.uint8)
                            poly_points = []
                            for j in range(0, len(points), 2):
                                poly_points.append([int(points[j]), int(points[j + 1])])
                            if len(poly_points) >= 3:
                                poly_points = np.array(poly_points, dtype=np.int32)
                                cv2.fillPoly(mask, [poly_points], 1)
                                mask_area = np.count_nonzero(mask)
                                total_mask_area += mask_area

            # If no objects are selected, give prompt
            if total_objects == 0:
                if selected_classes:
                    QtWidgets.QMessageBox.information(self.parent, "Prompt", "No targets found in selected classes")
                else:
                    QtWidgets.QMessageBox.information(self.parent, "Prompt", "No targets found")
                return

            # Calculate scaled area
            scaled_total_bbox_area = total_bbox_area * dx * dy
            scaled_total_mask_area = total_mask_area * dx * dy if has_masks else 0

            # Display measurement results
            info_text = f"Total Objects: {total_objects}\n"
            info_text += f"Total Bounding Box Area: {total_bbox_area} pixels²\n"

            if has_masks:
                info_text += f"Total Mask Area: {total_mask_area} pixels²\n"

            # Add scale information
            info_text += f"Scale Factor: dx={dx:.3f}, dy={dy:.3f}\n"
            info_text += f"Scaled Total Bounding Box Area: {scaled_total_bbox_area:.3f} units²\n"
            if has_masks:
                info_text += f"Scaled Total Mask Area: {scaled_total_mask_area:.3f} units²\n"

            # Display information dialog
            msg_box = QtWidgets.QMessageBox(self.parent)
            msg_box.setWindowTitle("2D Object Total Measurement Information")
            msg_box.setText(info_text)
            msg_box.exec_()

    def total_3d_info(self):
        """
        Statistics of 3D targets in all images, including area and volume-related information
        And display measurement results, supporting class filtering
        """
        # Statistics targets in all images
        total_objects = 0
        total_layers = 0
        total_bbox_area = 0
        total_mask_area = 0
        has_masks = False

        # Get selected class list
        selected_classes = self.parent.yolo_dock.get_selected_classes() if self.parent.annos_dock.show_filtered else None

        # Get scale information (if exists)
        dx = getattr(self, 'dx', 1.0)
        dy = getattr(self, 'dy', 1.0)
        dz = getattr(self, 'dz', 1.0)

        # Iterate through results of all images
        for file_path in self.parent.files_dock.file_paths:
            if file_path in self.yolo_results:
                results_label = self.yolo_results[file_path]
                if "boxes" in results_label and results_label["boxes"] is not None:
                    boxes = results_label["boxes"]

                    # Build class index mapping if needed
                    class_index_map = {}
                    if "names" in results_label and hasattr(self.parent.plotter, 'index'):
                        class_index_map = self.parent.plotter.index

                    layer_object_count = 0
                    # Statistics targets in each layer that meet class conditions
                    for i, box_data in enumerate(boxes):
                        # Check if it's a selected class
                        class_id = int(box_data[5]) if len(box_data) > 5 else i

                        # Check if class is in selected classes
                        class_selected = True
                        if selected_classes and len(selected_classes) > 0:
                            class_selected = False
                            class_name = results_label["names"].get(class_id,
                                                                    f"class_{class_id}") if "names" in results_label else f"class_{class_id}"
                            # Check if class name is in selected classes
                            if class_name in selected_classes:
                                class_selected = True

                        if not class_selected:
                            continue  # Skip unselected classes

                        layer_object_count += 1
                        total_objects += 1

                        x1, y1, x2, y2 = box_data[0], box_data[1], box_data[2], box_data[3]
                        bbox_area = (x2 - x1) * (y2 - y1)
                        total_bbox_area += bbox_area

                        # If mask exists, calculate mask area
                        if "masks" in results_label and results_label["masks"] is not None:
                            has_masks = True
                            masks = results_label["masks"]
                            if i < len(masks):
                                mask_data = masks[i]
                                # Calculate approximate mask area
                                if len(mask_data) > 1:
                                    points = mask_data[1:]  # Skip class_id
                                    if len(points) >= 6 and len(points) % 2 == 0:
                                        # Create a mask from polygon points
                                        img_h, img_w = self.img[1].shape[:2]  # Approximate with current image size
                                        mask = np.zeros((img_h, img_w), dtype=np.uint8)
                                        poly_points = []
                                        for j in range(0, len(points), 2):
                                            poly_points.append([int(points[j]), int(points[j + 1])])
                                        if len(poly_points) >= 3:
                                            poly_points = np.array(poly_points, dtype=np.int32)
                                            cv2.fillPoly(mask, [poly_points], 1)
                                            mask_area = np.count_nonzero(mask)
                                            total_mask_area += mask_area

                    # Only count layer if it has targets meeting class conditions
                    if layer_object_count > 0:
                        total_layers += 1

        if total_objects == 0:
            if selected_classes and len(selected_classes) > 0:
                QtWidgets.QMessageBox.warning(self.parent, "Measurement Information",
                                              "No targets found in selected classes")
            else:
                QtWidgets.QMessageBox.warning(self.parent, "Measurement Information", "No targets found")
            return

        # Volume estimation (total average area × layers × dz)
        avg_bbox_area = total_bbox_area / total_objects if total_objects > 0 else 0
        avg_mask_area = total_mask_area / total_objects if total_objects > 0 and has_masks else 0
        volume_bbox = avg_bbox_area * total_layers * dx * dy * dz
        volume_mask = avg_mask_area * total_layers * dx * dy * dz if has_masks else 0

        # Display measurement results
        info_text = f"Total Objects: {total_objects}\n"
        info_text += f"Total Layers: {total_layers}\n"
        info_text += f"Total Bounding Box Area: {total_bbox_area} pixels²\n"
        info_text += f"Average Bounding Box Area: {avg_bbox_area} pixels²\n"

        if has_masks:
            info_text += f"Total Mask Area: {total_mask_area} pixels²\n"
            info_text += f"Average Mask Area: {avg_mask_area} pixels²\n"

        # Add scale information
        info_text += f"Scale Factor: dx={dx:.3f}, dy={dy:.3f}, dz={dz:.3f}\n"
        info_text += f"Estimated Total Volume (Bounding Box): {volume_bbox:.3f} units³\n"
        if has_masks:
            info_text += f"Estimated Total Volume (Mask): {volume_mask:.3f} units³\n"

        # Display information dialog
        msg_box = QtWidgets.QMessageBox(self.parent)
        msg_box.setWindowTitle("3D Object Total Measurement Information")
        msg_box.setText(info_text)
        msg_box.exec_()

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
