"""标定对话框页面构建：任务列表页、参数设置页与图像检测页。"""

from PyQt5 import QtWidgets, QtCore


def build_ui(dialog):
    # 主布局
    main_layout = QtWidgets.QVBoxLayout(dialog)

    # 创建标签页
    dialog.tab_widget = QtWidgets.QTabWidget()

    # 添加各个功能页
    dialog.add_calibration_settings_page()
    dialog.add_task_list_page()  # 新增的任务列表页面
    dialog.add_image_detection_page()

    # 添加标签页到主界面
    main_layout.addWidget(dialog.tab_widget)

    # 状态栏
    dialog.status_bar = QtWidgets.QStatusBar()
    main_layout.addWidget(dialog.status_bar)

    # 设置主窗口大小
    dialog.resize(1200, 800)


def build_task_list_page(dialog):
    """添加任务列表页面"""
    page = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout()

    # 任务列表
    dialog.task_list = QtWidgets.QListWidget()
    dialog.task_list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
    layout.addWidget(QtWidgets.QLabel("任务列表:"))
    layout.addWidget(dialog.task_list)

    # 任务操作按钮
    button_layout = QtWidgets.QHBoxLayout()

    dialog.add_task_button = QtWidgets.QPushButton("添加任务")
    dialog.add_task_button.clicked.connect(dialog.show_add_task_dialog)

    dialog.remove_task_button = QtWidgets.QPushButton("移除任务")
    dialog.remove_task_button.clicked.connect(dialog.remove_selected_task)

    dialog.clear_task_button = QtWidgets.QPushButton("清空任务")
    dialog.clear_task_button.clicked.connect(dialog.clear_all_tasks)

    dialog.start_tasks_button = QtWidgets.QPushButton("开始处理任务")
    dialog.start_tasks_button.clicked.connect(dialog.start_processing_tasks)

    button_layout.addWidget(dialog.add_task_button)
    button_layout.addWidget(dialog.remove_task_button)
    button_layout.addWidget(dialog.clear_task_button)
    button_layout.addWidget(dialog.start_tasks_button)

    layout.addLayout(button_layout)

    # 任务详细信息显示
    details_group = QtWidgets.QGroupBox("任务详情")
    details_layout = QtWidgets.QFormLayout()

    dialog.task_name_label = QtWidgets.QLabel("未选择任务")
    dialog.task_status_label = QtWidgets.QLabel("状态: 待处理")
    dialog.task_params_label = QtWidgets.QLabel("参数: 无")

    details_layout.addRow("当前任务:", dialog.task_name_label)
    details_layout.addRow("", dialog.task_status_label)
    details_layout.addRow("", dialog.task_params_label)

    details_group.setLayout(details_layout)
    layout.addWidget(details_group)

    # 进度条
    dialog.tasks_progress_bar = QtWidgets.QProgressBar()
    layout.addWidget(dialog.tasks_progress_bar)

    layout.addStretch()
    page.setLayout(layout)
    dialog.tab_widget.addTab(page, "任务列表")


