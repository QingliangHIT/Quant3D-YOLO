"""标注面板构建：任务类型与显示开关按钮、检测结果树与信号连接。"""

from PyQt5 import QtCore, QtWidgets

from quant.core.config import DETECTION


def build_ui(dock):
    dock.setMinimumSize(QtCore.QSize(200, 100))
    dock.setFeatures(QtWidgets.QDockWidget.AllDockWidgetFeatures)

    # Create content widget
    dock.annos_content = QtWidgets.QWidget()
    dock.annos_layout = QtWidgets.QVBoxLayout(dock.annos_content)
    dock.annos_layout.setContentsMargins(5, 5, 5, 5)
    dock.annos_layout.setSpacing(2)

    # Create expand button
    dock.expand_button = QtWidgets.QPushButton()
    dock.expand_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_ArrowDown))
    dock.expand_button.setToolTip("Expand All")
    dock.expand_button.setFixedSize(20, 20)
    dock.expand_button.setIconSize(QtCore.QSize(12, 12))
    # Create collapse button
    dock.collapse_button = QtWidgets.QPushButton()
    dock.collapse_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_ArrowUp))
    dock.collapse_button.setToolTip("Collapse All")
    dock.collapse_button.setFixedSize(20, 20)
    dock.collapse_button.setIconSize(QtCore.QSize(12, 12))
    # Create task toggle button
    dock.task_toggle_button = QtWidgets.QPushButton()
    dock.task_toggle_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
    # dock.task_toggle_button.setToolTip("Switch Task (Current: detect)")
    dock.task_toggle_button.setFixedSize(20, 20)
    dock.task_toggle_button.setIconSize(QtCore.QSize(12, 12))
    # Create labels-display control button
    dock.filter_button = QtWidgets.QPushButton()
    dock.filter_button.setIcon(dock.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))
    dock.filter_button.setToolTip("Filter Display")
    dock.filter_button.setFixedSize(20, 20)
    dock.filter_button.setIconSize(QtCore.QSize(12, 12))
    dock.box_button = QtWidgets.QPushButton()
    dock.box_button.setFixedSize(20, 20)
    dock.box_button.setIconSize(QtCore.QSize(12, 12))
    dock.box_button.setToolTip("Toggle Bounding Boxes")
    dock.update_box_button_icon()
    dock.conf_button = QtWidgets.QPushButton()
    dock.conf_button.setFixedSize(20, 20)
    dock.conf_button.setIconSize(QtCore.QSize(12, 12))
    dock.conf_button.setToolTip("Toggle Confidence Display")
    dock.update_conf_button_icon()
    dock.label_button = QtWidgets.QPushButton()
    dock.label_button.setFixedSize(20, 20)
    dock.label_button.setIconSize(QtCore.QSize(12, 12))
    dock.label_button.setToolTip("Toggle Label Display")
    dock.update_label_button_icon()

    # Connect signals
    dock.expand_button.clicked.connect(dock.expand_all_items)
    dock.collapse_button.clicked.connect(dock.collapse_all_items)
    dock.task_toggle_button.clicked.connect(dock.toggle_task_type)
    dock.filter_button.clicked.connect(dock.toggle_filter)
    dock.box_button.clicked.connect(dock.toggle_boxes)
    dock.conf_button.clicked.connect(dock.toggle_confidence)
    dock.label_button.clicked.connect(dock.toggle_labels)

    # Create button frame
    dock.button_frame = QtWidgets.QFrame()
    dock.button_frame.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Raised)
    dock.button_frame_layout = QtWidgets.QHBoxLayout(dock.button_frame)
    dock.button_frame_layout.setContentsMargins(2, 2, 2, 2)
    dock.button_frame_layout.setSpacing(5)
    dock.button_frame_layout.addWidget(dock.expand_button)
    dock.button_frame_layout.addWidget(dock.collapse_button)
    dock.button_frame_layout.addStretch()
    dock.button_frame_layout.addWidget(dock.task_toggle_button)
    dock.button_frame_layout.addWidget(dock.filter_button)
    dock.button_frame_layout.addWidget(dock.box_button)
    dock.button_frame_layout.addWidget(dock.conf_button)
    dock.button_frame_layout.addWidget(dock.label_button)
    # Add buttons to frame
    dock.annos_layout.addWidget(dock.button_frame)

    # Create tab widget
    dock.tab_widget = QtWidgets.QTabWidget()
    dock.annos_layout.addWidget(dock.tab_widget)

    # Create detections tab
    dock.detections_tab = QtWidgets.QWidget()
    dock.detections_layout = QtWidgets.QVBoxLayout(dock.detections_tab)

    # Create tree widget to display detection results
    dock.detections_tree = QtWidgets.QTreeWidget()
    dock.detections_tree.setHeaderLabels(["Property", "Class", "Confidence"])
    dock.detections_tree.setAlternatingRowColors(True)

    # Disable auto-resizing of columns, use fixed column widths
    dock.detections_tree.header().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

    # Set default column widths
    dock.detections_tree.setColumnWidth(0, 100)  # Property column
    dock.detections_tree.setColumnWidth(1, 80)   # Value column
    dock.detections_tree.setColumnWidth(2, 80)   # Confidence column

    dock.detections_layout.addWidget(dock.detections_tree)

    dock.tab_widget.addTab(dock.detections_tab, "Detections")

    # Create annotations list tab
    dock.annotations_tab = QtWidgets.QWidget()
    dock.annotations_layout = QtWidgets.QVBoxLayout(dock.annotations_tab)

    # Task type list
    dock.task_types = list(DETECTION.annotation_tasks)
    dock.current_task_index = dock.task_types.index(DETECTION.default_task)
    # Label display modes: 0=none, 1=labels only, 2=labels+confidence
    dock.label_display_modes = ["None", "Boxex", "Labels", "Conf"]
    dock.current_label_display_index = 0  # 默认显示标签和置信度

    # Create list widget to display annotation items
    dock.list_widget = QtWidgets.QListWidget()
    dock.annotations_layout.addWidget(dock.list_widget)

    # Create statistics tab
    dock.stats_tab = QtWidgets.QWidget()
    dock.stats_layout = QtWidgets.QVBoxLayout(dock.stats_tab)

    dock.stats_text = QtWidgets.QTextEdit()
    dock.stats_text.setReadOnly(True)
    dock.stats_layout.addWidget(dock.stats_text)

    dock.tab_widget.addTab(dock.stats_tab, "Statistics")
    dock.tab_widget.addTab(dock.annotations_tab, "Annotations")

    # Set dock widget content
    dock.setWidget(dock.annos_content)
