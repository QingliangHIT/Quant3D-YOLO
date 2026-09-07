"""YOLO 参数面板：模型/任务选择、置信度与 IOU 阈值、点检测块大小与类别筛选。

可选项与默认值统一取自 quant.core.config.DETECTION，本文件只负责控件布局与信号。
"""

from PyQt5 import QtWidgets, QtCore

from quant.core.config import DETECTION
from quant.core.paths import MODEL_DIR
from quant.detection import model_service


class YoloDock(QtWidgets.QDockWidget):
    yolo_model_changed = QtCore.pyqtSignal(tuple)
    yolo_conf_threshold_changed = QtCore.pyqtSignal(float)
    yolo_iou_threshold_changed = QtCore.pyqtSignal(float)
    patch_size_changed = QtCore.pyqtSignal(int)
    class_filter_changed = QtCore.pyqtSignal()  # Add class filter signal

    def __init__(self, parent=None):
        super().__init__("YOLO Parameters", parent)
        self.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)
        self.classes = {}  # Store detected classes {class_name: count}
        self.setup_ui()
        self.setup_connections()
        self.patch_hide_timer = None
        self.parent = parent

    def setup_ui(self):
        # Create main widget and layout
        self.widget = QtWidgets.QWidget()
        self.setWidget(self.widget)

        # Create scroll area
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        # Create content widget
        self.content_widget = QtWidgets.QWidget()
        self.scroll_area.setWidget(self.content_widget)

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self.widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.scroll_area)

        # Content layout
        self.layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 10, 10, 10)

        # Model selection - label left, control right
        model_layout = QtWidgets.QFormLayout()
        model_layout.setLabelAlignment(QtCore.Qt.AlignLeft)
        model_layout.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        model_layout.setHorizontalSpacing(10)
        model_layout.setVerticalSpacing(5)

        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.setEditable(True)
        # 合并静态可选模型与模型目录扫描到的本地 .pt 权重
        self.model_combo.addItems(model_service.available_models())
        self.model_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.model_combo.setToolTip("Select a model, or type a name / full path")

        # 浏览按钮：手动指定任意 .pt 权重文件（可不在模型目录内）
        self.model_browse_button = QtWidgets.QPushButton("...")
        self.model_browse_button.setToolTip("Browse model file (.pt)")
        self.model_browse_button.setFixedWidth(28)

        model_row = QtWidgets.QHBoxLayout()
        model_row.setSpacing(4)
        model_row.addWidget(self.model_combo)
        model_row.addWidget(self.model_browse_button)
        model_layout.addRow("Model:\t", model_row)

        self.layout.addLayout(model_layout)

        # Task type selection: label on left, control on right
        task_layout = QtWidgets.QFormLayout()
        task_layout.setLabelAlignment(QtCore.Qt.AlignLeft)
        task_layout.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        task_layout.setHorizontalSpacing(10)
        task_layout.setVerticalSpacing(5)

        self.task_combo = QtWidgets.QComboBox()
        self.task_combo.addItems(list(DETECTION.model_tasks))
        self.task_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        task_layout.addRow("Task:\t", self.task_combo)

        self.layout.addLayout(task_layout)

        # Class filtering (new)
        class_filter_label = QtWidgets.QLabel("Classes")

        # Select all / none
        self.select_buttons_layout = QtWidgets.QHBoxLayout()
        self.select_all_button = QtWidgets.QPushButton()
        self.select_all_button.setToolTip("Select All")
        self.select_all_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton))
        self.select_all_button.setFixedSize(20, 20)
        self.select_all_button.setIconSize(QtCore.QSize(12, 12))

        self.select_none_button = QtWidgets.QPushButton()
        self.select_none_button.setToolTip("Select None")
        self.select_none_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserStop))
        self.select_none_button.setFixedSize(20, 20)
        self.select_none_button.setIconSize(QtCore.QSize(12, 12))
        #
        self.select_buttons_layout.addWidget(class_filter_label)
        self.select_buttons_layout.addStretch()
        self.select_buttons_layout.addWidget(self.select_all_button)
        self.select_buttons_layout.addWidget(self.select_none_button)
        self.layout.addLayout(self.select_buttons_layout)

        # Class list
        self.list_widget = QtWidgets.QListWidget()
        # self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)  # 禁用默认选择模式
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        # self.list_widget.able
        self.layout.addWidget(self.list_widget)

        # Parameters - grid layout for space
        self.params_group = QtWidgets.QGroupBox("Detection Parameters")
        # self.params_group.setFont(title_font)
        self.params_layout = QtWidgets.QGridLayout(self.params_group)
        self.params_layout.setSpacing(8)
        self.params_layout.setContentsMargins(10, 10, 10, 10)

        # Confidence threshold
        conf_label = QtWidgets.QLabel("Confidence:")
        conf_label.setToolTip("Minimum confidence for detections")

        self.conf_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.conf_slider.setMinimum(0)
        self.conf_slider.setMaximum(1000)
        self.conf_slider.setValue(round(DETECTION.default_conf * 1000))
        self.conf_slider.setToolTip("Adjust confidence threshold")

        self.conf_value_label = QtWidgets.QLabel(f"{DETECTION.default_conf:.3f}")
        self.conf_value_label.setMinimumWidth(40)
        self.conf_value_label.setAlignment(QtCore.Qt.AlignCenter)

        # IOU threshold
        iou_label = QtWidgets.QLabel("IOU:")
        iou_label.setToolTip("Intersection over Union threshold")

        self.iou_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.iou_slider.setMinimum(0)
        self.iou_slider.setMaximum(100)
        self.iou_slider.setValue(round(DETECTION.default_iou * 100))
        self.iou_slider.setToolTip("Adjust IOU threshold")

        self.iou_value_label = QtWidgets.QLabel(f"{DETECTION.default_iou:.2f}")
        self.iou_value_label.setMinimumWidth(40)
        self.iou_value_label.setAlignment(QtCore.Qt.AlignCenter)

        # Detection size
        patch_size_label = QtWidgets.QLabel("Patch Size:")
        patch_size_label.setToolTip("Detection patch size as percentage of image")

        self.patch_size_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.patch_size_slider.setMinimum(0)
        self.patch_size_slider.setMaximum(100)
        self.patch_size_slider.setValue(DETECTION.default_patch_percent)
        self.patch_size_slider.setToolTip("Adjust patch size for point detection")

        self.patch_size_value_label = QtWidgets.QLabel(f"{DETECTION.default_patch_percent}%")
        self.patch_size_value_label.setMinimumWidth(40)
        self.patch_size_value_label.setAlignment(QtCore.Qt.AlignCenter)

        # Max detections
        max_detections_label = QtWidgets.QLabel("Max Detections:")
        max_detections_label.setToolTip("Maximum number of detections to show")

        self.max_detections_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.max_detections_slider.setMinimum(1)
        self.max_detections_slider.setMaximum(1000)
        self.max_detections_slider.setValue(DETECTION.default_max_detections)
        self.max_detections_slider.setToolTip("Adjust maximum detections")

        self.max_detections_value_label = QtWidgets.QLabel(str(DETECTION.default_max_detections))
        self.max_detections_value_label.setMinimumWidth(40)
        self.max_detections_value_label.setAlignment(QtCore.Qt.AlignCenter)

        # Add to grid layout
        # Row 1 - Confidence
        self.params_layout.addWidget(conf_label, 0, 0)
        self.params_layout.addWidget(self.conf_slider, 0, 1)
        self.params_layout.addWidget(self.conf_value_label, 0, 2)

        # Row 2 - IOU
        self.params_layout.addWidget(iou_label, 1, 0)
        self.params_layout.addWidget(self.iou_slider, 1, 1)
        self.params_layout.addWidget(self.iou_value_label, 1, 2)

        # Row 3 - Patch size
        self.params_layout.addWidget(patch_size_label, 2, 0)
        self.params_layout.addWidget(self.patch_size_slider, 2, 1)
        self.params_layout.addWidget(self.patch_size_value_label, 2, 2)

        # Row 4 - Max detections
        self.params_layout.addWidget(max_detections_label, 3, 0)
        self.params_layout.addWidget(self.max_detections_slider, 3, 1)
        self.params_layout.addWidget(self.max_detections_value_label, 3, 2)

        # Add to main layout
        self.layout.addWidget(self.params_group)
        self.layout.addStretch()

    def setup_connections(self):
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        self.model_browse_button.clicked.connect(self.on_browse_model)
        self.task_combo.currentTextChanged.connect(self.on_task_changed)
        self.conf_slider.valueChanged.connect(self.on_conf_threshold_changed)
        self.iou_slider.valueChanged.connect(self.on_iou_threshold_changed)
        self.patch_size_slider.valueChanged.connect(self.on_patch_size_changed)
        self.max_detections_slider.valueChanged.connect(self.on_max_detections_changed)
        self.list_widget.itemChanged.connect(self.on_class_selection_changed)  # Connect class selection changed signal
        # Connect select all/none
        self.select_all_button.clicked.connect(self.select_all_classes)
        self.select_none_button.clicked.connect(self.deselect_all_classes)

    def select_all_classes(self):
        """
        Select all classes
        """
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(QtCore.Qt.Checked)

    def deselect_all_classes(self):
        """
        Deselect all classes
        """
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(QtCore.Qt.Unchecked)

    def get_selected_classes(self):
        """
        Get selected items
        """
        selected_items = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                selected_items.append(item.text())
        selected_classes = [item.split("\t")[1] for item in
                            selected_items] if self.parent.annos_dock.show_filtered else None
        return selected_classes

    def on_class_selection_changed(self):
        """
        Handle class selection change
        """
        # selected_classes = self.get_selected_classes()
        self.class_filter_changed.emit()

    def update_content(self, context, selected=None):
        """Update class list UI"""
        # Clear list
        if selected is not None:
            context = {class_name: count for class_name, count in context.items() if class_name in selected}

        self.list_widget.clear()
        self.list_widget.setVisible(True)
        # If dict, convert to string list
        if isinstance(context, dict):
            # Convert dict to formatted strings
            items = [f"{key}\t{value}" for key, value in context.items()]
            for item_text in items:
                item = QtWidgets.QListWidgetItem(item_text)
                item.setCheckState(QtCore.Qt.Checked)  # Add checkbox, checked by default
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)  # Ensure checkable
                self.list_widget.addItem(item)
        # If list or iterable
        elif hasattr(context, '__iter__') and not isinstance(context, str):
            for item_text in context:
                item = QtWidgets.QListWidgetItem(str(item_text))
                item.setCheckState(QtCore.Qt.Checked)  # Add checkbox, checked by default
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)  # Ensure checkable
                self.list_widget.addItem(item)
        # If single string
        else:
            item = QtWidgets.QListWidgetItem(str(context))
            item.setCheckState(QtCore.Qt.Checked)  # Add checkbox, checked by default
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)  # Ensure checkable
            self.list_widget.addItem(item)

    def get_classes(self, results):
        """
        Get class list
        :return: Class list
        """
        # Count all classes
        class_counts = {}

        if len(results) > 0:
            result = results[0]  # Take first result

            # Process bbox results
            if hasattr(result, 'boxes') and result.boxes is not None:
                class_ids = result.boxes.cls.cpu().numpy().astype(int)

                # Get class name map
                names = {}
                if hasattr(result, 'names'):
                    names = result.names
                elif hasattr(self.parent, 'yolo_model') and hasattr(self.parent.yolo_model, 'names'):
                    names = self.parent.yolo_model.names

                for class_id in class_ids:
                    class_name = names.get(class_id, f"class_{class_id}")
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1

            # Process mask results
            elif hasattr(result, 'masks') and result.masks is not None:
                # If has mask, may be segmentation
                if hasattr(result.boxes, 'cls'):
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)
                    names = {}
                    if hasattr(result, 'names'):
                        names = result.names
                    elif hasattr(self.parent, 'yolo_model') and hasattr(self.parent.yolo_model, 'names'):
                        names = self.parent.yolo_model.names

                    for class_id in class_ids:
                        class_name = names.get(class_id, f"class_{class_id}")
                        class_counts[class_name] = class_counts.get(class_name, 0) + 1
        return class_counts

    def get_classes_labels(self, yolo_labels):
        """
        Extract class stats from yolo_labels

        Args:
            yolo_labels (dict): Dict with boxes, masks, keypoints, obb

        Returns:
            dict: Class stats dict {class_name: count}
        """
        class_counts = {}

        # Check input valid
        if not yolo_labels:
            return class_counts

        # Extract basic info
        names = yolo_labels.get("names", {})
        boxes_data = yolo_labels.get("boxes", [])
        masks_data = yolo_labels.get("masks", [])
        obb_data = yolo_labels.get("obb", [])

        # Process bbox results
        if boxes_data:
            for box in boxes_data:
                class_id = int(box[5]) if len(box) > 5 else 0
                class_name = names.get(class_id, f"class_{class_id}")
                class_counts[class_name] = class_counts.get(class_name, 0) + 1

        # Process OBB results
        elif obb_data:
            for obb in obb_data:
                class_id = int(obb[0]) if len(obb) > 0 else 0
                class_name = names.get(class_id, f"class_{class_id}")
                class_counts[class_name] = class_counts.get(class_name, 0) + 1

        # Process mask results
        elif masks_data:
            for mask_info in masks_data:
                class_id = int(mask_info[0]) if len(mask_info) > 0 else 0
                class_name = names.get(class_id, f"class_{class_id}")
                class_counts[class_name] = class_counts.get(class_name, 0) + 1

        return class_counts

    def get_classes_ext(self, yolo_results):
        """
        Update class list from YOLO results
        :param yolo_results: YOLO results dict {file_path: results}
        """
        classes = {}
        for file_path, results in yolo_results.items():
            # Get current file class stats
            file_classes = self.get_classes_labels(results)
            # Merge into total stats
            for class_name, count in file_classes.items():
                classes[class_name] = classes.get(class_name, 0) + count
        return classes

    def on_browse_model(self):
        """打开文件对话框手动指定 .pt 权重，选中后写入模型下拉框并触发加载。"""
        start_dir = str(MODEL_DIR) if MODEL_DIR.is_dir() else ""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Model File", start_dir, "YOLO Weights (*.pt);;All Files (*)")
        if not file_path:
            return
        # 写入完整路径：resolve_weights 对含路径分隔符的值直接使用，无需再查目录
        self.model_combo.setCurrentText(file_path)

    def on_model_changed(self, model_name):
        self.yolo_model_changed.emit(('model', model_name))

    def on_task_changed(self, task_type):
        self.yolo_model_changed.emit(('task', task_type))

    def on_conf_threshold_changed(self, value):
        conf = value / 1000.0
        self.conf_value_label.setText(f"{conf:.3f}")
        self.yolo_conf_threshold_changed.emit(conf)

    def on_iou_threshold_changed(self, value):
        iou = value / 100.0
        self.iou_value_label.setText(f"{iou:.2f}")
        self.yolo_iou_threshold_changed.emit(iou)

    def on_max_detections_changed(self, value):
        self.max_detections_value_label.setText(str(value))

    def on_patch_size_changed(self, value):
        self.patch_size_value_label.setText(f"{value}%")
        # Start timer to auto-hide
        self.start_patch_hide_timer()
        # Signal emission can be added here if required
        self.patch_size_changed.emit(value)  # Emit signal to notify others

    def start_patch_hide_timer(self, delay=3000):
        """启动 patch_rect 自动隐藏定时器（毫秒）。

        当前页可能是相机页或未开页（没有 hide_patch_rect），此时不起定时器；
        旧定时器必须停掉并销毁，否则滑动滑块会不断泄漏 QTimer 并重复连接。
        """
        viewer = self.parent.tab_widget.currentWidget()
        if not hasattr(viewer, 'hide_patch_rect'):
            return

        if self.patch_hide_timer is not None:
            self.patch_hide_timer.stop()
            self.patch_hide_timer.deleteLater()

        self.patch_hide_timer = QtCore.QTimer(self)
        self.patch_hide_timer.setSingleShot(True)  # Single shot
        self.patch_hide_timer.timeout.connect(viewer.hide_patch_rect)
        self.patch_hide_timer.start(delay)

    def get_parameters(self):
        """Get current params"""
        return {
            "model": self.model_combo.currentText(),
            "task": self.task_combo.currentText(),
            "conf_threshold": self.conf_slider.value() / 1000.0,
            "iou_threshold": self.iou_slider.value() / 100.0,
            "patch_size": self.patch_size_slider.value(),
            "max_detections": self.max_detections_slider.value(),
            "classes": self.classes
        }