def build_settings_page(dialog):
    """添加标定参数设置页面"""
    page = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout()

    # 参数输入区域
    form_group = QtWidgets.QGroupBox("Calibration Parameters")
    form_layout = QtWidgets.QFormLayout()

    # 棋盘格尺寸输入
    dialog.square_size_input = QtWidgets.QLineEdit(str(dialog.square_size))
    form_layout.addRow("Square Size (mm):", dialog.square_size_input)

    # 模式尺寸输入
    dialog.pattern_size_input = QtWidgets.QLineEdit(str(dialog.inner_corners[1]) + ','+ str(dialog.inner_corners[1]))
    form_layout.addRow("Pattern Size (width,height):", dialog.pattern_size_input)

    # 检测类型选择
    dialog.pattern_type_combo = QtWidgets.QComboBox()
    dialog.pattern_type_combo.addItems(["chessboard", "circles", "asymmetric_circles"])
    dialog.pattern_type_combo.setCurrentText(dialog.pattern_type)
    form_layout.addRow("Pattern Type:", dialog.pattern_type_combo)

    # 图像目录选择
    image_dir_layout = QtWidgets.QHBoxLayout()
    dialog.image_dir_input = QtWidgets.QLineEdit(str(dialog.image_dir))
    dialog.browse_button = QtWidgets.QPushButton("Browse...")
    dialog.browse_button.clicked.connect(dialog.select_image_directory)
    image_dir_layout.addWidget(dialog.image_dir_input)
    image_dir_layout.addWidget(dialog.browse_button)
    form_layout.addRow("Image Directory:", image_dir_layout)

    # 加载标定参数
    load_calib_layout = QtWidgets.QHBoxLayout()
    dialog.load_calib_input = QtWidgets.QLineEdit()
    dialog.load_calib_button = QtWidgets.QPushButton("加载标定参数")
    dialog.load_calib_button.clicked.connect(dialog.load_calibration_parameters)
    load_calib_layout.addWidget(dialog.load_calib_input)
    load_calib_layout.addWidget(dialog.load_calib_button)
    form_layout.addRow("Load calibration:", load_calib_layout)

    form_group.setLayout(form_layout)
    layout.addWidget(form_group)

    # 高级选项区域
    advanced_group = QtWidgets.QGroupBox("Advanced Options")
    advanced_layout = QtWidgets.QGridLayout()

    # 复选框选项
    dialog.shuffle_checkbox = QtWidgets.QCheckBox("Shuffle Images")
    dialog.filter_files_checkbox = QtWidgets.QCheckBox("Filter Bad Files")
    dialog.gen_detector_checkbox = QtWidgets.QCheckBox("Generate Detector")

    advanced_layout.addWidget(dialog.shuffle_checkbox, 0, 0)
    advanced_layout.addWidget(dialog.filter_files_checkbox, 0, 1)
    advanced_layout.addWidget(dialog.gen_detector_checkbox, 1, 0)

    # 最大图像数量
    dialog.detect_num_spinbox = QtWidgets.QSpinBox()
    dialog.detect_num_spinbox.setRange(1, 10000)
    dialog.detect_num_spinbox.setValue(1000)
    advanced_layout.addWidget(QtWidgets.QLabel("Max Image Pairs:"), 1, 1)
    advanced_layout.addWidget(dialog.detect_num_spinbox, 1, 2)

    advanced_group.setLayout(advanced_layout)
    layout.addWidget(advanced_group)

    # 操作按钮
    button_layout = QtWidgets.QHBoxLayout()
    dialog.start_calib_button = QtWidgets.QPushButton("Start Calibration")
    dialog.start_calib_button.clicked.connect(dialog.start_calibration)
    dialog.save_calib_button = QtWidgets.QPushButton("Save Calibration")
    dialog.save_calib_button.clicked.connect(dialog.save_calibration)
    # 添加“从当前设置创建任务”按钮
    dialog.create_task_button = QtWidgets.QPushButton("从当前设置创建任务")
    dialog.create_task_button.clicked.connect(dialog.show_add_task_dialog)

    button_layout.addWidget(dialog.start_calib_button)
    button_layout.addWidget(dialog.save_calib_button)
    button_layout.addStretch()

    button_layout.addWidget(dialog.create_task_button)
    layout.addLayout(button_layout)

    # 日志输出
    # 日志输出区域 - 替换为 Tab 形式
    dialog.log_tab_widget = QtWidgets.QTabWidget()

    # 创建原始日志输出区域
    log_widget = QtWidgets.QWidget()
    log_layout = QtWidgets.QVBoxLayout(log_widget)
    dialog.log_output = QtWidgets.QTextEdit()
    dialog.log_output.setReadOnly(True)
    log_layout.addWidget(QtWidgets.QLabel("Log Output:"))
    log_layout.addWidget(dialog.log_output)
    dialog.log_tab_widget.addTab(log_widget, "Log Output")

    dialog.result_text_edit = QtWidgets.QTextEdit()
    dialog.result_text_edit.setReadOnly(True)
    dialog.log_tab_widget.addTab(dialog.result_text_edit, "Calibration Results")

    dialog.error_text_edit = QtWidgets.QTextEdit()
    dialog.error_text_edit.setReadOnly(True)
    dialog.log_tab_widget.addTab(dialog.error_text_edit, "Error Analysis")

    # 插入到布局中
    layout.addWidget(dialog.log_tab_widget)

    layout.addStretch()
    page.setLayout(layout)
    dialog.tab_widget.addTab(page, "Settings")


def build_image_detection_page(dialog):
    """添加图像检测页面（单目预览）"""
    page = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout()

    # 图像显示区域
    image_group = QtWidgets.QGroupBox("Image Preview")
    image_layout = QtWidgets.QHBoxLayout()

    dialog.image_label = QtWidgets.QLabel("Camera Preview")
    dialog.image_label.setAlignment(QtCore.Qt.AlignCenter)

    image_layout.addWidget(dialog.image_label, 1)
    image_group.setLayout(image_layout)
    layout.addWidget(image_group)

    # 进度条
    dialog.progress_bar = QtWidgets.QProgressBar()
    layout.addWidget(dialog.progress_bar)

    layout.addStretch()
    page.setLayout(layout)
    dialog.tab_widget.addTab(page, "Image Detection")
