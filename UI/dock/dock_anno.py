from PyQt5 import QtCore, QtWidgets
from UI.control.config import TASK
from UI.control.config import show_boxes, show_filtered, show_confidence, show_labels


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
        self.setMinimumSize(QtCore.QSize(200, 100))
        self.setFeatures(QtWidgets.QDockWidget.AllDockWidgetFeatures)

        # Create content widget
        self.annos_content = QtWidgets.QWidget()
        self.annos_layout = QtWidgets.QVBoxLayout(self.annos_content)
        self.annos_layout.setContentsMargins(5, 5, 5, 5)
        self.annos_layout.setSpacing(2)

        # Create expand button
        self.expand_button = QtWidgets.QPushButton()
        self.expand_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowDown))
        self.expand_button.setToolTip("Expand All")
        self.expand_button.setFixedSize(20, 20)
        self.expand_button.setIconSize(QtCore.QSize(12, 12))
        # Create collapse button
        self.collapse_button = QtWidgets.QPushButton()
        self.collapse_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowUp))
        self.collapse_button.setToolTip("Collapse All")
        self.collapse_button.setFixedSize(20, 20)
        self.collapse_button.setIconSize(QtCore.QSize(12, 12))
        # Create task toggle button
        self.task_toggle_button = QtWidgets.QPushButton()
        self.task_toggle_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        # self.task_toggle_button.setToolTip("Switch Task (Current: detect)")
        self.task_toggle_button.setFixedSize(20, 20)
        self.task_toggle_button.setIconSize(QtCore.QSize(12, 12))
        # Create labels-display control button
        self.filter_button = QtWidgets.QPushButton()
        self.filter_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))
        self.filter_button.setToolTip("Filter Display")
        self.filter_button.setFixedSize(20, 20)
        self.filter_button.setIconSize(QtCore.QSize(12, 12))
        self.box_button = QtWidgets.QPushButton()
        self.box_button.setFixedSize(20, 20)
        self.box_button.setIconSize(QtCore.QSize(12, 12))
        self.box_button.setToolTip("Toggle Bounding Boxes")
        self.update_box_button_icon()
        self.conf_button = QtWidgets.QPushButton()
        self.conf_button.setFixedSize(20, 20)
        self.conf_button.setIconSize(QtCore.QSize(12, 12))
        self.conf_button.setToolTip("Toggle Confidence Display")
        self.update_conf_button_icon()
        self.label_button = QtWidgets.QPushButton()
        self.label_button.setFixedSize(20, 20)
        self.label_button.setIconSize(QtCore.QSize(12, 12))
        self.label_button.setToolTip("Toggle Label Display")
        self.update_label_button_icon()

        # Connect signals
        self.expand_button.clicked.connect(self.expand_all_items)
        self.collapse_button.clicked.connect(self.collapse_all_items)
        self.task_toggle_button.clicked.connect(self.toggle_task_type)
        self.filter_button.clicked.connect(self.toggle_filter)
        self.box_button.clicked.connect(self.toggle_boxes)
        self.conf_button.clicked.connect(self.toggle_confidence)
        self.label_button.clicked.connect(self.toggle_labels)

        # Create button frame
        self.button_frame = QtWidgets.QFrame()
        self.button_frame.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Raised)
        self.button_frame_layout = QtWidgets.QHBoxLayout(self.button_frame)
        self.button_frame_layout.setContentsMargins(2, 2, 2, 2)
        self.button_frame_layout.setSpacing(5)
        self.button_frame_layout.addWidget(self.expand_button)
        self.button_frame_layout.addWidget(self.collapse_button)
        self.button_frame_layout.addStretch()
        self.button_frame_layout.addWidget(self.task_toggle_button)
        self.button_frame_layout.addWidget(self.filter_button)
        self.button_frame_layout.addWidget(self.box_button)
        self.button_frame_layout.addWidget(self.conf_button)
        self.button_frame_layout.addWidget(self.label_button)
        # Add buttons to frame
        self.annos_layout.addWidget(self.button_frame)

        # Create tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        self.annos_layout.addWidget(self.tab_widget)

        # Create detections tab
        self.detections_tab = QtWidgets.QWidget()
        self.detections_layout = QtWidgets.QVBoxLayout(self.detections_tab)

        # Create tree widget to display detection results
        self.detections_tree = QtWidgets.QTreeWidget()
        self.detections_tree.setHeaderLabels(["Property", "Class", "Confidence"])
        self.detections_tree.setAlternatingRowColors(True)

        # Disable auto-resizing of columns, use fixed column widths
        self.detections_tree.header().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

        # Set default column widths
        self.detections_tree.setColumnWidth(0, 100)  # Property column
        self.detections_tree.setColumnWidth(1, 80)   # Value column
        self.detections_tree.setColumnWidth(2, 80)   # Confidence column

        self.detections_layout.addWidget(self.detections_tree)

        self.tab_widget.addTab(self.detections_tab, "Detections")

        # Create annotations list tab
        self.annotations_tab = QtWidgets.QWidget()
        self.annotations_layout = QtWidgets.QVBoxLayout(self.annotations_tab)

        # Task type list
        self.task_types = ["detect", "segment", "obb", "pose", "auto"]
        self.current_task_index = 4
        # Label display modes: 0=none, 1=labels only, 2=labels+confidence
        self.label_display_modes = ["None", "Boxex", "Labels", "Conf"]
        self.current_label_display_index = 0  # 默认显示标签和置信度

        # Create list widget to display annotation items
        self.list_widget = QtWidgets.QListWidget()
        self.annotations_layout.addWidget(self.list_widget)

        # Create statistics tab
        self.stats_tab = QtWidgets.QWidget()
        self.stats_layout = QtWidgets.QVBoxLayout(self.stats_tab)

        self.stats_text = QtWidgets.QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_layout.addWidget(self.stats_text)

        self.tab_widget.addTab(self.stats_tab, "Statistics")
        self.tab_widget.addTab(self.annotations_tab, "Annotations")

        # Set dock widget content
        self.setWidget(self.annos_content)

    def toggle_task_type(self):
        """
        Toggle task type
        """
        # Switch to next task type
        self.current_task_index = (self.current_task_index + 1) % len(self.task_types)
        current_task = self.task_types[self.current_task_index]

        # Update button tooltip
        self.task_toggle_button.setToolTip(f"Switch Task (Current: {current_task})")

        # Show current task type in status bar
        if self.parent and hasattr(self.parent, 'statusbar'):
            self.parent.statusbar.showMessage(f"Task switched to: {current_task}", 2000)

    def update_task_type(self, task):
        """
        Update task type
        """
        # Get current task type
        if isinstance(task, int):
            self.current_task_index = task
        else:
            self.current_task_index = self.task_types.index(task)
        if not isinstance(self.current_task_index, int) or self.current_task_index < 0:
            self.current_task_index = 0
        current_task = self.get_current_task_type()
        # Update button tooltip
        self.task_toggle_button.setToolTip(f"Switch Task (Current: {current_task})")

        # Show current task type in status bar
        if self.parent and hasattr(self.parent, 'statusbar'):
            self.parent.statusbar.showMessage(f"Task switched to: {current_task}", 2000)

    def on_task_type_changed(self, task_type):
        """
        Handler when task type changes
        """
        pass

    def get_current_task_type(self):
        """
        Get current selected task type
        """
        return self.task_types[self.current_task_index]

    def update_box_button_icon(self):
        """
        Update bounding box button icon
        """
        if self.show_boxes:
            self.box_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
        else:
            self.box_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))
        self.box_button.setToolTip("Boxes Display: ON" if self.show_boxes else "Boxes Display: OFF")
        self.parent.statusbar.showMessage("Boxes Display: ON" if self.show_boxes else "Boxes Display: OFF", 2000)

    def update_conf_button_icon(self):
        """
        Update confidence button icon
        """
        if self.show_confidence:
            self.conf_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
        else:
            self.conf_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))
        self.conf_button.setToolTip("Confidence Display: ON" if self.show_confidence else "Confidence Display: OFF")
        self.parent.statusbar.showMessage("Confidence Display: ON" if self.show_confidence else "Confidence Display: OFF", 2000)

    def update_label_button_icon(self):
        """
        Update label button icon
        """
        if self.show_labels:
            self.label_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
        else:
            self.label_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))
        self.label_button.setToolTip("Labels Display: ON" if self.show_labels else "Labels Display: OFF")
        self.parent.statusbar.showMessage("Labels Display: ON" if self.show_labels else "Labels Display: OFF", 2000)

    def toggle_boxes(self):
        """
        Toggle bounding box display
        """
        self.show_boxes = not self.show_boxes
        self.update_box_button_icon()

    def toggle_confidence(self):
        """
        Toggle confidence display
        """
        self.show_confidence = not self.show_confidence
        self.update_conf_button_icon()

    def toggle_labels(self):
        """
        Toggle label display
        """
        self.show_labels = not self.show_labels
        self.update_label_button_icon()

    def update_label_display_button(self):
        """
        Update label display button icon and tooltip
        """
        current_mode = self.label_display_modes[self.current_label_display_index]
        self.labels_button.setToolTip(f"Label Display: {current_mode}")

        # Set different icons based on current mode
        if current_mode == "None":
            # Use close icon
            self.labels_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        elif current_mode == "Labels":
            # Use label icon
            self.labels_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView))
        elif current_mode == "Labels+Conf":
            # Use information icon
            self.labels_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation))

    def toggle_filter(self):
        """
        Toggle filter display
        """
        self.show_filtered = not self.show_filtered
        self.update_filter_button_icon()

    def update_filter_button_icon(self):
        # Set different icons based on filter state
        if self.show_filtered:
            self.filter_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
        else:
            self.filter_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))

        self.filter_button.setToolTip("Filter Display: ON" if self.show_filtered else "Filter Display: OFF")
        self.parent.statusbar.showMessage("Filter Display: ON" if self.show_filtered else "Filter Display: OFF", 2000)

    def toggle_label_display(self):
        """
        Toggle label display mode (similar to toggle_task_type implementation)
        """
        # Switch to next display mode
        self.current_label_display_index = (self.current_label_display_index + 1) % len(self.label_display_modes)
        current_mode = self.label_display_modes[self.current_label_display_index]

        # Update button icon and tooltip
        self.update_label_display_button()

        # Show current mode in status bar
        if self.parent and hasattr(self.parent, 'statusbar'):
            self.parent.statusbar.showMessage(f"Label display mode: {current_mode}", 2000)

    def get_labels_status(self):
        """
        Get label display status
        :return: dict containing label display settings
        """
        current_mode = self.label_display_modes[self.current_label_display_index]
        return {
            "show_confidence": current_mode == "Labels+Conf",
            "show_labels": current_mode in ["Labels", "Labels+Conf"]
        }

    def toggle_expand_all(self):
        """Toggle expand/collapse state"""
        self.expand_all = not self.expand_all
        if self.expand_all:
            self.detections_tree.expandAll()
        else:
            self.detections_tree.collapseAll()

    def expand_all_items(self):
        """Expand all items"""
        self.expand_all = True
        self.detections_tree.expandAll()

    def collapse_all_items(self):
        """Collapse all items"""
        self.expand_all = False
        self.detections_tree.collapseAll()

    @staticmethod
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

    def update_detections_info(self, detections_info):
        """
        Update detection results information
        """
        self.detections_tree.clear()

        if not detections_info:
            item = QtWidgets.QTreeWidgetItem(["No detections", "", ""])
            self.detections_tree.addTopLevelItem(item)
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

            self.detections_tree.addTopLevelItem(detection_item)

        # Expand or collapse based on saved state
        if self.expand_all:
            self.detections_tree.expandAll()
        # Otherwise keep collapsed state

    def update_statistics(self, detections_info):
        """
        Update statistics information
        """
        if not detections_info:
            self.stats_text.setPlainText("No detections")
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

        self.stats_text.setPlainText(stats_text)

    def update_all_info(self, detections_info, selected_classes):
        """
        Update all information (detection details and statistics)
        """
        # Filter detection results by selected classes
        if selected_classes:
            detections_info = self.filter_detections_by_class(detections_info, selected_classes)

        self.update_statistics(detections_info)
        self.update_detections_info(detections_info)

    def update_annot_info(self, detections_info, selected_classes):
        """
        Update annotation information (specifically for annotation data display)
        """
        # self.tab_widget.setCurrentIndex(1)
        self.list_widget.clear()
        if selected_classes:
            detections_info = self.filter_detections_by_class(detections_info, selected_classes)

        # Display statistics at the beginning of list_widget
        if not detections_info:
            item = QtWidgets.QListWidgetItem("No annotation information")
            self.list_widget.addItem(item)
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
        self.list_widget.addItem(stat_item)

        total_item = QtWidgets.QListWidgetItem(f"Total Detections: {total_detections}")
        total_item.setFlags(total_item.flags() & ~QtCore.Qt.ItemIsSelectable)
        self.list_widget.addItem(total_item)

        conf_item = QtWidgets.QListWidgetItem(f"Average Confidence: {avg_confidence:.3f}")
        conf_item.setFlags(conf_item.flags() & ~QtCore.Qt.ItemIsSelectable)
        self.list_widget.addItem(conf_item)

        if area1_count > 0:
            area1_item = QtWidgets.QListWidgetItem(f"Average Bounding Box Area: {total_area1 / area1_count:.2f}")
            area1_item.setFlags(area1_item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.list_widget.addItem(area1_item)

        if area2_count > 0:
            area2_item = QtWidgets.QListWidgetItem(f"Average Mask Area: {total_area2 / area2_count:.2f}")
            area2_item.setFlags(area2_item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.list_widget.addItem(area2_item)

        if keys_count > 0:
            keys_item = QtWidgets.QListWidgetItem(f"Average Keypoints: {total_keys / keys_count:.1f}")
            keys_item.setFlags(keys_item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.list_widget.addItem(keys_item)

        # Add separator line
        separator_item = QtWidgets.QListWidgetItem("-" * 30)
        separator_item.setFlags(separator_item.flags() & ~QtCore.Qt.ItemIsSelectable)
        self.list_widget.addItem(separator_item)

        current_task = self.get_current_task_type()

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
            self.list_widget.addItem(item)

    def clear_all_info(self):
        """
        Clear all information
        """
        self.detections_tree.clear()
        self.list_widget.clear()
        self.stats_text.clear()

        # Add default items
        item = QtWidgets.QTreeWidgetItem(["No detections", "", ""])
        self.detections_tree.addTopLevelItem(item)
        self.stats_text.setPlainText("No detections")

    def cleanup(self):
        """
        Clean up resources
        """
        self.clear_all_info()
