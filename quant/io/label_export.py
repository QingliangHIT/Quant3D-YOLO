"""标签与掩码导出：results_label -> YOLO txt / labelme json / COCO json / 掩码图像。"""

import json
import os
import traceback

import numpy as np
from PyQt5 import QtCore


def results_to_mask(view, results_label):
    shape = results_label.get('shape', None)
    height, width = shape[:2]
    mask_img = np.zeros((height, width, 3), dtype=np.uint8)

    if len(results_label) > 0:
        if hasattr(view.parent, 'plotter'):
            black_background = np.zeros((height, width, 3), dtype=np.uint8)
            mask_img = view.parent.plotter.process_mini(black_background, results_label,
                                                        show_boxes=view.parent.annos_dock.show_boxes,
                                                        show_conf=view.parent.annos_dock.show_confidence,
                                                        show_labels=view.parent.annos_dock.show_labels)
    return mask_img


def export_labels_to_txt(view, results_label, save_path):
    # Export labels to YOLO format txt file
    try:
        yolo_params = view.parent.yolo_dock.get_parameters()
        task_type = yolo_params["task"]
        if os.path.exists(save_path):
            os.remove(save_path)

        shape = results_label.get("shape")
        if not shape:
            view.parent.statusbar.showMessage("Image shape information missing", 3000)
            return False

        height, width = shape

        with open(save_path, 'w', encoding='utf-8') as f:
            if task_type == "detect":
                boxes_data = results_label.get("boxes", [])
                for box in boxes_data:
                    if len(box) >= 6:
                        class_id = int(box[5])
                        x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
                        center_x = ((x1 + x2) / 2) / width
                        center_y = ((y1 + y2) / 2) / height
                        box_width = (x2 - x1) / width
                        box_height = (y2 - y1) / height

                        f.write(f"{class_id} {center_x:.6f} {center_y:.6f} {box_width:.6f} {box_height:.6f}\n")

            elif task_type == "segment":
                masks_data = results_label.get("masks", [])
                for mask in masks_data:
                    if len(mask) >= 3:
                        class_id = int(mask[0])
                        points = mask[1:]
                        line = str(class_id)
                        for i in range(0, len(points), 2):
                            x_norm = points[i] / width
                            y_norm = points[i + 1] / height
                            line += f" {x_norm:.6f} {y_norm:.6f}"
                        f.write(line + "\n")

            elif task_type == "pose":
                keypoints_data = results_label.get("keypoints", [])
                for kps in keypoints_data:
                    for kp in kps:
                        if len(kp) >= 3:
                            x_norm = kp[0] / width
                            y_norm = kp[1] / height
                            conf = kp[2]
                            f.write(f"{x_norm:.6f} {y_norm:.6f} {conf:.6f} ")
                    f.write("\n")

            elif task_type == "obb":
                obb_data = results_label.get("obb", [])
                for obb in obb_data:
                    if len(obb) >= 9:
                        class_id = int(obb[0])
                        points = obb[1:]
                        line = str(class_id)
                        for i in range(0, len(points), 2):
                            x_norm = points[i] / width
                            y_norm = points[i + 1] / height
                            line += f" {x_norm:.6f} {y_norm:.6f}"
                        f.write(line + "\n")

        return True
    except Exception as e:
        print(f"Error exporting labels to txt: {str(e)}")
        return False


def export_labels_to_json(view, results_label, save_path, json_format="labelme"):
    # Export labels to JSON format
    try:
        yolo_params = view.parent.yolo_dock.get_parameters()
        task_type = yolo_params["task"]
        if json_format.lower() == "labelme":
            json_data = view._convert_to_labelme_format(results_label, task_type)
        elif json_format.lower() == "coco":
            json_data = view._convert_to_coco_format(results_label, task_type)
        else:
            view.parent.statusbar.showMessage(f"Unsupported JSON format: {json_format}", 3000)
            return False

        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        print(f"Error exporting labels to JSON: {str(e)}")
        traceback.print_exc()
        return False


