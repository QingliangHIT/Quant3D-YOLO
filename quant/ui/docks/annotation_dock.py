"""标注面板：检测结果树与统计列表的宿主，具体行为分布在同目录的 annotation_* 模块。"""

from PyQt5 import QtWidgets
from quant.core.config import TASK, show_boxes, show_filtered, show_confidence, show_labels
from quant.ui.docks import annotation_ui, annotation_display, annotation_report


class AnnoDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None, expand_all=False):
        super().__init__("Annotations", parent)
        self.current_task_index = None
        self.show_filtered = show_filtered
        self.show_boxes = show_boxes
        self.show_confidence = show_confidence
        self.show_labels = show_labels
        self.parent = parent
        self.expand_all = expand_all  # Default expanded state
        self.init_ui()
        self.update_box_button_icon()
        self.update_filter_button_icon()
        self.update_task_type(TASK)

    def init_ui(self):
        annotation_ui.build_ui(self)

    def toggle_task_type(self):
        annotation_display.toggle_task_type(self)

    def update_task_type(self, task):
        annotation_display.update_task_type(self, task)

    def on_task_type_changed(self, task_type):
        annotation_display.on_task_type_changed(self, task_type)

    def get_current_task_type(self):
        return annotation_display.get_current_task_type(self)

    def update_box_button_icon(self):
        annotation_display.update_box_button_icon(self)

    def update_conf_button_icon(self):
        annotation_display.update_conf_button_icon(self)

    def update_label_button_icon(self):
        annotation_display.update_label_button_icon(self)

    def toggle_boxes(self):
        annotation_display.toggle_boxes(self)

    def toggle_confidence(self):
        annotation_display.toggle_confidence(self)

    def toggle_labels(self):
        annotation_display.toggle_labels(self)

    def update_label_display_button(self):
        annotation_display.update_label_display_button(self)

    def toggle_filter(self):
        annotation_display.toggle_filter(self)

    def update_filter_button_icon(self):
        annotation_display.update_filter_button_icon(self)

    def toggle_label_display(self):
        annotation_display.toggle_label_display(self)

    def get_labels_status(self):
        return annotation_display.get_labels_status(self)

    def toggle_expand_all(self):
        annotation_display.toggle_expand_all(self)

    def expand_all_items(self):
        annotation_display.expand_all_items(self)

    def collapse_all_items(self):
        annotation_display.collapse_all_items(self)

    @staticmethod
    def filter_detections_by_class(detections_info, selected_classes):
        return annotation_display.filter_detections_by_class(detections_info, selected_classes)

    def update_detections_info(self, detections_info):
        return annotation_report.update_detections_info(self, detections_info)

    def update_statistics(self, detections_info):
        return annotation_report.update_statistics(self, detections_info)

    def update_all_info(self, detections_info, selected_classes):
        annotation_report.update_all_info(self, detections_info, selected_classes)

    def update_annot_info(self, detections_info, selected_classes):
        return annotation_report.update_annot_info(self, detections_info, selected_classes)

    def clear_all_info(self):
        annotation_report.clear_all_info(self)

    def cleanup(self):
        """释放面板资源。"""
        self.clear_all_info()
