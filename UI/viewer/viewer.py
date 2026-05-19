import os
import json

import numpy as np
import torch
import xml.etree.ElementTree as ET
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt
from UI.tools.tools import get_image_format_name
from UI.tools.utils import get_img_color
from UI.tools.tool_plot_yolo import *
from UI.control.config import dx, dy, dz
from ultralytics.engine.results import Results
from ultralytics.engine.results import Boxes, Masks, Keypoints, OBB


class Viewer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Image Viewer")
        self.resize(640, 480)
        self.dx, self.dy, self.dz = dx, dy, dz
        self.threshold = 0.5

        # Create QGraphicsView and QGraphicsScene
        self.graphics_view = QtWidgets.QGraphicsView(self)
        self.graphics_scene = QtWidgets.QGraphicsScene(self)
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setRenderHint(QtGui.QPainter.Antialiasing)

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.graphics_view)

        self.switch_display_btn = QtWidgets.QLabel("1", self.graphics_view)
        self.switch_display_btn.setStyleSheet("""
            font-size: 20px;
            color: grey;
            background-color: rgba(255, 255, 255, 180);
            border-radius: 10px;
            padding: 2px 6px;
        """)
        self.switch_display_btn.setCursor(Qt.PointingHandCursor)
        self.switch_display_btn.setAlignment(Qt.AlignCenter)
        self.switch_display_btn.mousePressEvent = self.on_switch_display_click
        self.switch_display_btn.hide()

        # Image container
        self.pixmap_item = None
        # self.mask = None
        self.img = None
        self.show_label = False
        self.show_results = False
        self.show_detect_results = False
        self.load_yolo_results = False
        self.show_yolo_point_results = False
        self.default_save_path = None
        self.mask_opacity = 0.5  # Mask opacity
        self.label_file_path = None

        # Point detection related properties
        self.point_detection_mode = False
        self.last_click_point = None
        self.image_cache = {}  # Cache loaded images
        self.label_cache = {}
        self.yolo_cache = {}

        # YOLO model related properties
        self.yolo_mode = 'detect'
        self.yolo_results = {}  # Store YOLO detection results

        # Mouse interaction variables
        self.mouse_pressed = False
        self.ctrl_pressed = False
        self.last_mouse_pos = None

        # Multi-image display control
        self.display_modes = [1, 2, 4, 8]
        self.current_mode_index = 0  # Default to 1 image
        self.pixmap_items = []  # Store multiple pixmap items

        # Properties for displaying detection area box
        self.patch_size = 320  # Default detection area size
        self.patch_rect_item = None  # Graphics item for displaying detection area box
        self.patch_hide_timer = None

        self.graphics_view.wheelEvent = self.wheelEvent
        self.graphics_view.mousePressEvent = self.mousePressEvent
        self.graphics_view.mouseMoveEvent = self.mouseMoveEvent
        self.graphics_view.mouseReleaseEvent = self.mouseReleaseEvent

    def on_context_menu(self, point):
        pass

    def update_patch_rect(self, patch_size_percent):
        """
        Update detection area box size (by image ratio)
        :param patch_size_percent: Detection area percentage of image size (10-100)
        """
        if not self.pixmap_item or not self.point_detection_mode:
            return

        pixmap = self.pixmap_item.pixmap()
        if pixmap.isNull():
            return

        img_width = pixmap.width()
        img_height = pixmap.height()

        patch_size = int(min(img_width, img_height) * patch_size_percent / 100)
        patch_size = min(patch_size, img_width, img_height)

        if self.patch_rect_item is None:
            self.patch_rect_item = QtWidgets.QGraphicsRectItem()
            self.patch_rect_item.setPen(QtGui.QPen(QtCore.Qt.red, 3, QtCore.Qt.DashLine))
            self.graphics_scene.addItem(self.patch_rect_item)

        x = (img_width - patch_size) / 2
        y = (img_height - patch_size) / 2

        self.patch_rect_item.setRect(x, y, patch_size, patch_size)
        self.patch_rect_item.setZValue(1000)
        self.patch_rect_item.show()

    def update_display_layout(self):
        if not self.pixmap_item:
            return
        pixmap = self.pixmap_item.pixmap()
        if pixmap.isNull():
            return

        width = pixmap.width()
        height = pixmap.height()

        # Clear all image items
        for item in self.pixmap_items:
            self.graphics_scene.removeItem(item)
        self.pixmap_items.clear()

        current_mode = self.display_modes[self.current_mode_index]
        cols = int(current_mode ** 0.5)
        rows = (current_mode + cols - 1) // cols

        # Add multiple pixmap items
        for i in range(current_mode):
            item = self.graphics_scene.addPixmap(pixmap)
            x = (i % cols) * width
            y = (i // cols) * height
            item.setPos(x, y)
            self.pixmap_items.append(item)

        # Update scene rect and fit to view
        new_rect = QtCore.QRectF(0, 0, cols * width, rows * height)
        self.graphics_scene.setSceneRect(new_rect)
        self.graphics_view.fitInView(new_rect, Qt.KeepAspectRatio)

    def update_image(self, img):
        """Update displayed image with point detection results"""
        if len(img.shape) == 2:  # Grayscale
            height, width = img.shape
            bytes_per_line = width
            q_image = QtGui.QImage(img.data, width, height, bytes_per_line, QtGui.QImage.Format_Grayscale8)
        else:  # Color image
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            height, width, channel = img.shape
            bytes_per_line = 3 * width
            q_image = QtGui.QImage(img.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888)

        fmt = get_image_format_name(q_image.format())
        pixmap = QtGui.QPixmap.fromImage(q_image)

        self.graphics_scene.removeItem(self.pixmap_item)
        self.pixmap_item = self.graphics_scene.addPixmap(pixmap)
        self.graphics_scene.setSceneRect(QtCore.QRectF(pixmap.rect()))
        return fmt

    def load_aval_mask(self, img, mask, opacity):
        if mask.shape[:2] != img.shape[:2]:
            mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
        mask = get_img_color(mask, 3 + self.parent.plotter.offset)
        annotated_img = cv2.addWeighted(img, opacity, mask, 1 - opacity, 0)
        img[mask > 0] = annotated_img[mask > 0]
        # mask = np.squeeze(mask)
        # img[mask != 0] = 0
        return True, img

    def load_mask(self, img, file_path, reverse=False):
        if os.path.exists(file_path):
            mask = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
            if mask is None:
                return False, img
            if reverse:
                return self.load_aval_mask(img, ~mask, self.mask_opacity)
            else:
                return self.load_aval_mask(img, mask, self.mask_opacity)
        else:
            return False, img

    def load_label_file_txt(self, img, file_path):
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            boxes_data = []
            masks_data = []
            keypoints_data = []
            obb_data = []
            height, width = img.shape[:2]

            for line_num, line in enumerate(lines, 1):
                parts = line.strip().split()
                if len(parts) < 5:
                    continue

                try:
                    class_id = int(parts[0])
                    task = self.parent.annos_dock.get_current_task_type()

                    if len(parts) >= 49 and task == "pose":
                        self.parent.annos_dock.update_task_type(3)
                        keypoints = []
                        for i in range(1, len(parts), 3):
                            if i + 2 < len(parts):
                                x = float(parts[i]) * width
                                y = float(parts[i + 1]) * height
                                conf = float(parts[i + 2])
                                keypoints.append([x, y, conf])

                        if len(keypoints) > 0:
                            valid_points = [kp for kp in keypoints if kp[2] > 0]
                            if len(valid_points) > 0:
                                x_coords = [kp[0] for kp in valid_points]
                                y_coords = [kp[1] for kp in valid_points]
                                x_min, x_max = min(x_coords), max(x_coords)
                                y_min, y_max = min(y_coords), max(y_coords)

                                boxes_data.append([
                                    x_min, y_min, x_max, y_max, 1.0, class_id
                                ])
                                keypoints_data.append(keypoints)

                    elif len(parts) == 9 and task == "obb":
                        self.parent.annos_dock.update_task_type(2)
                        obb_coords = [float(x) for x in parts[1:]]
                        if len(obb_coords) == 8:
                            obb_abs_coords = []
                            for i, coord in enumerate(obb_coords):
                                if i % 2 == 0:
                                    obb_abs_coords.append(coord * width)
                                else:
                                    obb_abs_coords.append(coord * height)

                            obb_data.append([class_id] + obb_abs_coords)

                            x_coords = obb_abs_coords[::2]
                            y_coords = obb_abs_coords[1::2]
                            boxes_data.append([
                                min(x_coords), min(y_coords),
                                max(x_coords), max(y_coords),
                                1.0, class_id
                            ])
                    elif len(parts) >= 5 and task == "detect" or 5 <= len(parts) < 7:
                        self.parent.annos_dock.update_task_type(0)
                        seg_points = [float(x) for x in parts[1:]]
                        if len(seg_points) >= 6 and len(seg_points) % 2 == 0:
                            abs_points = []
                            for i, coord in enumerate(seg_points):
                                if i % 2 == 0:
                                    abs_points.append(coord * width)
                                else:
                                    abs_points.append(coord * height)

                            x_coords = abs_points[::2]
                            y_coords = abs_points[1::2]
                            box = [min(x_coords), min(y_coords),
                                   max(x_coords), max(y_coords), 1.0, class_id]
                            boxes_data.append(box)

                            x_center = (box[0] + box[2]) / 2
                            y_center = (box[1] + box[3]) / 2
                            box_width = box[2] - box[0]
                            box_height = box[3] - box[1]

                            if box_width <= 0 or box_height <= 0:
                                print(
                                    f"Warning: Label file {file_path} line {line_num} bounding box size is zero or negative")
                                continue
                        else:
                            x_center = float(parts[1]) * width
                            y_center = float(parts[2]) * height
                            box_width = float(parts[3]) * width
                            box_height = float(parts[4]) * height

                            if box_width <= 0 or box_height <= 0:
                                print(
                                    f"Warning: Label file {file_path} line {line_num} bounding box size is zero or negative")
                                continue

                            boxes_data.append([
                                (x_center - box_width / 2),
                                (y_center - box_height / 2),
                                (x_center + box_width / 2),
                                (y_center + box_height / 2),
                                1.0,
                                class_id
                            ])

                    elif len(parts) >= 7:
                        self.parent.annos_dock.update_task_type(1)
                        seg_points = [float(x) for x in parts[1:]]
                        if len(seg_points) >= 6 and len(seg_points) % 2 == 0:
                            abs_points = []
                            for i, coord in enumerate(seg_points):
                                if i % 2 == 0:
                                    abs_points.append(coord * width)
                                else:
                                    abs_points.append(coord * height)

                            x_coords = abs_points[::2]
                            y_coords = abs_points[1::2]
                            boxes_data.append([
                                min(x_coords), min(y_coords),
                                max(x_coords), max(y_coords),
                                1.0, class_id
                            ])

                            masks_data.append([class_id] + abs_points)

                except ValueError as ve:
                    print(f"Warning: Label file {file_path} line {line_num} data format error: {ve}")
                    continue

            if boxes_data or masks_data or keypoints_data or obb_data:
                yolo_labels = {"file_path": file_path, "boxes": boxes_data, "masks": masks_data,
                               "keypoints": keypoints_data, "obb": obb_data, "names": {}}
                img = self.show_annotations_with_results(img, yolo_labels)
                return True, yolo_labels
            else:
                return False, None

        except FileNotFoundError:
            print(f"Error: Cannot find label file {file_path}")
            return False, img
        except Exception as e:
            print(f"Error: Exception occurred while loading label file {file_path}: {e}")
            return False, img

    def load_label_file_json(self, img, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            boxes_data = []
            masks_data = []
            keypoints_data = []
            obb_data = []
            names = {}
            class_id = 0
            height, width = img.shape[:2]

            # Process COCO format keypoint annotations
            if "annotations" in data and "categories" in data:
                cat_id_to_name = {cat["id"]: cat["name"] for cat in data["categories"]}

                for ann in data["annotations"]:
                    class_id = ann.get("category_id", 0)
                    class_name = cat_id_to_name.get(class_id, f"class_{class_id}")

                    if class_name not in names.values():
                        names[len(names)] = class_name

                    local_class_id = 0
                    for cid, cname in names.items():
                        if cname == class_name:
                            local_class_id = cid
                            break

                    if "bbox" in ann:
                        bbox = ann["bbox"]
                        x, y, box_width, box_height = bbox
                        boxes_data.append([
                            x, y, x + box_width, y + box_height,
                            1.0, local_class_id
                        ])

                    if "segmentation" in ann:
                        seg = ann["segmentation"]
                        if isinstance(seg, list) and len(seg) > 0:
                            if isinstance(seg[0], list):
                                for polygon in seg:
                                    if len(polygon) >= 6:
                                        abs_polygon = []
                                        for i in range(0, len(polygon), 2):
                                            abs_polygon.append(polygon[i])
                                            abs_polygon.append(polygon[i + 1])
                                        masks_data.append([local_class_id] + abs_polygon)
                            elif isinstance(seg, dict):
                                pass

                    if "keypoints" in ann:
                        kps = ann["keypoints"]
                        if len(kps) % 3 == 0:
                            keypoints = []
                            for i in range(0, len(kps), 3):
                                keypoints.append([
                                    kps[i],
                                    kps[i + 1],
                                    kps[i + 2]
                                ])
                            keypoints_data.append(keypoints)

            # Process LabelMe format
            elif "shapes" in data:
                shapes = data["shapes"]
                for shape in shapes:
                    label = shape.get("label", "0")
                    if label not in names.values():
                        names[class_id] = label
                        class_id += 1

                    local_class_id = 0
                    for cid, cname in names.items():
                        if cname == label:
                            local_class_id = cid
                            break

                    points = shape.get("points", [])
                    if len(points) < 2:
                        continue

                    shape_type = shape.get("shape_type", "polygon")

                    if shape_type == "rectangle":
                        if len(points) == 2:
                            x_coords = [p[0] for p in points]
                            y_coords = [p[1] for p in points]
                            x_min, x_max = min(x_coords), max(x_coords)
                            y_min, y_max = min(y_coords), max(y_coords)

                            boxes_data.append([
                                x_min, y_min, x_max, y_max,
                                1.0, local_class_id
                            ])

                    elif shape_type == "polygon":
                        if len(points) >= 3:
                            abs_points = []
                            for p in points:
                                abs_points.append(p[0])
                                abs_points.append(p[1])

                            x_coords = abs_points[::2]
                            y_coords = abs_points[1::2]
                            boxes_data.append([
                                min(x_coords), min(y_coords),
                                max(x_coords), max(y_coords),
                                1.0, local_class_id
                            ])

                            masks_data.append([local_class_id] + abs_points)

                    elif shape_type == "point":
                        if len(points) == 1:
                            keypoints_data.append([[points[0][0], points[0][1], 2]])

            if boxes_data or masks_data or keypoints_data or obb_data:
                yolo_labels = {"file_path": file_path, "boxes": boxes_data, "masks": masks_data,
                               "keypoints": keypoints_data, "obb": obb_data, "names": names}
                img = self.show_annotations_with_results(img, yolo_labels)
                return True, yolo_labels
            else:
                return False, None

        except FileNotFoundError:
            print(f"Error: Cannot find JSON label file {file_path}")
            return False, img
        except json.JSONDecodeError as e:
            print(f"Error: JSON label file {file_path} format error: {e}")
            return False, img
        except Exception as e:
            print(f"Error: Exception occurred while loading JSON label file {file_path}: {e}")
            return False, img

    def load_label_file_xml(self, img, file_path):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            boxes_data = []
            masks_data = []
            keypoints_data = []
            obb_data = []
            names = {}
            height, width = img.shape[:2]

            size = root.find('size')
            if size is None:
                print(f"Warning: XML label file {file_path} missing image size information")
                return False, img

            try:
                img_w = int(size.find('width').text)
                img_h = int(size.find('height').text)
            except (AttributeError, ValueError, TypeError) as e:
                print(f"Warning: XML label file {file_path} invalid image size information: {e}")
                return False, img

            objects = root.findall('object')
            if not objects:
                print(f"Warning: No object labels found in XML label file {file_path}")
                return False, img

            for obj_idx, obj in enumerate(objects):
                try:
                    name_elem = obj.find('name')
                    class_name = "0"
                    if name_elem is not None and name_elem.text is not None:
                        class_name = name_elem.text

                    if class_name not in names.values():
                        names[len(names)] = class_name

                    class_id = 0
                    for cid, cname in names.items():
                        if cname == class_name:
                            class_id = cid
                            break

                    bndbox = obj.find('bndbox')
                    if bndbox is None:
                        print(f"Warning: XML label file {file_path} object {obj_idx} missing bounding box information")
                        continue

                    xmin_elem = bndbox.find('xmin')
                    ymin_elem = bndbox.find('ymin')
                    xmax_elem = bndbox.find('xmax')
                    ymax_elem = bndbox.find('ymax')

                    if not all([xmin_elem, ymin_elem, xmax_elem, ymax_elem]):
                        print(
                            f"Warning: XML label file {file_path} object {obj_idx} incomplete bounding box coordinates")
                        continue

                    xmin = float(xmin_elem.text)
                    ymin = float(ymin_elem.text)
                    xmax = float(xmax_elem.text)
                    ymax = float(ymax_elem.text)

                    if xmin < 0 or ymin < 0 or xmax > img_w or ymax > img_h or xmin >= xmax or ymin >= ymax:
                        print(f"Warning: XML label file {file_path} object {obj_idx} invalid bounding box coordinates")
                        continue

                    boxes_data.append([
                        xmin, ymin, xmax, ymax, 1.0, class_id
                    ])

                except (AttributeError, ValueError, TypeError) as e:
                    print(f"Warning: XML label file {file_path} object {obj_idx} data format error: {e}")
                    continue
                except Exception as e:
                    print(f"Warning: XML label file {file_path} object {obj_idx} processing exception: {e}")
                    continue

            if boxes_data or masks_data or keypoints_data or obb_data:
                yolo_labels = {"file_path": file_path, "boxes": boxes_data, "masks": masks_data,
                               "keypoints": keypoints_data, "obb": obb_data, "names": names}
                return True, yolo_labels
            else:
                return False, None

        except FileNotFoundError:
            print(f"Error: Cannot find XML label file {file_path}")
            return False, img
        except ET.ParseError as e:
            print(f"Error: XML label file {file_path} format error: {e}")
            return False, img
        except Exception as e:
            print(f"Error: Exception occurred while loading XML label file {file_path}: {e}")
            return False, img

    def show_annotations_with_results(self, img, yolo_labels):
        """
        Display various types of annotations using ultralytics Results and plot methods
        """
        try:
            selected_classes = self.parent.yolo_dock.get_selected_classes() if self.parent.annos_dock.show_filtered else None
            annotated_img = self.parent.plotter.process_mini(img, yolo_labels, selected_classes,
                                                             show_boxes=self.parent.annos_dock.show_boxes,
                                                             show_conf=self.parent.annos_dock.show_confidence,
                                                             show_labels=self.parent.annos_dock.show_labels)
            return annotated_img

        except Exception as e:
            print(f"Error displaying annotations with Results: {e}")
            import traceback
            traceback.print_exc()
            return img

    def result_to_label(self, results):
        """
        Convert Results object back to label format
        """
        if not isinstance(results, Results):
            return None

        file_path = results.path
        orig_shape = results.orig_shape
        names = results.names if hasattr(results, 'names') else {}

        boxes_data = []
        masks_data = []
        keypoints_data = []
        obb_data = []

        if hasattr(results, 'boxes') and results.boxes is not None:
            boxes = results.boxes.xyxy.data.cpu().numpy()
            cls = results.boxes.cls.data.cpu().numpy()
            conf = results.boxes.conf.data.cpu().numpy()

            for i, box in enumerate(boxes):
                boxes_data.append([
                    box[0],
                    box[1],
                    box[2],
                    box[3],
                    conf[i],
                    int(cls[i])
                ])

        if hasattr(results, 'masks') and results.masks is not None:
            masks = results.masks.xy
            for i, mask in enumerate(masks):
                class_id = int(results.boxes.data[i][5]) if results.boxes is not None and i < len(
                    results.boxes.data) else i
                polygon_points = mask.flatten().tolist()
                masks_data.append([class_id] + polygon_points)

        if hasattr(results, 'keypoints') and results.keypoints is not None:
            keypoints = results.keypoints.xy.data.cpu().numpy()

            for i, kps in enumerate(keypoints):
                keypoints_list = []
                for j, kp in enumerate(kps):
                    keypoints_list.extend([
                        kp[0],
                        kp[1],
                        results.keypoints.conf.data.cpu().numpy()[i][j]
                    ])
                keypoints_data.append(keypoints_list)

        if hasattr(results, 'obb') and results.obb is not None:
            obb = results.obb.xyxyxyxy.data.cpu().numpy()

            for i, obb_item in enumerate(obb):
                class_id = int(results.boxes.data[i][5]) if results.boxes is not None and i < len(
                    results.boxes.data) else i
                obb_coords = obb_item.flatten().tolist()
                obb_data.append([int(class_id)] + obb_coords)

        labels = {
            "file_path": file_path,
            "shape": orig_shape,
            "boxes": boxes_data,
            "masks": masks_data,
            "keypoints": keypoints_data,
            "obb": obb_data,
            "names": names
        }

        return labels

    def label_to_result(self, img, labels):
        file_path = labels.get("file_path")
        shape = labels.get("shape")
        boxes_data = labels.get("boxes", None)
        masks_data = labels.get("masks", None)
        keypoints_data = labels.get("keypoints", None)
        obb_data = labels.get("obb", None)
        names = labels.get("names", None)
        if file_path is None or shape is None:
            return None
        if not (boxes_data or masks_data or keypoints_data or obb_data):
            return None

        boxes_tensor = None
        masks_tensor = None
        keypoints_tensor = None

        if boxes_data and len(boxes_data) > 0:
            boxes_tensor = torch.tensor(boxes_data, dtype=torch.float32)

        if masks_data and len(masks_data) > 0:
            img_h, img_w = shape
            mask_list = []

            for mask_info in masks_data:
                if len(mask_info) < 3:
                    continue

                class_id = mask_info[0]
                points = mask_info[1:]

                if len(points) < 6 or len(points) % 2 != 0:
                    continue

                mask = np.zeros((img_h, img_w), dtype=np.uint8)

                abs_points = []
                for i in range(0, len(points), 2):
                    x = int(points[i])
                    y = int(points[i + 1])
                    x = max(0, min(x, img_w - 1))
                    y = max(0, min(y, img_h - 1))
                    abs_points.append([x, y])

                if len(abs_points) >= 3:
                    pts = np.array(abs_points, np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.fillPoly(mask, [pts], 1)
                    mask_list.append(mask)

            if mask_list:
                masks_tensor = torch.tensor(np.array(mask_list), dtype=torch.uint8)

        if keypoints_data and len(keypoints_data) > 0:
            kps_list = []
            for kps in keypoints_data:
                kps_list.append(kps)

            if kps_list:
                max_kps = max(len(kps) // 3 for kps in kps_list)
                padded_kps = []
                for kps in kps_list:
                    while len(kps) < max_kps * 3:
                        kps.extend([0, 0, 0])
                    padded_kps.append(kps)

                keypoints_tensor = torch.tensor(padded_kps, dtype=torch.float32).view(-1, max_kps, 3)

        if obb_data and len(obb_data) > 0:
            img_h, img_w = shape
            obb_list = []

            for obb_info in obb_data:
                if len(obb_info) < 9:
                    continue

                class_id = obb_info[0]
                points = obb_info[1:]

                if len(points) < 8 or len(points) % 2 != 0:
                    continue

                obb_points = []
                for i in range(0, len(points), 2):
                    x = points[i]
                    y = points[i + 1]
                    x = max(0, min(x, img_w - 1))
                    y = max(0, min(y, img_h - 1))
                    obb_points.extend([x, y])

                obb_list.append([int(class_id)] + obb_points)

            if obb_list:
                obb_tensor = torch.tensor(np.array(obb_list), dtype=torch.float32)

        if not names:
            if hasattr(self.parent, 'yolo_model') and hasattr(self.parent.yolo_model, 'names'):
                names = self.parent.yolo_model.names
            else:
                max_class_id = 0
                if boxes_tensor is not None:
                    max_class_id = max(max_class_id, int(boxes_tensor[:, 5].max().item()))
                names = {i: f"class_{i}" for i in range(max_class_id + 1)}

        result = Results(
            orig_img=img,
            path=file_path,
            names=names,
            boxes=boxes_tensor,
            masks=masks_tensor,
            keypoints=keypoints_tensor,
        )
        return result

    def merge_results(self, file_path, new_results):
        """
        Merge new detection results into existing yolo_results
        """
        try:
            if file_path in self.yolo_results:
                existing_results = self.yolo_results[file_path]

                if (hasattr(existing_results[0], 'boxes') and existing_results[0].boxes is not None and
                        hasattr(new_results[0], 'boxes') and new_results[0].boxes is not None):
                    merged_boxes_data = np.concatenate([
                        existing_results[0].boxes.data.cpu().numpy(),
                        new_results[0].boxes.data.cpu().numpy()
                    ], axis=0)
                    existing_results[0].boxes = Boxes(
                        torch.from_numpy(merged_boxes_data),
                        orig_shape=existing_results[0].orig_shape
                    )

                if (hasattr(existing_results[0], 'masks') and
                        hasattr(new_results[0], 'masks') and new_results[0].masks is not None):
                    merged_masks_data = np.concatenate([
                        existing_results[0].masks.data.cpu().numpy(),
                        new_results[0].masks.data.cpu().numpy()
                    ], axis=0)
                    existing_results[0].masks = Masks(
                        torch.from_numpy(merged_masks_data),
                        orig_shape=existing_results[0].orig_shape
                    )

                if (hasattr(existing_results[0], 'keypoints') and existing_results[0].keypoints is not None and
                        hasattr(new_results[0], 'keypoints') and new_results[0].keypoints is not None):
                    merged_keypoints_data = np.concatenate([
                        existing_results[0].keypoints.data.cpu().numpy(),
                        new_results[0].keypoints.data.cpu().numpy()
                    ], axis=0)
                    existing_results[0].keypoints = Keypoints(
                        torch.from_numpy(merged_keypoints_data),
                        orig_shape=existing_results[0].orig_shape
                    )

                if (hasattr(existing_results[0], 'obb') and existing_results[0].obb is not None and
                        hasattr(new_results[0], 'obb') and new_results[0].obb is not None):
                    merged_obb_data = np.concatenate([
                        existing_results[0].obb.data.cpu().numpy(),
                        new_results[0].obb.data.cpu().numpy()
                    ], axis=0)
                    existing_results[0].obb = OBB(
                        torch.from_numpy(merged_obb_data),
                        orig_shape=existing_results[0].orig_shape
                    )

                self.yolo_results[file_path] = existing_results
            else:
                self.yolo_results[file_path] = new_results
        except Exception as e:
            self.parent.statusbar.showMessage(
                f"❌ Local detection results cannot be merged with global detection results: {str(e)}", 5000)
            self.yolo_results[file_path] = new_results

    def merge_results_label(self, file_path, new_label):
        """
        Merge new detection results (in labels format) into existing yolo_results
        """
        try:
            if file_path in self.yolo_results:
                existing_labels = self.yolo_results[file_path]

                if "boxes" in existing_labels and "boxes" in new_label:
                    existing_labels["boxes"].extend(new_label["boxes"])

                if "masks" in existing_labels and "masks" in new_label:
                    existing_labels["masks"].extend(new_label["masks"])

                if "keypoints" in existing_labels and "keypoints" in new_label:
                    existing_labels["keypoints"].extend(new_label["keypoints"])

                if "obb" in existing_labels and "obb" in new_label:
                    existing_labels["obb"].extend(new_label["obb"])

                if "names" in new_label:
                    existing_labels["names"].update(new_label["names"])

                self.yolo_results[file_path] = existing_labels
            else:
                self.yolo_results[file_path] = new_label

        except Exception as e:
            self.parent.statusbar.showMessage(
                f"❌ Local detection results cannot be merged with global detection results: {str(e)}", 5000)
            self.yolo_results[file_path] = new_label

    def reset_results(self):
        """Clear image cache"""
        current_item = self.parent.files_dock.list_widget.currentItem()
        if not current_item:
            self.parent.statusbar.showMessage("No image selected", 2000)
            return
        file_path = current_item.data(QtCore.Qt.UserRole)
        if self.yolo_results:
            self.yolo_results.clear()
        if self.yolo_cache:
            self.yolo_cache.clear()
        self.parent.statusbar.showMessage("All inspection results reset", 2000)
        self.load_file(file_path)

    def reset_view(self):
        """Reset view and reset currently displayed image to image_cache"""
        current_item = self.parent.files_dock.list_widget.currentItem()
        if not current_item:
            self.parent.statusbar.showMessage("No image selected", 2000)
            return

        file_path = current_item.data(QtCore.Qt.UserRole)
        if file_path not in self.parent.files_dock.file_paths:
            self.parent.statusbar.showMessage("Current image not in image list", 2000)
            return

        try:
            if file_path in self.yolo_results:
                del self.yolo_results[file_path]
            if file_path in self.yolo_cache:
                del self.yolo_cache[file_path]
            self.parent.statusbar.showMessage(f"Detection results reset: {os.path.basename(file_path)}", 3000)
            self.load_file(file_path)
        except Exception as e:
            self.parent.statusbar.showMessage(f"Failed to reset image: {str(e)}", 3000)

    def on_switch_display_click(self, event):
        self.current_mode_index = (self.current_mode_index + 1) % len(self.display_modes)
        self.update_display_layout()
        event.accept()

    def hide_patch_rect(self):
        """
        Hide detection area box
        """
        if self.patch_rect_item:
            self.patch_rect_item.hide()
        if self.patch_hide_timer:
            self.patch_hide_timer.stop()

    # ===== mouse =====
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.pixmap_item:
            self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

        if self.switch_display_btn.isVisible():
            self.switch_display_btn.move(
                self.graphics_view.width() - self.switch_display_btn.width() - 10,
                10
            )

    def enterEvent(self, event):
        if self.switch_display_btn.isVisible():
            self.reset_hide_timer()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.reset_hide_timer()
        super().leaveEvent(event)

    def reset_hide_timer(self):
        """Reset button hide timer"""
        if hasattr(self, 'hide_timer'):
            self.hide_timer.stop()
        self.hide_timer = QtCore.QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_floating_button)
        self.hide_timer.start(2000)

    def hide_floating_button(self):
        """Hide display switch button"""
        self.switch_display_btn.hide()

    def zoom_in(self):
        self.graphics_view.scale(1.1, 1.1)

    def zoom_out(self):
        self.graphics_view.scale(0.9, 0.9)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.graphics_view.scale(1.1, 1.1)
            elif delta < 0:
                self.graphics_view.scale(0.9, 0.9)
            event.accept()
        elif self.parent.is_fixed_size:
            delta = event.angleDelta().y()
            current_mode = self.display_modes[self.current_mode_index]
            if delta > 0:
                self.parent.files_dock.prev_image(event, current_mode)
            elif delta < 0:
                self.parent.files_dock.next_image(event, current_mode)
            else:
                event.ignore()
            event.accept()
        else:
            delta = event.angleDelta().y()
            if delta > 0:
                self.graphics_view.scale(1.1, 1.1)
            elif delta < 0:
                self.graphics_view.scale(0.9, 0.9)
            event.accept()

    def mousePressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.button() == Qt.MouseButton.LeftButton:
            if self.point_detection_mode and self.pixmap_item:
                self.handle_point_detection(event, super=True)
            else:
                self.ctrl_pressed = True
        elif event.modifiers() == Qt.ControlModifier and event.button() == Qt.MouseButton.RightButton:
            if self.pixmap_item is not None:
                self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

        elif event.button() == Qt.MouseButton.RightButton and (self.show_label or self.show_results):
            self.on_context_menu(event.pos())
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.mouse_pressed = True
            self.last_mouse_pos = event.pos()
            self.graphics_view.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.point_detection_mode and self.pixmap_item:
                self.handle_point_detection(event)
            elif self.switch_display_btn.isVisible():
                self.reset_hide_timer()
            else:
                self.switch_display_btn.show()
                self.switch_display_btn.move(self.graphics_view.width() - self.switch_display_btn.width() - 10, 10)
        else:
            QtWidgets.QGraphicsView.mousePressEvent(self.graphics_view, event)

    def mouseMoveEvent(self, event):
        if self.pixmap_item and not self.mouse_pressed and self.ctrl_pressed:
            view_pos = event.pos()
            scene_pos = self.graphics_view.mapToScene(view_pos)
            pixmap_pos = self.pixmap_item.mapFromScene(scene_pos)

            x, y = int(pixmap_pos.x()), int(pixmap_pos.y())

            img = self.img[1]
            img_h, img_w = img.shape[:2] if len(img.shape) >= 2 else (0, 0)
            if 0 <= x < img_w and 0 <= y < img_h:
                if len(img) == 2:
                    pixel_value = img[y, x]
                    self.parent.statusbar.showMessage(f"Position: ({x}, {y})  V: {pixel_value}", 1000)
                elif len(img.shape) == 3:
                    b, g, r = img[y, x]
                    self.parent.statusbar.showMessage(f"Position: ({x}, {y}) V: R={r}, G={g}, B={b}", 1000)
            else:
                self.parent.statusbar.showMessage("", 1000)
        if self.mouse_pressed:
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            h_scroll = self.graphics_view.horizontalScrollBar()
            v_scroll = self.graphics_view.verticalScrollBar()
            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or event.button() == Qt.MouseButton.RightButton or event.button() == Qt.MouseButton.LeftButton:
            self.mouse_pressed = False
            self.graphics_view.setCursor(Qt.ArrowCursor)
            self.ctrl_pressed = False
        else:
            QtWidgets.QGraphicsView.mouseReleaseEvent(self.graphics_view, event)

    def cleanup(self):
        """Clean up resources occupied by ImageViewer"""
        if self.pixmap_item:
            self.graphics_scene.removeItem(self.pixmap_item)
            self.pixmap_item = None

        self.graphics_scene.clear()

        self.graphics_view.setScene(None)
        self.graphics_view = None
        self.graphics_scene = None

        self.label_file_path = None

        self.ctrl_pressed = False
        self.mouse_pressed = False
        self.last_mouse_pos = None
        self.parent.statusbar.showMessage(f"✅ ImageViewer resources released", 3000)