def convert_to_labelme_format(view, results_label, task_type):
    # Convert to LabelMe JSON format
    try:
        file_path = results_label.get("file_path", "")
        shape = results_label.get("shape", [])
        height, width = shape if len(shape) >= 2 else (0, 0)

        labelme_data = {
            "version": "5.1.1",
            "flags": {},
            "shapes": [],
            "imagePath": os.path.basename(file_path) if file_path else "",
            "imageData": None,
            "imageHeight": height,
            "imageWidth": width
        }

        names = results_label.get("names", {})

        if task_type == "detect":
            boxes_data = results_label.get("boxes", [])
            for i, box in enumerate(boxes_data):
                if len(box) >= 6:
                    class_id = int(box[5])
                    class_name = names.get(class_id, f"class_{class_id}")

                    x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
                    shape_data = {
                        "label": class_name,
                        "points": [[x1, y1], [x2, y2]],
                        "group_id": None,
                        "shape_type": "rectangle",
                        "flags": {}
                    }
                    labelme_data["shapes"].append(shape_data)

        elif task_type == "segment":
            masks_data = results_label.get("masks", [])
            for i, mask in enumerate(masks_data):
                if len(mask) >= 3:
                    class_id = int(mask[0])
                    class_name = names.get(class_id, f"class_{class_id}")
                    points = mask[1:]

                    polygon_points = []
                    for j in range(0, len(points), 2):
                        if j + 1 < len(points):
                            polygon_points.append([float(points[j]), float(points[j + 1])])

                    if len(polygon_points) >= 3:
                        shape_data = {
                            "label": class_name,
                            "points": polygon_points,
                            "group_id": None,
                            "shape_type": "polygon",
                            "flags": {}
                        }
                        labelme_data["shapes"].append(shape_data)

        elif task_type == "pose":
            keypoints_data = results_label.get("keypoints", [])
            for i, kps in enumerate(keypoints_data):
                for j, kp in enumerate(kps):
                    if len(kp) >= 3:
                        x, y, conf = float(kp[0]), float(kp[1]), float(kp[2])
                        if conf > 0:
                            class_name = f"keypoint_{j}"
                            shape_data = {
                                "label": class_name,
                                "points": [[x, y]],
                                "group_id": None,
                                "shape_type": "point",
                                "flags": {}
                            }
                            labelme_data["shapes"].append(shape_data)

        elif task_type == "obb":
            obb_data = results_label.get("obb", [])
            for i, obb in enumerate(obb_data):
                if len(obb) >= 9:
                    class_id = int(obb[0])
                    class_name = names.get(class_id, f"class_{class_id}")
                    points = obb[1:]

                    polygon_points = []
                    for j in range(0, len(points), 2):
                        if j + 1 < len(points):
                            polygon_points.append([float(points[j]), float(points[j + 1])])

                    if len(polygon_points) >= 3:
                        shape_data = {
                            "label": class_name,
                            "points": polygon_points,
                            "group_id": None,
                            "shape_type": "polygon",
                            "flags": {}
                        }
                        labelme_data["shapes"].append(shape_data)

        return labelme_data
    except Exception as e:
        print(f"Error converting to LabelMe format: {str(e)}")
        traceback.print_exc()
        return {
            "version": "5.1.1",
            "flags": {},
            "shapes": [],
            "imagePath": "",
            "imageData": None,
            "imageHeight": 0,
            "imageWidth": 0
        }


