"""检测框几何查询：重叠判定、最近框搜索、单目标抽取。"""

import numpy as np
import cv2


def boxes_overlap(view, box1, box2, threshold=0.3):
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


def find_nearest_box(view, scene_pos, results_label):
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


def extract_single_label(view, results_label, box_idx):
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
