"""点击式局部检测：以图像坐标点为种子做单图/跨图 YOLO 检测。"""

import traceback

import cv2
import numpy as np
import torch
from ultralytics.engine.results import Boxes, Masks, Keypoints, OBB
from ultralytics.utils import ops

from quant.core.gpu import print_gpu_memory_usage


def rescale_patch_masks(masks, target_hw):
    """把网络输出的 patch mask 缩放到 patch 在原图中的实际尺寸。

    ultralytics 8.4 移除了 `ops.scale_image`，改用 `ops.scale_masks`（入参为 (N,C,H,W) tensor），
    两者语义与数据布局都不同，因此在此集中适配；统一返回 (N, h, w) 的 float32 数组。
    """
    scale_masks = getattr(ops, "scale_masks", None)
    if scale_masks is not None:
        tensor = torch.from_numpy(np.ascontiguousarray(masks, dtype=np.float32)).unsqueeze(1)
        scaled = scale_masks(tensor, (int(target_hw[0]), int(target_hw[1])))
        return scaled.squeeze(1).cpu().numpy().astype(np.float32)
    # 旧版 ultralytics 回退：入参 (h, w, n)，输出同布局
    scaled = ops.scale_image(masks.transpose(1, 2, 0), (int(target_hw[0]), int(target_hw[1]), masks.shape[0]))
    return np.asarray(scaled).transpose(2, 0, 1).astype(np.float32)


def perform_3d_detection(view, point_x, point_y):
    """跨所有图像做 3D 检测，找出包含指定点的目标。"""
    model = view.parent.yolo_model
    if model is None:
        view.parent.statusbar.showMessage("❌ YOLO model is not loaded", 5000)
        return 0

    yolo_params = view.parent.yolo_dock.get_parameters()
    detection_count = 0
    new_yolo_results = {}

    # Iterate through all images
    for file_path in view.parent.files_dock.file_paths:
        if view.yolo_cache and file_path in view.yolo_cache:
            img = view.yolo_cache[file_path]['img']
        else:
            img = view.image_cache[file_path] if file_path in view.image_cache else cv2.imread(file_path,
                                                                                               cv2.IMREAD_COLOR)
        if img is None:
            continue

        # Perform detection
        results = model(
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
                new_label = view.result_to_label(new_result)
                view.merge_results_label(file_path, new_label)
                labels = view.parent.plotter.get_info_abels(new_label)
                classes = view.parent.yolo_dock.get_classes_labels(new_label)

                if view.yolo_cache and file_path in view.yolo_cache:
                    classes_old = view.yolo_cache[file_path]['classes']
                    labels_old = view.yolo_cache[file_path]['labels']
                    for class_name, count in classes.items():
                        classes_old[class_name] = classes_old.get(class_name, 0) + count
                    labels = labels_old + labels
                    classes = classes_old

                selected_classes = view.parent.yolo_dock.get_selected_classes() if view.parent.annos_dock.show_filtered else None

                new_result.orig_img = img
                img = view.parent.plotter.process_mini(img, new_label, selected_classes,
                                                       show_boxes=view.parent.annos_dock.show_boxes,
                                                       show_conf=view.parent.annos_dock.show_confidence,
                                                       show_labels=view.parent.annos_dock.show_labels)
                view.yolo_cache[file_path] = {'img': img, 'labels': labels, 'classes': classes}
                del results
                # Clear CUDA cache
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            else:
                # If no box contains click point, keep original results unchanged
                pass

    view.load_image()
    view.parent.statusbar.showMessage(f"✅ 3D detection completed: Detected {detection_count} targets", 3000)
    return detection_count


def perform_local_detection(view, x, y):
    """在点击位置附近做局部检测，返回是否成功。"""
    if view.img is None or view.img[1] is None:
        view.parent.statusbar.showMessage("Please open an image first", 2000)
        return False
    model = view.parent.yolo_model
    if model is None:
        view.parent.statusbar.showMessage("❌ YOLO model is not loaded", 5000)
        return False
    try:
        # Get detection area size
        yolo_params = view.parent.yolo_dock.get_parameters()
        patch_size_percent = yolo_params.get("patch_size", 50)
        max_detections = yolo_params.get("max_detections", 50)

        file_path, img = view.img
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
            view.parent.statusbar.showMessage("Unable to extract local image", 2000)
            return False

        # Perform detection
        results = model(
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
                    patch_masks = rescale_patch_masks(masks, (y2 - y1, x2 - x1))
                    orig_masks = np.zeros((img.shape[0], img.shape[1], masks.shape[0]), dtype=np.float32)
                    orig_masks[y1:y2, x1:x2, :] = patch_masks.transpose(1, 2, 0)
                    result.masks = Masks(
                        torch.from_numpy(orig_masks.transpose(2, 0, 1)),
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
                classes = view.parent.yolo_dock.get_classes(results)
                labels = view.parent.plotter.get_info(results)
                new_results_label = view.result_to_label(result)

                if file_path in view.yolo_cache:
                    classes_old = view.yolo_cache[file_path]['classes']
                    labels_old = view.yolo_cache[file_path]['labels']
                    for class_name, count in classes.items():
                        classes_old[class_name] = classes_old.get(class_name, 0) + count
                    labels = labels_old + labels
                    classes = classes_old

                view.merge_results_label(file_path, new_results_label)
                selected_classes = view.parent.yolo_dock.get_selected_classes() if view.parent.annos_dock.show_filtered else None

                view.parent.annos_dock.update_all_info(labels, selected_classes)
                view.parent.categories_dock.update_content(classes, selected_classes)

                # Update displayed image
                results[0].orig_img = view.img[1]
                img = view.parent.plotter.process_mini(img, new_results_label, selected_classes,
                                                       show_boxes=view.parent.annos_dock.show_boxes,
                                                       show_conf=view.parent.annos_dock.show_confidence,
                                                       show_labels=view.parent.annos_dock.show_labels)
                view.img = file_path, img
                view.update_image(img)
                view.yolo_cache[file_path] = {'img': img, 'labels': labels, 'classes': classes}
                del results
                # Clear CUDA cache
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                view.parent.statusbar.showMessage(
                    f"✅ Local detection completed: Detected {detection_count} targets({ret})", 3000)
            else:
                view.parent.statusbar.showMessage("✅ Local detection completed: No targets detected", 3000)
        else:
            view.parent.statusbar.showMessage("✅ Local detection completed: No targets detected", 3000)

    except Exception as e:
        view.parent.statusbar.showMessage(f"❌ Local detection failed: {str(e)}", 5000)
        traceback.print_exc()
        return False
    return True
