"""标注信息汇总：检测数量统计、类别分布与结果树内容渲染。"""

from PyQt5 import QtCore, QtWidgets


def update_detections_info(dock, detections_info):
    """
    Update detection results information
    """
    dock.detections_tree.clear()

    if not detections_info:
        item = QtWidgets.QTreeWidgetItem(["No detections", "", ""])
        dock.detections_tree.addTopLevelItem(item)
        return

    for detection in detections_info:
        # Create detection item
        detection_item = QtWidgets.QTreeWidgetItem([
            f"{detection.get('id', 'N/A')}",
            f"{detection.get('class_name', 'Unknown')}",
            f"{detection.get('confidence', 0):.3f}" if detection.get('confidence') is not None else "N/A"
        ])

        # Set bold font for detection item to highlight
        font = detection_item.font(0)
        font.setBold(False)
        detection_item.setFont(0, font)
        detection_item.setFont(1, font)
        detection_item.setFont(2, font)

        # Add detailed information
        details = [
            ("ID", str(detection.get("id", "N/A")), ""),
            ("CID", str(detection.get("class_id", "N/A")), ""),
            ("CName", detection.get("class_name", "N/A"), ""),
            ("Conf", f"{detection.get('confidence', 0):.3f}" if detection.get('confidence') is not None else "N/A",
             f"{detection.get('confidence', 0):.3f}" if detection.get('confidence') is not None else "N/A"),
            ("AB", str(detection.get("area1", "N/A")), ""),
            ("AM", str(detection.get("area2", "N/A")), ""),
            ("Keys", str(detection.get("keys", "N/A")), "")
        ]

        for key, value, conf in details:
            child_item = QtWidgets.QTreeWidgetItem([key, value, conf])
            detection_item.addChild(child_item)

        dock.detections_tree.addTopLevelItem(detection_item)

    # Expand or collapse based on saved state
    if dock.expand_all:
        dock.detections_tree.expandAll()
    # Otherwise keep collapsed state


def update_statistics(dock, detections_info):
    """
    Update statistics information
    """
    if not detections_info:
        dock.stats_text.setPlainText("No detections")
        return

    # Count detections by class
    class_counts = {}
    total_detections = len(detections_info)
    avg_confidence = 0.0
    total_area1 = 0.0
    total_area2 = 0.0
    total_keys = 0
    area1_count = 0
    area2_count = 0
    keys_count = 0

    for detection in detections_info:
        class_name = detection.get("class_name", "Unknown")
        class_counts[class_name] = class_counts.get(class_name, 0) + 1

        if "confidence" in detection:
            avg_confidence += detection["confidence"]

        if detection.get("area1") is not None:
            total_area1 += detection["area1"]
            area1_count += 1

        if detection.get("area2") is not None:
            total_area2 += detection["area2"]
            area2_count += 1

        if detection.get("keys") is not None:
            total_keys += detection["keys"]
            keys_count += 1

    if total_detections > 0:
        avg_confidence /= total_detections

    # Build statistics text
    stats_text = f"Detection Statistics\n"
    stats_text += f"=" * 30 + "\n"
    stats_text += f"Total Detections: {total_detections}\n"
    stats_text += f"Average Confidence: {avg_confidence:.3f}\n"

    if area1_count > 0:
        stats_text += f"Average Bounding Box Area: {total_area1 / area1_count:.2f}\n"
    else:
        stats_text += f"Average Bounding Box Area: N/A\n"

    if area2_count > 0:
        stats_text += f"Average Mask Area: {total_area2 / area2_count:.2f}\n"
    else:
        stats_text += f"Average Mask Area: N/A\n"

    if keys_count > 0:
        stats_text += f"Average Keypoints: {total_keys / keys_count:.1f}\n"
    else:
        stats_text += f"Average Keypoints: N/A\n"

    stats_text += f"\nDetections by Class:\n"
    stats_text += f"-" * 20 + "\n"
    for class_name, count in sorted(class_counts.items()):
        stats_text += f"{class_name}: {count}\n"

    dock.stats_text.setPlainText(stats_text)


def update_all_info(dock, detections_info, selected_classes):
    """
    Update all information (detection details and statistics)
    """
    # Filter detection results by selected classes
    if selected_classes:
        detections_info = dock.filter_detections_by_class(detections_info, selected_classes)

    dock.update_statistics(detections_info)
    dock.update_detections_info(detections_info)


