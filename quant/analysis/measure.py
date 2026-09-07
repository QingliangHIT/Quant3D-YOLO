"""目标测量：单目标 2D/3D 尺寸测算与全图汇总统计。"""

import numpy as np
from PyQt5 import QtWidgets
import cv2


def measure_2d_object_info(view, img, box_idx):
    """Measure 2D object information using label dictionary format"""
    if view.img[0] not in view.yolo_results:
        return
    view.update_image(img)
    results_label = view.yolo_results[view.img[0]]

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
            elif hasattr(view.parent, 'yolo_model') and hasattr(view.parent.yolo_model, 'names'):
                class_name = view.parent.yolo_model.names.get(class_id, f"class_{class_id}")

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
                        img_h, img_w = view.img[1].shape[:2]
                        mask = np.zeros((img_h, img_w), dtype=np.uint8)
                        poly_points = []
                        for i in range(0, len(points), 2):
                            poly_points.append([int(points[i]), int(points[i + 1])])
                        if len(poly_points) >= 3:
                            poly_points = np.array(poly_points, dtype=np.int32)
                            cv2.fillPoly(mask, [poly_points], 1)
                            mask_area = np.count_nonzero(mask)

            # Get scale information (if exists)
            dx = getattr(view, 'dx', 1.0)
            dy = getattr(view, 'dy', 1.0)

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
            msg_box = QtWidgets.QMessageBox(view.parent)
            msg_box.setWindowTitle("2D Object Measurement Information")
            msg_box.setText(info_text)
            msg_box.finished.connect(view.load_image)
            msg_box.exec_()


def measure_3d_object_info(view, img, box_idx):
    """Measure 3D object information using label dictionary format"""
    # Find targets containing same area in all images
    target_boxes = []  # Store matching target boxes from all images

    # Get current image target box coordinates
    if view.img[0] not in view.yolo_results:
        return

    view.update_image(img)
    current_results_label = view.yolo_results[view.img[0]]
    if "boxes" not in current_results_label or not current_results_label["boxes"]:
        return

    current_boxes = current_results_label["boxes"]
    if box_idx >= len(current_boxes):
        return

    # Get current target box
    current_box = current_boxes[box_idx]
    x1, y1, x2, y2 = current_box[0], current_box[1], current_box[2], current_box[3]

    # Find matching targets in all images
    for file_path in view.parent.files_dock.file_paths:
        if file_path in view.yolo_results:
            results_label = view.yolo_results[file_path]
            if "boxes" in results_label and results_label["boxes"]:
                boxes = results_label["boxes"]
                # Find targets overlapping with current target
                for i, box in enumerate(boxes):
                    # Simple overlap check
                    box_x1, box_y1, box_x2, box_y2 = box[0], box[1], box[2], box[3]
                    if view.boxes_overlap((x1, y1, x2, y2), (box_x1, box_y1, box_x2, box_y2)):
                        target_boxes.append({
                            'file_path': file_path,
                            'box_index': i,
                            'box_coords': box,
                            'results_label': results_label
                        })
                        break  # Take only one matching target per image

    if not target_boxes:
        QtWidgets.QMessageBox.warning(view.parent, "Measurement Information",
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
                        img_h, img_w = view.img[1].shape[:2]  # Use current image shape as approximation
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
    dx = getattr(view, 'dx', 1.0)
    dy = getattr(view, 'dy', 1.0)
    dz = getattr(view, 'dz', 1.0)

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
                elif hasattr(view.parent, 'yolo_model') and hasattr(view.parent.yolo_model, 'names'):
                    class_name = view.parent.yolo_model.names.get(class_id, f"class_{class_id}")

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
    msg_box = QtWidgets.QMessageBox(view.parent)
    msg_box.setWindowTitle("3D Object Measurement Information")
    msg_box.setText(info_text)
    msg_box.finished.connect(view.load_image)
    msg_box.exec_()


def total_2d_info(view):
    """
    Statistics of all 2D targets in current image, including area-related information
    And display measurement results, supporting class filtering
    """
    if view.img[0] not in view.yolo_results:
        return

    results_label = view.yolo_results[view.img[0]]

    # Get bounding box coordinates
    if "boxes" in results_label and results_label["boxes"] is not None:
        boxes = results_label["boxes"]

        # Get selected class list
        selected_classes = []
        if hasattr(view.parent, 'yolo_dock') and view.parent.yolo_dock and \
                hasattr(view.parent.yolo_dock, 'get_selected_classes'):
            classes = view.parent.yolo_dock.get_selected_classes()
            if "names" in results_label and hasattr(view.parent.plotter, 'index'):
                index = view.parent.plotter.index
                selected_classes = [int(index[name]) for name in classes if name in index]

        # Initialize statistics variables
        total_objects = 0
        total_bbox_area = 0
        total_mask_area = 0
        has_masks = "masks" in results_label and results_label["masks"] is not None

        # Get scale information (if exists)
        dx = getattr(view, 'dx', 1.0)
        dy = getattr(view, 'dy', 1.0)

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
                        img_h, img_w = view.img[1].shape[:2]
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
                QtWidgets.QMessageBox.information(view.parent, "Prompt", "No targets found in selected classes")
            else:
                QtWidgets.QMessageBox.information(view.parent, "Prompt", "No targets found")
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
        msg_box = QtWidgets.QMessageBox(view.parent)
        msg_box.setWindowTitle("2D Object Total Measurement Information")
        msg_box.setText(info_text)
        msg_box.exec_()


def total_3d_info(view):
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
    selected_classes = view.parent.yolo_dock.get_selected_classes() if view.parent.annos_dock.show_filtered else None

    # Get scale information (if exists)
    dx = getattr(view, 'dx', 1.0)
    dy = getattr(view, 'dy', 1.0)
    dz = getattr(view, 'dz', 1.0)

    # Iterate through results of all images
    for file_path in view.parent.files_dock.file_paths:
        if file_path in view.yolo_results:
            results_label = view.yolo_results[file_path]
            if "boxes" in results_label and results_label["boxes"] is not None:
                boxes = results_label["boxes"]

                # Build class index mapping if needed
                class_index_map = {}
                if "names" in results_label and hasattr(view.parent.plotter, 'index'):
                    class_index_map = view.parent.plotter.index

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
                                    img_h, img_w = view.img[1].shape[:2]  # Approximate with current image size
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
            QtWidgets.QMessageBox.warning(view.parent, "Measurement Information",
                                          "No targets found in selected classes")
        else:
            QtWidgets.QMessageBox.warning(view.parent, "Measurement Information", "No targets found")
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
    msg_box = QtWidgets.QMessageBox(view.parent)
    msg_box.setWindowTitle("3D Object Total Measurement Information")
    msg_box.setText(info_text)
    msg_box.exec_()