def convert_to_coco_format(view, results_label, task_type):
    # Convert to COCO JSON format
    try:
        file_path = results_label.get("file_path", "")
        shape = results_label.get("shape", [])
        height, width = shape if len(shape) >= 2 else (0, 0)

        coco_data = {
            "info": {
                "description": "Exported from Quant3D",
                "version": "1.0",
                "year": 2024,
                "contributor": "Quant3D",
                "date_created": QtCore.QDateTime.currentDateTime().toString("yyyy/MM/dd")
            },
            "licenses": [{
                "id": 1,
                "name": "Unknown",
                "url": ""
            }],
            "images": [{
                "id": 1,
                "width": width,
                "height": height,
                "file_name": os.path.basename(file_path) if file_path else "",
                "license": 1,
                "flickr_url": "",
                "coco_url": "",
                "date_captured": QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
            }],
            "annotations": [],
            "categories": []
        }

        names = results_label.get("names", {})

        category_map = {}
        for class_id, class_name in names.items():
            category_id = len(coco_data["categories"]) + 1
            category_map[class_id] = category_id
            coco_data["categories"].append({
                "id": category_id,
                "name": class_name,
                "supercategory": "object"
            })

        if not names:
            unique_class_ids = set()

            if task_type == "detect":
                boxes_data = results_label.get("boxes", [])
                for box in boxes_data:
                    if len(box) >= 6:
                        unique_class_ids.add(int(box[5]))
            elif task_type == "segment":
                masks_data = results_label.get("masks", [])
                for mask in masks_data:
                    if len(mask) >= 1:
                        unique_class_ids.add(int(mask[0]))
            elif task_type == "obb":
                obb_data = results_label.get("obb", [])
                for obb in obb_data:
                    if len(obb) >= 1:
                        unique_class_ids.add(int(obb[0]))

            for class_id in unique_class_ids:
                category_id = len(coco_data["categories"]) + 1
                category_map[class_id] = category_id
                coco_data["categories"].append({
                    "id": category_id,
                    "name": f"class_{class_id}",
                    "supercategory": "object"
                })

        annotation_id = 1

        if task_type == "detect":
            boxes_data = results_label.get("boxes", [])
            for i, box in enumerate(boxes_data):
                if len(box) >= 6:
                    class_id = int(box[5])
                    category_id = category_map.get(class_id, class_id)

                    x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
                    width_bbox = x2 - x1
                    height_bbox = y2 - y1
                    area = width_bbox * height_bbox
                    confidence = float(box[4]) if len(box) > 4 else 1.0

                    annotation = {
                        "id": annotation_id,
                        "image_id": 1,
                        "category_id": category_id,
                        "bbox": [x1, y1, width_bbox, height_bbox],
                        "area": area,
                        "iscrowd": 0,
                        "confidence": confidence
                    }
                    coco_data["annotations"].append(annotation)
                    annotation_id += 1

        elif task_type == "segment":
            masks_data = results_label.get("masks", [])
            for i, mask in enumerate(masks_data):
                if len(mask) >= 3:
                    class_id = int(mask[0])
                    category_id = category_map.get(class_id, class_id)
                    points = mask[1:]

                    x_coords = [float(points[j]) for j in range(0, len(points), 2)]
                    y_coords = [float(points[j]) for j in range(1, len(points), 2)]
                    x_min, x_max = min(x_coords), max(x_coords)
                    y_min, y_max = min(y_coords), max(y_coords)
                    width_bbox = x_max - x_min
                    height_bbox = y_max - y_min
                    area = width_bbox * height_bbox

                    segmentation = []
                    seg_points = []
                    for j in range(0, len(points), 2):
                        if j + 1 < len(points):
                            seg_points.extend([float(points[j]), float(points[j + 1])])
                    segmentation.append(seg_points)

                    annotation = {
                        "id": annotation_id,
                        "image_id": 1,
                        "category_id": category_id,
                        "bbox": [x_min, y_min, width_bbox, height_bbox],
                        "segmentation": segmentation,
                        "area": area,
                        "iscrowd": 0
                    }
                    coco_data["annotations"].append(annotation)
                    annotation_id += 1

        elif task_type == "obb":
            obb_data = results_label.get("obb", [])
            for i, obb in enumerate(obb_data):
                if len(obb) >= 9:
                    class_id = int(obb[0])
                    category_id = category_map.get(class_id, class_id)
                    points = obb[1:]

                    x_coords = [float(points[j]) for j in range(0, len(points), 2)]
                    y_coords = [float(points[j]) for j in range(1, len(points), 2)]
                    x_min, x_max = min(x_coords), max(x_coords)
                    y_min, y_max = min(y_coords), max(y_coords)
                    width_bbox = x_max - x_min
                    height_bbox = y_max - y_min
                    area = width_bbox * height_bbox

                    segmentation = []
                    seg_points = []
                    for j in range(0, len(points), 2):
                        if j + 1 < len(points):
                            seg_points.extend([float(points[j]), float(points[j + 1])])
                    segmentation.append(seg_points)

                    annotation = {
                        "id": annotation_id,
                        "image_id": 1,
                        "category_id": category_id,
                        "bbox": [x_min, y_min, width_bbox, height_bbox],
                        "segmentation": segmentation,
                        "area": area,
                        "iscrowd": 0
                    }
                    coco_data["annotations"].append(annotation)
                    annotation_id += 1

        return coco_data
    except Exception as e:
        print(f"Error converting to COCO format: {str(e)}")
        traceback.print_exc()
        return {
            "info": {
                "description": "Exported from Quant3D",
                "version": "1.0",
                "year": 2024,
                "contributor": "Quant3D",
                "date_created": QtCore.QDateTime.currentDateTime().toString("yyyy/MM/dd")
            },
            "licenses": [{
                "id": 1,
                "name": "Unknown",
                "url": ""
            }],
            "images": [],
            "annotations": [],
            "categories": []
        }