def update_annot_info(dock, detections_info, selected_classes):
    """
    Update annotation information (specifically for annotation data display)
    """
    # dock.tab_widget.setCurrentIndex(1)
    dock.list_widget.clear()
    if selected_classes:
        detections_info = dock.filter_detections_by_class(detections_info, selected_classes)

    # Display statistics at the beginning of list_widget
    if not detections_info:
        item = QtWidgets.QListWidgetItem("No annotation information")
        dock.list_widget.addItem(item)
        return

    # Calculate statistics and display at the beginning
    class_counts = {}
    total_detections = len(detections_info)
    avg_confidence = 0.0
    total_area1 = 0.0
    total_area2 = 0.0
    total_keys = 0
    area1_count = 0
    area2_count = 0
    keys_count = 0

    for detection in detections_info:
        class_name = detection.get("class_name", "Unknown")
        class_counts[class_name] = class_counts.get(class_name, 0) + 1

        if "confidence" in detection:
            avg_confidence += detection["confidence"]

        if detection.get("area1") is not None:
            total_area1 += detection["area1"]
            area1_count += 1

        if detection.get("area2") is not None:
            total_area2 += detection["area2"]
            area2_count += 1

        if detection.get("keys") is not None:
            total_keys += detection["keys"]
            keys_count += 1

    if total_detections > 0:
        avg_confidence /= total_detections

    # Add statistics information at the beginning of list_widget
    stat_item = QtWidgets.QListWidgetItem("--- Statistics ---")
    stat_item.setFlags(stat_item.flags() & ~QtCore.Qt.ItemIsSelectable)
    font = stat_item.font()
    font.setBold(True)
    stat_item.setFont(font)
    dock.list_widget.addItem(stat_item)

    total_item = QtWidgets.QListWidgetItem(f"Total Detections: {total_detections}")
    total_item.setFlags(total_item.flags() & ~QtCore.Qt.ItemIsSelectable)
    dock.list_widget.addItem(total_item)

    conf_item = QtWidgets.QListWidgetItem(f"Average Confidence: {avg_confidence:.3f}")
    conf_item.setFlags(conf_item.flags() & ~QtCore.Qt.ItemIsSelectable)
    dock.list_widget.addItem(conf_item)

    if area1_count > 0:
        area1_item = QtWidgets.QListWidgetItem(f"Average Bounding Box Area: {total_area1 / area1_count:.2f}")
        area1_item.setFlags(area1_item.flags() & ~QtCore.Qt.ItemIsSelectable)
        dock.list_widget.addItem(area1_item)

    if area2_count > 0:
        area2_item = QtWidgets.QListWidgetItem(f"Average Mask Area: {total_area2 / area2_count:.2f}")
        area2_item.setFlags(area2_item.flags() & ~QtCore.Qt.ItemIsSelectable)
        dock.list_widget.addItem(area2_item)

    if keys_count > 0:
        keys_item = QtWidgets.QListWidgetItem(f"Average Keypoints: {total_keys / keys_count:.1f}")
        keys_item.setFlags(keys_item.flags() & ~QtCore.Qt.ItemIsSelectable)
        dock.list_widget.addItem(keys_item)

    # Add separator line
    separator_item = QtWidgets.QListWidgetItem("-" * 30)
    separator_item.setFlags(separator_item.flags() & ~QtCore.Qt.ItemIsSelectable)
    dock.list_widget.addItem(separator_item)

    current_task = dock.get_current_task_type()

    for i, detection in enumerate(detections_info):
        # Create annotation item text
        class_name = detection.get('class_name', 'Unknown')
        id_text = detection.get('id', i)

        # Build display text
        display_text = f"[{id_text}] {class_name}"

        if detection.get("area1") is not None:
            display_text += f" | Box Area: {detection['area1']:.2f}"
        if detection.get("area2") is not None:
            display_text += f" | Mask Area: {detection['area2']:.2f}"
        if detection.get("keys") is not None and detection["keys"] > 0:
            display_text += f" | Keypoints: {detection['keys']}"

        item = QtWidgets.QListWidgetItem(display_text)
        dock.list_widget.addItem(item)


def clear_all_info(dock):
    """
    Clear all information
    """
    dock.detections_tree.clear()
    dock.list_widget.clear()
    dock.stats_text.clear()

    # Add default items
    item = QtWidgets.QTreeWidgetItem(["No detections", "", ""])
    dock.detections_tree.addTopLevelItem(item)
    dock.stats_text.setPlainText("No detections")
