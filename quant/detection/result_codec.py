"""检测结果编解码：ultralytics Results / results_label 字典 与内部标注结构的互转与过滤。"""
from __future__ import annotations

import numpy as np
from ultralytics.engine.results import Results


def filter_results_label(yolo_labels: dict, names: dict, classes_names=None) -> dict:
    """按类别名过滤 results_label 字典（框/掩码/关键点/旋转框）。"""
    if not isinstance(classes_names, list):
        return yolo_labels

    names = yolo_labels.get("names", names)
    if len(names) == 0:
        return yolo_labels

    name_to_index = {name: i for (i, name) in names.items()}
    classes_ids = [int(name_to_index[name]) for name in classes_names if name in name_to_index]

    file_path = yolo_labels.get("file_path", "")
    shape = yolo_labels.get("shape", [])
    boxes_data = yolo_labels.get("boxes", [])
    masks_data = yolo_labels.get("masks", [])
    keypoints_data = yolo_labels.get("keypoints", [])
    obb_data = yolo_labels.get("obb", [])

    if len(classes_ids) == 0:
        return {
            "file_path": file_path, "shape": shape, "boxes": [], "masks": [],
            "keypoints": [], "obb": [], "names": names,
        }

    filtered_boxes = [box for box in boxes_data if len(box) > 5 and int(box[5]) in classes_ids]
    filtered_masks = [mask for mask in masks_data if len(mask) > 0 and int(mask[0]) in classes_ids]
    filtered_obb = [obb for obb in obb_data if len(obb) > 0 and int(obb[0]) in classes_ids]

    if keypoints_data and filtered_boxes:
        filtered_keypoints = [keypoints_data[i] for i in range(min(len(keypoints_data), len(filtered_boxes)))]
    elif keypoints_data and not boxes_data:
        filtered_keypoints = keypoints_data
    else:
        filtered_keypoints = []

    return {
        "file_path": file_path,
        "shape": shape,
        "boxes": filtered_boxes,
        "masks": filtered_masks,
        "keypoints": filtered_keypoints,
        "obb": filtered_obb,
        "names": names,
    }


def summarize_results(results, names: dict) -> list:
    """从 ultralytics Results 列表提取检测信息字典。"""
    detections_info = []
    if not results or len(results) == 0:
        return detections_info

    result = results[0]

    if getattr(result, "boxes", None) is not None:
        boxes = result.boxes.xyxy
        confidences = result.boxes.conf
        class_ids = result.boxes.cls
        for i in range(len(boxes)):
            x1, y1, x2, y2 = boxes[i]
            class_id = int(class_ids[i])
            detections_info.append({
                "id": i,
                "class_id": class_id,
                "class_name": names.get(class_id, f"class_{class_id}"),
                "confidence": float(confidences[i]),
                "area1": float((x2 - x1) * (y2 - y1)),
                "area2": None,
                "keys": 0,
            })

    if getattr(result, "obb", None) is not None:
        obb_data = result.obb.data.cpu().numpy()
        class_ids = result.obb.cls.cpu().numpy().astype(int)
        confidences = result.obb.conf.cpu().numpy()
        for i in range(len(obb_data)):
            _, _, width, height, angle = obb_data[i][:5]
            class_id = int(class_ids[i])
            detections_info.append({
                "id": i,
                "class_id": class_id,
                "class_name": names.get(class_id, f"class_{class_id}"),
                "confidence": float(confidences[i]) if i < len(confidences) else 0.0,
                "area1": float(width * height),
                "area2": None,
                "keys": 0,
                "angle": float(angle),
            })

    if getattr(result, "keypoints", None) is not None:
        keypoints_data = result.keypoints.data.cpu().numpy()
        for i, detection_dict in enumerate(detections_info):
            if i < len(keypoints_data):
                detection_dict["keys"] = int(np.count_nonzero(keypoints_data[i][:, 2] > 0))

    if getattr(result, "masks", None) is not None:
        masks = result.masks.data.cpu().numpy()
        has_boxes = result.boxes is not None
        class_ids = result.boxes.cls.cpu().numpy().astype(int) if has_boxes else [0] * len(masks)
        confidences = result.boxes.conf.cpu().numpy() if has_boxes else [0.0] * len(masks)

        for i in range(len(detections_info), len(masks)):
            class_id = int(class_ids[i]) if i < len(class_ids) else 0
            detections_info.append({
                "id": i,
                "class_id": class_id,
                "class_name": names.get(class_id, f"class_{class_id}"),
                "confidence": float(confidences[i]) if i < len(confidences) else 0.0,
                "area1": None,
                "area2": None,
                "keys": 0,
            })

        for i, (mask_data, detection_dict) in enumerate(zip(masks, detections_info)):
            detection_dict["area2"] = float(np.count_nonzero(mask_data))

    return detections_info


