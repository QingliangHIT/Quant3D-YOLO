"""标签文件解析：把 YOLO txt / labelme json / Pascal VOC xml 解析为统一的 results_label 结构。"""

import json
import xml.etree.ElementTree as ET


def load_label_file_txt(view, img, file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
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
                task = view.parent.annos_dock.get_current_task_type()

                if len(parts) >= 49 and task == "pose":
                    view.parent.annos_dock.update_task_type(3)
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
                    view.parent.annos_dock.update_task_type(2)
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
                    view.parent.annos_dock.update_task_type(0)
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
                    view.parent.annos_dock.update_task_type(1)
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
            img = view.show_annotations_with_results(img, yolo_labels)
            return True, yolo_labels
        else:
            return False, None

    except FileNotFoundError:
        print(f"Error: Cannot find label file {file_path}")
        return False, img
    except Exception as e:
        print(f"Error: Exception occurred while loading label file {file_path}: {e}")
        return False, img


def load_label_file_json(view, img, file_path):
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
            img = view.show_annotations_with_results(img, yolo_labels)
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


def load_label_file_xml(view, img, file_path):
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
