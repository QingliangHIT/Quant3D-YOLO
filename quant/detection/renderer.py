"""标注渲染器门面。

YOLOPlotter 只保存渲染状态（任务类型、类别名、色偏），
具体绘制委托 quant.imaging.annotation，结果解析委托 quant.detection.result_codec。
"""
from __future__ import annotations

from quant.detection.result_codec import filter_results_label, summarize_label, summarize_results
from quant.imaging.annotation import render_annotation


class YOLOPlotter:
    """检测结果渲染与统计的统一入口。"""

    def __init__(self, task: str = "detect", names=None):
        self.task = task
        self.offset = 0
        self.names = {} if names is None else names
        self.index = {name: i for (i, name) in self.names.items()} if self.names else {}

    # -- 渲染 ---------------------------------------------------------------
    def process_mini(self, img, results_label, classes_names=None,
                     show_boxes=True, show_conf=False, show_labels=False):
        """按当前状态把 results_label 绘制到 img 上。"""
        names = results_label.get("names", self.names)
        if isinstance(classes_names, list) and classes_names and names:
            results_label = filter_results_label(results_label, self.names, classes_names)
        return render_annotation(
            img, results_label, self.names, self.task, self.offset,
            show_boxes=show_boxes, show_conf=show_conf, show_labels=show_labels,
        )

    # -- 过滤与统计 ---------------------------------------------------------
    def filter_results_label(self, yolo_labels, classes_names=None):
        return filter_results_label(yolo_labels, self.names, classes_names)

    def get_info(self, results):
        return summarize_results(results, self.names)

    def get_info_abels(self, results_label):
        return summarize_label(results_label)


# 语义化别名（新代码推荐使用）
AnnotationRenderer = YOLOPlotter