def polygon_area(points) -> float:
    """鞋带公式计算多边形面积（points 为 [x1, y1, x2, y2, ...]）。"""
    if len(points) < 6 or len(points) % 2 != 0:
        return 0.0
    x_coords = [points[j] for j in range(0, len(points), 2)]
    y_coords = [points[j] for j in range(1, len(points), 2)]
    area = 0.0
    for j in range(len(x_coords)):
        k = (j + 1) % len(x_coords)
        area += x_coords[j] * y_coords[k]
        area -= x_coords[k] * y_coords[j]
    return abs(area) / 2.0


def summarize_label(results_label: dict) -> list:
    """从 results_label 字典提取检测信息（含框面积与掩码多边形面积）。"""
    detections_info = []
    if not results_label:
        return detections_info

    names = results_label.get("names", {})
    boxes_data = results_label.get("boxes", [])
    masks_data = results_label.get("masks", [])
    keypoints_data = results_label.get("keypoints", [])
    obb_data = results_label.get("obb", [])

    for i, box in enumerate(boxes_data):
        x1, y1, x2, y2 = box[:4]
        class_id = int(box[5]) if len(box) > 5 else 0
        detections_info.append({
            "id": i,
            "class_id": class_id,
            "class_name": names.get(class_id, f"class_{class_id}"),
            "confidence": float(box[4]) if len(box) > 4 else 1.0,
            "area1": float((x2 - x1) * (y2 - y1)),
            "area2": None,
            "keys": 0,
        })

    if obb_data and not detections_info:
        for i, obb in enumerate(obb_data):
            class_id = int(obb[0]) if len(obb) > 0 else 0
            if len(obb) >= 9:
                x_coords = [obb[j] for j in range(1, len(obb), 2)]
                y_coords = [obb[j] for j in range(2, len(obb), 2)]
                obb_area = float((max(x_coords) - min(x_coords)) * (max(y_coords) - min(y_coords)))
            else:
                obb_area = 0.0
            detections_info.append({
                "id": i,
                "class_id": class_id,
                "class_name": names.get(class_id, f"class_{class_id}"),
                "confidence": 1.0,
                "area1": obb_area,
                "area2": None,
                "keys": 0,
            })
    elif obb_data:
        for i, (detection_dict, obb) in enumerate(zip(detections_info, obb_data)):
            class_id = int(obb[0]) if len(obb) > 0 else detection_dict["class_id"]
            if len(obb) >= 9:
                x_coords = [obb[j] for j in range(1, len(obb), 2)]
                y_coords = [obb[j] for j in range(2, len(obb), 2)]
                detection_dict["area1"] = float(
                    (max(x_coords) - min(x_coords)) * (max(y_coords) - min(y_coords))
                )
            if "class_id" not in detection_dict or detection_dict["class_id"] == 0:
                detection_dict["class_id"] = class_id
                detection_dict["class_name"] = names.get(class_id, f"class_{class_id}")

    for i, detection_dict in enumerate(detections_info):
        if i >= len(keypoints_data):
            break
        kps = keypoints_data[i]
        if not isinstance(kps, list) or not kps:
            continue
        if isinstance(kps[0], list) and len(kps[0]) >= 3:
            visible = sum(1 for kp in kps if len(kp) >= 3 and kp[2] > 0)
        elif len(kps) % 3 == 0:
            visible = sum(1 for j in range(2, len(kps), 3) if kps[j] > 0)
        else:
            visible = 0
        detection_dict["keys"] = int(visible)

    if masks_data:
        for i in range(len(detections_info), len(masks_data)):
            mask_info = masks_data[i]
            class_id = int(mask_info[0]) if len(mask_info) > 0 else 0
            detections_info.append({
                "id": i,
                "class_id": class_id,
                "class_name": names.get(class_id, f"class_{class_id}"),
                "confidence": 1.0,
                "area1": None,
                "area2": None,
                "keys": 0,
            })
        for i, (detection_dict, mask_info) in enumerate(zip(detections_info, masks_data)):
            detection_dict["area2"] = float(polygon_area(mask_info[1:]))

    return detections_info


def result_to_label(view, results):
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


def merge_results_label(view, file_path, new_label):
    """
    Merge new detection results (in labels format) into existing yolo_results
    """
    try:
        if file_path in view.yolo_results:
            existing_labels = view.yolo_results[file_path]

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

            view.yolo_results[file_path] = existing_labels
        else:
            view.yolo_results[file_path] = new_label

    except Exception as e:
        view.parent.statusbar.showMessage(
            f"❌ Local detection results cannot be merged with global detection results: {str(e)}", 5000)
        view.yolo_results[file_path] = new_label
