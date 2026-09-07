"""新建标定任务对话框。"""

from datetime import datetime

from PyQt5 import QtWidgets


class AddTaskDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加新任务")
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # 任务类型选择
        type_layout = QtWidgets.QHBoxLayout()
        self.task_type_combo = QtWidgets.QComboBox()
        self.task_type_combo.addItems([
            "calibrate",  # 标定任务
            "save_result"  # 保存结果任务
        ])
        type_layout.addWidget(QtWidgets.QLabel("任务类型:"))
        type_layout.addWidget(self.task_type_combo)
        layout.addLayout(type_layout)

        # 任务名称输入
        self.task_name_edit = QtWidgets.QLineEdit()
        self.task_name_edit.setText(f"任务_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        layout.addWidget(QtWidgets.QLabel("任务名称:"))
        layout.addWidget(self.task_name_edit)

        # 参数面板容器
        self.param_container = QtWidgets.QWidget()
        self.param_layout = QtWidgets.QStackedLayout(self.param_container)

        # 标定任务参数面板
        calibrate_panel = QtWidgets.QWidget()
        calibrate_layout = QtWidgets.QFormLayout()

        self.calibrate_square_size = QtWidgets.QLineEdit("40")
        self.calibrate_pattern_size = QtWidgets.QLineEdit("7,7")
        self.calibrate_image_dir = QtWidgets.QLineEdit()
        self.calibrate_browse_button = QtWidgets.QPushButton("...")
        self.calibrate_browse_button.clicked.connect(self.select_image_directory)

        image_dir_layout = QtWidgets.QHBoxLayout()
        image_dir_layout.addWidget(self.calibrate_image_dir)
        image_dir_layout.addWidget(self.calibrate_browse_button)

        self.calibrate_pattern_type = QtWidgets.QComboBox()
        self.calibrate_pattern_type.addItems(["chessboard", "circles", "asymmetric_circles"])

        self.calibrate_shuffle = QtWidgets.QCheckBox()
        self.calibrate_filter_files = QtWidgets.QCheckBox()
        self.calibrate_gen_detector = QtWidgets.QCheckBox()
        self.calibrate_detect_num = QtWidgets.QSpinBox()
        self.calibrate_detect_num.setRange(1, 10000)
        self.calibrate_detect_num.setValue(1000)

        calibrate_layout.addRow("棋盘格尺寸 (mm):", self.calibrate_square_size)
        calibrate_layout.addRow("模式尺寸 (宽,高):", self.calibrate_pattern_size)

        tmp_layout = QtWidgets.QHBoxLayout()
        tmp_layout.addLayout(image_dir_layout)
        calibrate_layout.addRow("图像目录:", tmp_layout)

        calibrate_layout.addRow("模式类型:", self.calibrate_pattern_type)
        calibrate_layout.addRow("随机排序:", self.calibrate_shuffle)
        calibrate_layout.addRow("过滤无效文件:", self.calibrate_filter_files)
        calibrate_layout.addRow("生成检测器:", self.calibrate_gen_detector)
        calibrate_layout.addRow("最大图像数量:", self.calibrate_detect_num)

        calibrate_panel.setLayout(calibrate_layout)

        # 保存结果任务参数面板
        save_result_panel = QtWidgets.QWidget()
        save_result_layout = QtWidgets.QFormLayout()

        self.save_file_path = QtWidgets.QLineEdit()
        self.save_browse_button = QtWidgets.QPushButton("...")
        self.save_browse_button.clicked.connect(self.select_save_location)

        file_path_layout = QtWidgets.QHBoxLayout()
        file_path_layout.addWidget(self.save_file_path)
        file_path_layout.addWidget(self.save_browse_button)

        tmp_layout = QtWidgets.QHBoxLayout()
        tmp_layout.addLayout(file_path_layout)
        save_result_layout.addRow("保存路径:", tmp_layout)

        save_result_layout.addRow(QtWidgets.QLabel("需要前置标定任务"))

        save_result_panel.setLayout(save_result_layout)

        # 将面板添加到堆栈布局中
        self.param_layout.addWidget(calibrate_panel)
        self.param_layout.addWidget(save_result_panel)

        # 切换面板
        self.task_type_combo.currentIndexChanged.connect(self.switch_param_panel)

        layout.addWidget(self.param_container)

        # 按钮
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def switch_param_panel(self, index):
        """切换参数面板"""
        self.param_layout.setCurrentIndex(index)

    def select_image_directory(self):
        """选择图像目录"""
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Image Directory")
        if directory:
            self.calibrate_image_dir.setText(directory)

    def select_save_location(self):
        """选择保存位置"""
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存标定结果", "", "JSON文件 (*.json)")
        if file_path:
            self.save_file_path.setText(file_path)

    def get_task_info(self):
        """获取任务信息"""
        task_type = self.task_type_combo.currentText()
        task_name = self.task_name_edit.text()

        base_info = {
            "name": task_name,
            "type": task_type
        }

        if task_type == "calibrate":
            base_info.update({
                "square_size": float(self.calibrate_square_size.text()),
                "pattern_size": tuple(map(int, self.calibrate_pattern_size.text().split(','))),
                "image_dir": self.calibrate_image_dir.text(),
                "detect_shape": self.calibrate_pattern_type.currentText(),
                "detect_num": self.calibrate_detect_num.value(),
                "shuffle": self.calibrate_shuffle.isChecked(),
                "filter_files": self.calibrate_filter_files.isChecked(),
                "gen_detector": self.calibrate_gen_detector.isChecked()
            })
        elif task_type == "save_result":
            base_info.update({
                "file_path": self.save_file_path.text()
            })

        return base_info
