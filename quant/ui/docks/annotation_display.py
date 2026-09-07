"""标注显示开关：任务类型切换、检测框/置信度/标签可见性、类别筛选与展开折叠。"""

from PyQt5 import QtWidgets


def toggle_task_type(dock):
    """
    Toggle task type
    """
    # Switch to next task type
    dock.current_task_index = (dock.current_task_index + 1) % len(dock.task_types)
    current_task = dock.task_types[dock.current_task_index]

    # Update button tooltip
    dock.task_toggle_button.setToolTip(f"Switch Task (Current: {current_task})")

    # Show current task type in status bar
    if dock.parent and hasattr(dock.parent, 'statusbar'):
        dock.parent.statusbar.showMessage(f"Task switched to: {current_task}", 2000)


def update_task_type(dock, task):
    """切换标注面板的任务档位，task 可为档位下标或任务名。"""
    # Get current task type
    if isinstance(task, int):
        dock.current_task_index = task
    elif task in dock.task_types:
        dock.current_task_index = dock.task_types.index(task)
    else:
        # 模型任务名可能是不在档位表中的取值（如 classify），退回首档而不是抛 ValueError
        dock.current_task_index = 0
    if not 0 <= dock.current_task_index < len(dock.task_types):
        dock.current_task_index = 0
    current_task = dock.get_current_task_type()
    # Update button tooltip
    dock.task_toggle_button.setToolTip(f"Switch Task (Current: {current_task})")

    # Show current task type in status bar
    if dock.parent and hasattr(dock.parent, 'statusbar'):
        dock.parent.statusbar.showMessage(f"Task switched to: {current_task}", 2000)


def on_task_type_changed(dock, task_type):
    """
    Handler when task type changes
    """
    pass


def get_current_task_type(dock):
    """
    Get current selected task type
    """
    return dock.task_types[dock.current_task_index]


def update_box_button_icon(dock):
    """
    Update bounding box button icon
    """
    if dock.show_boxes:
        dock.box_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
    else:
        dock.box_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))
    dock.box_button.setToolTip("Boxes Display: ON" if dock.show_boxes else "Boxes Display: OFF")
    dock.parent.statusbar.showMessage("Boxes Display: ON" if dock.show_boxes else "Boxes Display: OFF", 2000)


def update_conf_button_icon(dock):
    """
    Update confidence button icon
    """
    if dock.show_confidence:
        dock.conf_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
    else:
        dock.conf_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))
    dock.conf_button.setToolTip("Confidence Display: ON" if dock.show_confidence else "Confidence Display: OFF")
    dock.parent.statusbar.showMessage("Confidence Display: ON" if dock.show_confidence else "Confidence Display: OFF", 2000)


def update_label_button_icon(dock):
    """
    Update label button icon
    """
    if dock.show_labels:
        dock.label_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
    else:
        dock.label_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))
    dock.label_button.setToolTip("Labels Display: ON" if dock.show_labels else "Labels Display: OFF")
    dock.parent.statusbar.showMessage("Labels Display: ON" if dock.show_labels else "Labels Display: OFF", 2000)


def toggle_boxes(dock):
    """
    Toggle bounding box display
    """
    dock.show_boxes = not dock.show_boxes
    dock.update_box_button_icon()


def toggle_confidence(dock):
    """
    Toggle confidence display
    """
    dock.show_confidence = not dock.show_confidence
    dock.update_conf_button_icon()


def toggle_labels(dock):
    """
    Toggle label display
    """
    dock.show_labels = not dock.show_labels
    dock.update_label_button_icon()


def update_label_display_button(dock):
    """
    Update label display button icon and tooltip
    """
    current_mode = dock.label_display_modes[dock.current_label_display_index]
    dock.labels_button.setToolTip(f"Label Display: {current_mode}")

    # Set different icons based on current mode
    if current_mode == "None":
        # Use close icon
        dock.labels_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
    elif current_mode == "Labels":
        # Use label icon
        dock.labels_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView))
    elif current_mode == "Labels+Conf":
        # Use information icon
        dock.labels_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation))


def toggle_filter(dock):
    """
    Toggle filter display
    """
    dock.show_filtered = not dock.show_filtered
    dock.update_filter_button_icon()


def update_filter_button_icon(dock):
    # Set different icons based on filter state
    if dock.show_filtered:
        dock.filter_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
    else:
        dock.filter_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))

    dock.filter_button.setToolTip("Filter Display: ON" if dock.show_filtered else "Filter Display: OFF")
    dock.parent.statusbar.showMessage("Filter Display: ON" if dock.show_filtered else "Filter Display: OFF", 2000)


def toggle_label_display(dock):
    """
    Toggle label display mode (similar to toggle_task_type implementation)
    """
    # Switch to next display mode
    dock.current_label_display_index = (dock.current_label_display_index + 1) % len(dock.label_display_modes)
    current_mode = dock.label_display_modes[dock.current_label_display_index]

    # Update button icon and tooltip
    dock.update_label_display_button()

    # Show current mode in status bar
    if dock.parent and hasattr(dock.parent, 'statusbar'):
        dock.parent.statusbar.showMessage(f"Label display mode: {current_mode}", 2000)


def get_labels_status(dock):
    """
    Get label display status
    :return: dict containing label display settings
    """
    current_mode = dock.label_display_modes[dock.current_label_display_index]
    return {
        "show_confidence": current_mode == "Labels+Conf",
        "show_labels": current_mode in ["Labels", "Labels+Conf"]
    }


def toggle_expand_all(dock):
    """Toggle expand/collapse state"""
    dock.expand_all = not dock.expand_all
    if dock.expand_all:
        dock.detections_tree.expandAll()
    else:
        dock.detections_tree.collapseAll()


def expand_all_items(dock):
    """Expand all items"""
    dock.expand_all = True
    dock.detections_tree.expandAll()


def collapse_all_items(dock):
    """Collapse all items"""
    dock.expand_all = False
    dock.detections_tree.collapseAll()


def filter_detections_by_class(detections_info, selected_classes):
    """
    Filter detection results by selected classes
    :param detections_info: All detection results
    :param selected_classes: List of selected classes
    :return: Filtered detection results
    """
    filtered_detections = []
    for detection in detections_info:
        if detection.get('class_name') in selected_classes:
            filtered_detections.append(detection)

    return filtered_detections
