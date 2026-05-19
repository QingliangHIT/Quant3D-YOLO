import cv2
import numpy as np


# Color list (BGR format)
COLORS = [
    (0, 0, 255),  # Red
    (0, 255, 0),  # Green
    (255, 0, 0),  # Blue
    (255, 255, 0),  # Cyan
    (255, 0, 255),  # Purple
    (0, 255, 255),  # Yellow
    (128, 0, 128),  # Dark purple
    (0, 128, 128),  # Dark cyan
    (128, 128, 0),  # Dark yellow
    (128, 128, 128),  # Gray
]


class YOLOPlotter:
    def __init__(self, task="detect", names=None):
        self.task = task
        self.offset = 0
        self.names = {} if names is None else names
        self.index = {name: i for (i, name) in self.names.items()} if len(names) > 0 else {}

    def process(self, results, classes_names=None, show_boxes=True, show_conf=False, show_labels=False):
        """Process YOLO results and draw annotations on image"""
        try:
            if len(results) > 0:
                result = results[0]
                height, width = result.orig_shape

                # Adaptive parameters based on image size
                line_thickness = max(1, int(min(width, height) / 432))
                font_scale = min(width, height) / 1080.0
                result = self.filter_result(result, classes_names)

                img = result.plot(
                    line_width=line_thickness,
                    font_size=font_scale,
                    boxes=show_boxes,
                    masks=self.task != 'detect',
                    kpt_line=True,
                    conf=show_conf,
                    labels=show_labels,
                )
                return img
            return results.orig_img

        except Exception as e:
            print(f"Error processing YOLO results: {e}")
            return None

    def process_mini(self, img, results_label, classes_names=None, show_boxes=True, show_conf=False, show_labels=False):
        """Process results_label format data and draw annotations"""
        try:
            height, width = img.shape[:2]
            show_masks = self.task != 'detect'
            if not show_masks and not show_boxes:
                show_boxes = True

            # Adaptive parameters based on image size
            line_thickness = max(1, int(min(width, height) / 432))
            font_scale = min(width, height) / 1080.0

            # Get label data
            boxes_data = results_label.get("boxes", [])
            masks_data = results_label.get("masks", [])
            keypoints_data = results_label.get("keypoints", [])
            obb_data = results_label.get("obb", [])
            names = results_label.get("names", self.names)

            # Filter results by class
            if isinstance(classes_names, list) and len(classes_names) > 0 and len(names) > 0:
                name_to_index = {name: i for (i, name) in names.items()}
                classes_ids = [int(name_to_index[name]) for name in classes_names if name in name_to_index]

                # Filter bbox data
                filtered_boxes = []
                for box in boxes_data:
                    class_id = int(box[5])
                    if class_id in classes_ids:
                        filtered_boxes.append(box)
                boxes_data = filtered_boxes

                # Filter mask data
                filtered_masks = []
                for mask in masks_data:
                    class_id = int(mask[0])
                    if class_id in classes_ids:
                        filtered_masks.append(mask)
                masks_data = filtered_masks

                # Filter keypoints data
                filtered_keypoints = []
                for i, kp in enumerate(keypoints_data):
                    if i < len(boxes_data):
                        filtered_keypoints.append(kp)
                keypoints_data = filtered_keypoints

                # Filter OBB data
                filtered_obb = []
                for obb in obb_data:
                    class_id = int(obb[0])
                    if class_id in classes_ids:
                        filtered_obb.append(obb)
                obb_data = filtered_obb

            # Draw annotations
            if show_boxes and boxes_data:
                img = self.draw_boxes_direct(img, boxes_data, names, height, width, line_thickness, font_scale,
                                             show_conf, show_labels)

            if show_masks and masks_data:
                img = self.draw_masks_direct(img, masks_data, height, width)

            if keypoints_data:
                img = self.draw_keypoints_direct(img, keypoints_data, names, height, width, line_thickness, font_scale,
                                                 show_conf, show_labels)

            if obb_data:
                img = self.draw_obb_direct(img, obb_data, names, height, width, line_thickness, font_scale, show_conf,
                                           show_labels)

            return img

        except Exception as e:
            print(f"Error processing YOLO results: {e}")
            import traceback
            traceback.print_exc()
            return img

    def draw_boxes_direct(self, img, boxes_data, names, height, width, line_thickness, font_scale, show_conf,
                          show_labels):
        """Draw bounding boxes directly on image"""
        for box in boxes_data:
            x1, y1, x2, y2 = box[:4]
            confidence = box[4]
            class_id = int(box[5])

            # Ensure coordinates are within image bounds
            x1 = max(0, min(x1, width - 1))
            y1 = max(0, min(y1, height - 1))
            x2 = max(0, min(x2, width - 1))
            y2 = max(0, min(y2, height - 1))

            # class_name = names.get(class_id, f"class_{class_id}")
            class_name = names.get(class_id, f"{class_id}")
            color = COLORS[(class_id + self.offset) % len(COLORS)]

            # Draw bounding box
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, line_thickness)

            # Draw label
            if show_labels or show_conf:
                label_parts = []
                if show_labels:
                    label_parts.append(class_name)
                if show_conf:
                    label_parts.append(f'{confidence:.2f}')

                if label_parts:
                    label = ' '.join(label_parts)
                    text_size = \
                        cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, max(1, line_thickness // 2))[0]
                    label_bg_height = int(1.5 * text_size[1])
                    cv2.rectangle(img, (int(x1), int(y1) - label_bg_height),
                                  (int(x1) + text_size[0], int(y1)), color, -1)
                    cv2.putText(img, label, (int(x1), int(y1) - max(2, label_bg_height // 4)),
                                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), max(1, line_thickness // 2))

        return img

    def draw_masks_direct(self, img, masks_data, height, width):
        """Draw segmentation masks directly on image"""
        mask_img = np.zeros_like(img)

        # Draw color for each mask
        for i, mask_info in enumerate(masks_data):
            class_id = int(mask_info[0])
            points = mask_info[1:]

            if len(points) >= 6 and len(points) % 2 == 0:
                color = COLORS[(class_id + self.offset) % len(COLORS)]

                # Build points array
                pts = []
                for j in range(0, len(points), 2):
                    x = int(points[j])
                    y = int(points[j + 1])
                    x = max(0, min(x, width - 1))
                    y = max(0, min(y, height - 1))
                    pts.append([x, y])

                if len(pts) >= 3:
                    pts = np.array(pts, np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.fillPoly(mask_img, [pts], color)

        # Overlay mask on image
        img = cv2.addWeighted(img, 1.0, mask_img, 0.5, 0)
        return img

    def draw_keypoints_direct(self, img, keypoints_data, names, height, width, line_thickness, font_scale, show_conf,
                              show_labels):
        """Draw keypoints directly on image"""
        for i, kps in enumerate(keypoints_data):
            # Draw keypoints
            for kp in kps:
                x, y, conf = kp
                if conf > 0:
                    x = max(0, min(x, width - 1))
                    y = max(0, min(y, height - 1))
                    cv2.circle(img, (int(x), int(y)), line_thickness * 2, (0, 255, 0), -1)

        return img

    def draw_obb_direct(self, img, obb_data, names, height, width, line_thickness, font_scale, show_conf, show_labels):
        """Draw oriented bounding boxes directly on image"""
        for obb in obb_data:
            class_id = int(obb[0])
            points = obb[1:]

            if len(points) == 8:
                color = COLORS[(class_id + self.offset) % len(COLORS)]

                # Build points array
                pts = []
                for j in range(0, len(points), 2):
                    x = points[j]
                    y = points[j + 1]
                    x = max(0, min(x, width - 1))
                    y = max(0, min(y, height - 1))
                    pts.append((int(x), int(y)))

                # Draw polygon outline
                for j in range(4):
                    p1 = pts[j]
                    p2 = pts[(j + 1) % 4]
                    cv2.line(img, p1, p2, color, line_thickness)

                # Draw label
                if show_labels or show_conf:
                    x, y = pts[0]
                    class_name = names.get(class_id, f"class_{class_id}")

                    label_parts = []
                    if show_labels:
                        label_parts.append(class_name)

                    if label_parts:
                        label = ' '.join(label_parts)
                        text_size = \
                            cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, max(1, line_thickness // 2))[0]
                        label_bg_height = int(1.5 * text_size[1])
                        cv2.rectangle(img, (int(x), int(y) - label_bg_height),
                                      (int(x) + text_size[0], int(y)), color, -1)
                        cv2.putText(img, label, (int(x), int(y) - max(2, label_bg_height // 4)),
                                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), max(1, line_thickness // 2))

        return img

    def filter_result(self, result, classes_names=None):
        """Filter YOLO results by class names"""
        from ultralytics.engine.results import Results
        import torch

        if isinstance(classes_names, list) and len(classes_names) > 0 and len(self.index) > 0:
            classes = [int(self.index[name]) for name in classes_names]

            if result.boxes is not None:
                classes_tensor = torch.tensor(classes, device=result.boxes.cls.device)
                filtered_boxes_indices = (result.boxes.cls[..., None] == classes_tensor).any(-1)

                result.boxes = result.boxes[filtered_boxes_indices]

                if result.masks is not None:
                    result.masks = result.masks[filtered_boxes_indices]

                if result.keypoints is not None:
                    result.keypoints = result.keypoints[filtered_boxes_indices]

            if result.obb is not None:
                classes_tensor = torch.tensor(classes, device=result.obb.cls.device)
                filtered_obb_indices = (result.obb.cls[..., None] == classes_tensor).any(-1)
                result.obb = result.obb[filtered_obb_indices]
        return result

    def filter_results_label(self, yolo_labels, classes_names=None):
        """Filter results_label format data by class names"""
        if not isinstance(classes_names, list):
            return yolo_labels

        names = yolo_labels.get("names", self.names)

        if len(names) == 0:
            return yolo_labels

        name_to_index = {name: i for (i, name) in names.items()}
        classes_ids = [int(name_to_index[name]) for name in classes_names if name in name_to_index]

        if len(classes_ids) == 0:
            return {
                "file_path": yolo_labels.get("file_path", ""),
                "shape": yolo_labels.get("shape", []),
                "boxes": [],
                "masks": [],
                "keypoints": [],
                "obb": [],
                "names": names
            }

        # Get original data
        file_path = yolo_labels.get("file_path", "")
        shape = yolo_labels.get("shape", [])
        boxes_data = yolo_labels.get("boxes", [])
        masks_data = yolo_labels.get("masks", [])
        keypoints_data = yolo_labels.get("keypoints", [])
        obb_data = yolo_labels.get("obb", [])

        # Filter bbox data
        filtered_boxes = []
        if boxes_data:
            for box in boxes_data:
                if len(box) > 5:
                    class_id = int(box[5])
                    if class_id in classes_ids:
                        filtered_boxes.append(box)

        # Filter mask data
        filtered_masks = []
        if masks_data:
            for mask in masks_data:
                if len(mask) > 0:
                    class_id = int(mask[0])
                    if class_id in classes_ids:
                        filtered_masks.append(mask)

        # Filter keypoints data
        filtered_keypoints = []
        if keypoints_data and filtered_boxes:
            for i in range(min(len(keypoints_data), len(filtered_boxes))):
                filtered_keypoints.append(keypoints_data[i])
        elif keypoints_data and not boxes_data:
            filtered_keypoints = keypoints_data

        # Filter OBB data
        filtered_obb = []
        if obb_data:
            for obb in obb_data:
                if len(obb) > 0:
                    class_id = int(obb[0])
                    if class_id in classes_ids:
                        filtered_obb.append(obb)

        return {
            "file_path": file_path,
            "shape": shape,
            "boxes": filtered_boxes,
            "masks": filtered_masks,
            "keypoints": filtered_keypoints,
            "obb": filtered_obb,
            "names": names
        }

    def get_info(self, results):
        """Extract detection information from YOLO results"""
        detections_info = []

        if not results or len(results) == 0:
            return detections_info

        result = results[0]

        # Process bbox results
        if hasattr(result, 'boxes') and result.boxes is not None:
            boxes = result.boxes.xyxy
            confidences = result.boxes.conf
            class_ids = result.boxes.cls

            for i in range(len(boxes)):
                x1, y1, x2, y2 = boxes[i]
                confidence = float(confidences[i])
                class_id = int(class_ids[i])

                class_name = self.names.get(class_id, f"class_{class_id}")
                box_area = float((x2 - x1) * (y2 - y1))

                detection_dict = {
                    "id": i,
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": confidence,
                    "area1": box_area,
                    "area2": None,
                    "keys": 0
                }

                detections_info.append(detection_dict)

        # Process OBB results
        if hasattr(result, 'obb') and result.obb is not None:
            obb_data = result.obb.data.cpu().numpy()
            class_ids = result.obb.cls.cpu().numpy().astype(int)
            confidences = result.obb.conf.cpu().numpy()

            for i in range(len(obb_data)):
                x_center, y_center, width, height, angle = obb_data[i][:5]
                confidence = float(confidences[i]) if i < len(confidences) else 0.0
                class_id = int(class_ids[i])

                class_name = self.names.get(class_id, f"class_{class_id}")
                obb_area = float(width * height)

                detection_dict = {
                    "id": i,
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": confidence,
                    "area1": obb_area,
                    "area2": None,
                    "keys": 0,
                    "angle": float(angle)
                }

                detections_info.append(detection_dict)

        # Process keypoints info
        if hasattr(result, 'keypoints') and result.keypoints is not None:
            keypoints_data = result.keypoints.data.cpu().numpy()

            for i, detection_dict in enumerate(detections_info):
                if i < len(keypoints_data):
                    visible_keypoints = np.count_nonzero(keypoints_data[i][:, 2] > 0)
                    detection_dict["keys"] = int(visible_keypoints)

        # Process mask results
        if hasattr(result, 'masks') and result.masks is not None:
            masks = result.masks.data.cpu().numpy()
            class_ids = result.boxes.cls.cpu().numpy().astype(int) if result.boxes is not None else [0] * len(masks)
            confidences = result.boxes.conf.cpu().numpy() if result.boxes is not None else [0.0] * len(masks)

            if len(masks) > len(detections_info):
                for i in range(len(detections_info), len(masks)):
                    class_id = int(class_ids[i]) if i < len(class_ids) else 0
                    confidence = float(confidences[i]) if i < len(confidences) else 0.0
                    class_name = self.names.get(class_id, f"class_{class_id}")

                    detection_dict = {
                        "id": i,
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": confidence,
                        "area1": None,
                        "area2": None,
                        "keys": 0
                    }
                    detections_info.append(detection_dict)

            for i, (mask_data, detection_dict) in enumerate(zip(masks, detections_info)):
                mask_area = np.count_nonzero(mask_data)
                detection_dict["area2"] = float(mask_area)

        elif hasattr(result, 'masks') and result.masks is not None:
            masks = result.masks.data.cpu().numpy()
            class_ids = result.boxes.cls.cpu().numpy().astype(int) if result.boxes is not None else [0] * len(masks)
            confidences = result.boxes.conf.cpu().numpy() if result.boxes is not None else [0.0] * len(masks)

            for i, mask_data in enumerate(masks):
                class_id = int(class_ids[i]) if i < len(class_ids) else 0
                confidence = float(confidences[i]) if i < len(confidences) else 0.0
                class_name = self.names.get(class_id, f"class_{class_id}")

                mask_area = np.count_nonzero(mask_data)

                detection_dict = {
                    "id": i,
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": confidence,
                    "area1": None,
                    "area2": float(mask_area),
                    "keys": 0
                }
                detections_info.append(detection_dict)

        return detections_info

    def get_info_abels(self, results_label):
        """Extract detection information from results_label format data"""
        detections_info = []

        if not results_label:
            return detections_info

        names = results_label.get("names", {})
        boxes_data = results_label.get("boxes", [])
        masks_data = results_label.get("masks", [])
        keypoints_data = results_label.get("keypoints", [])
        obb_data = results_label.get("obb", [])

        # Process bounding box detection results
        if boxes_data:
            for i, box in enumerate(boxes_data):
                x1, y1, x2, y2 = box[:4]
                confidence = float(box[4]) if len(box) > 4 else 1.0
                class_id = int(box[5]) if len(box) > 5 else 0

                class_name = names.get(class_id, f"class_{class_id}")
                box_area = float((x2 - x1) * (y2 - y1))

                detection_dict = {
                    "id": i,
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": confidence,
                    "area1": box_area,
                    "area2": None,
                    "keys": 0
                }

                detections_info.append(detection_dict)

        # Process OBB detection results
        if obb_data:
            if not detections_info:
                for i, obb in enumerate(obb_data):
                    class_id = int(obb[0]) if len(obb) > 0 else 0
                    class_name = names.get(class_id, f"class_{class_id}")

                    if len(obb) >= 9:
                        x_coords = [obb[j] for j in range(1, len(obb), 2)]
                        y_coords = [obb[j] for j in range(2, len(obb), 2)]
                        x_min, x_max = min(x_coords), max(x_coords)
                        y_min, y_max = min(y_coords), max(y_coords)
                        obb_area = float((x_max - x_min) * (y_max - y_min))
                    else:
                        obb_area = 0.0

                    detection_dict = {
                        "id": i,
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": 1.0,
                        "area1": obb_area,
                        "area2": None,
                        "keys": 0
                    }

                    detections_info.append(detection_dict)
            else:
                for i, (detection_dict, obb) in enumerate(zip(detections_info, obb_data)):
                    if i < len(obb_data):
                        class_id = int(obb[0]) if len(obb) > 0 else detection_dict["class_id"]

                        if len(obb) >= 9:
                            x_coords = [obb[j] for j in range(1, len(obb), 2)]
                            y_coords = [obb[j] for j in range(2, len(obb), 2)]
                            x_min, x_max = min(x_coords), max(x_coords)
                            y_min, y_max = min(y_coords), max(y_coords)
                            obb_area = float((x_max - x_min) * (y_max - y_min))
                            detection_dict["area1"] = obb_area

                        if "class_id" not in detection_dict or detection_dict["class_id"] == 0:
                            detection_dict["class_id"] = class_id
                            detection_dict["class_name"] = names.get(class_id, f"class_{class_id}")

        # Process keypoint information
        if keypoints_data:
            for i, detection_dict in enumerate(detections_info):
                if i < len(keypoints_data):
                    kps = keypoints_data[i]
                    if isinstance(kps, list) and len(kps) > 0:
                        if isinstance(kps[0], list) and len(kps[0]) >= 3:
                            visible_keypoints = sum(1 for kp in kps if len(kp) >= 3 and kp[2] > 0)
                        elif len(kps) % 3 == 0:
                            visible_keypoints = sum(1 for j in range(2, len(kps), 3) if kps[j] > 0)
                        else:
                            visible_keypoints = 0
                        detection_dict["keys"] = int(visible_keypoints)

        # Process mask segmentation results
        if masks_data:
            if len(masks_data) > len(detections_info):
                for i in range(len(detections_info), len(masks_data)):
                    mask_info = masks_data[i]
                    class_id = int(mask_info[0]) if len(mask_info) > 0 else 0
                    class_name = names.get(class_id, f"class_{class_id}")

                    detection_dict = {
                        "id": i,
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": 1.0,
                        "area1": None,
                        "area2": None,
                        "keys": 0
                    }
                    detections_info.append(detection_dict)

            for i, (detection_dict, mask_info) in enumerate(zip(detections_info, masks_data)):
                if i < len(masks_data):
                    points = mask_info[1:]
                    if len(points) >= 6 and len(points) % 2 == 0:
                        x_coords = [points[j] for j in range(0, len(points), 2)]
                        y_coords = [points[j] for j in range(1, len(points), 2)]

                        n = len(x_coords)
                        area = 0.0
                        for j in range(n):
                            k = (j + 1) % n
                            area += x_coords[j] * y_coords[k]
                            area -= x_coords[k] * y_coords[j]
                        mask_area = abs(area) / 2.0
                        detection_dict["area2"] = float(mask_area)

        elif masks_data and not boxes_data and not obb_data:
            for i, mask_info in enumerate(masks_data):
                class_id = int(mask_info[0]) if len(mask_info) > 0 else 0
                class_name = names.get(class_id, f"class_{class_id}")

                points = mask_info[1:]
                mask_area = 0.0
                if len(points) >= 6 and len(points) % 2 == 0:
                    x_coords = [points[j] for j in range(0, len(points), 2)]
                    y_coords = [points[j] for j in range(1, len(points), 2)]

                    n = len(x_coords)
                    area = 0.0
                    for j in range(n):
                        k = (j + 1) % n
                        area += x_coords[j] * y_coords[k]
                        area -= x_coords[k] * y_coords[j]
                    mask_area = abs(area) / 2.0

                detection_dict = {
                    "id": i,
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": 1.0,
                    "area1": None,
                    "area2": float(mask_area),
                    "keys": 0
                }
                detections_info.append(detection_dict)

        return detections_info

    def draw_bounding_boxes(self, result, img, height, width, line_thickness, font_scale):
        """Draw bounding boxes on image"""
        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            confidences = result.boxes.conf.cpu().numpy()
            class_ids = result.boxes.cls.cpu().numpy().astype(int)

            for i in range(len(boxes)):
                x1, y1, x2, y2 = boxes[i]

                x1 = max(0, min(x1, width - 1))
                y1 = max(0, min(y1, height - 1))
                x2 = max(0, min(x2, width - 1))
                y2 = max(0, min(y2, height - 1))

                class_id = class_ids[i]
                confidence = confidences[i]
                class_name = self.names[class_id] if class_id < len(
                    self.names) else f"class_{class_id}"

                color = COLORS[(class_id + self.offset) % len(COLORS)]

                cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, line_thickness)

                label = f'{class_name} {confidence:.2f}'
                text_size = \
                    cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, max(1, line_thickness // 2))[0]
                label_bg_height = int(1.5 * text_size[-1])
                cv2.rectangle(img, (int(x1), int(y1) - label_bg_height),
                              (int(x1) + text_size[0], int(y1)), color, -1)

                cv2.putText(img, label, (int(x1), int(y1) - max(2, label_bg_height // 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), max(1, line_thickness // 2))

    def draw_bounding_mask(self, result, img, height, width, line_thickness, font_scale):
        """Draw segmentation masks on image"""
        if result.masks is not None:
            masks = result.masks.data.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy().astype(int) if result.boxes is not None else [0] * len(
                masks)

            mask_img = np.zeros_like(img)

            for i, (mask, class_id) in enumerate(zip(masks, classes)):
                mask_resized = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
                color = COLORS[(class_id + self.offset) % len(COLORS)]
                mask_bool = mask_resized > 0.5
                mask_img[mask_bool] = color

            img = cv2.addWeighted(img, 1.0, mask_img, 0.5, 0)

            if result.boxes is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                confidences = result.boxes.conf.cpu().numpy()
                class_ids = result.boxes.cls.cpu().numpy().astype(int)

                for i in range(len(boxes)):
                    x1, y1, x2, y2 = boxes[i]

                    x1 = max(0, min(x1, width - 1))
                    y1 = max(0, min(y1, height - 1))
                    x2 = max(0, min(x2, width - 1))
                    y2 = max(0, min(y2, height - 1))

                    class_id = class_ids[i]
                    confidence = confidences[i]
                    class_name = self.names[class_id] if class_id < len(
                        self.names) else f"class_{class_id}"

                    color = COLORS[(class_id + self.offset) % len(COLORS)]

                    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, line_thickness)

                    label = f'{class_name} {confidence:.2f}'
                    text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                                                max(1, line_thickness // 2))[0]
                    label_bg_height = int(1.5 * text_size[-1])
                    cv2.rectangle(img, (int(x1), int(y1) - label_bg_height),
                                  (int(x1) + text_size[0], int(y1)), color, -1)

                    cv2.putText(img, label, (int(x1), int(y1) - max(2, label_bg_height // 4)),
                                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255),
                                max(1, line_thickness // 2))
        else:
            self.draw_bounding_boxes(result, img, height, width, line_thickness, font_scale)
