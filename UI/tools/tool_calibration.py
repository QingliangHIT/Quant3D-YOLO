# dialog_calibration.py
import os
import time
from datetime import datetime

import cv2
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from matplotlib import pyplot as plt

from calibrate.calib import CameraCalibrator
import cv2


class CalibrationDetector:
    def __init__(self, inner_corners=(7, 7), pattern_type='circles'):
        """
        初始化标定检测器
        :param inner_corners: 棋盘格内部角点数量 (width, height)
        :param pattern_type: 检测类型 ('chessboard', 'circles', 'asymmetric_circles')
        """
        self.inner_corners = inner_corners
        self.pattern_type = pattern_type
        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    def detect(self, image):
        """
        根据 pattern_type 自动选择检测方法
        :param image: 输入图像
        :return: 是否检测成功，以及绘制了角点的图像
        """
        if self.pattern_type == 'chessboard':
            return self.detect_chessboard(image)
        elif self.pattern_type == 'circles':
            return self.detect_circles_grid(image, flags=cv2.CALIB_CB_SYMMETRIC_GRID)
        elif self.pattern_type == 'asymmetric_circles':
            return self.detect_circles_grid(image, flags=cv2.CALIB_CB_ASYMMETRIC_GRID)
        else:
            raise ValueError(f"Unsupported pattern type: {self.pattern_type}")

    def detect_chessboard(self, image):
        """检测棋盘格"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, self.inner_corners, None)
        if ret:
            # 角点精检测
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), self.criteria)
            cv2.drawChessboardCorners(image, self.inner_corners, corners, ret)
        return ret, image

    def detect_circles_grid(self, image, flags=0):
        """检测圆形网格（对称或非对称）"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findCirclesGrid(gray, self.inner_corners, flags=flags)
        if ret:
            cv2.drawChessboardCorners(image, self.inner_corners, corners, ret)
        return ret, image


class CalibrationSettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibration Settings")

        layout = QtWidgets.QFormLayout(self)

        # 内角数量输入
        self.inner_corners_width = QtWidgets.QSpinBox()
        self.inner_corners_width.setRange(1, 20)
        self.inner_corners_width.setValue(7)  # 默认值
        self.inner_corners_height = QtWidgets.QSpinBox()
        self.inner_corners_height.setRange(1, 20)
        self.inner_corners_height.setValue(7)  # 默认值
        # self.square_size = QtWidgets.QTextEdit()
        # self.square_size.setValue(40)  # 默认值
        layout.addRow("Inner Corners (Width)", self.inner_corners_width)
        layout.addRow("Inner Corners (Height)", self.inner_corners_height)
        # layout.addRow("Square size", self.square_size)

        # 检测类型选择
        self.pattern_type_combo = QtWidgets.QComboBox()
        self.pattern_type_combo.addItems([
            'circles',  # 圆形网格
            'chessboard',  # 棋盘格
            'asymmetric_circles'  # 非对称圆形网格
        ])
        layout.addRow("Detection Type", self.pattern_type_combo)

        # 图像路径选择
        # self.image_path_input = QtWidgets.QLineEdit()
        # self.browse_button = QtWidgets.QPushButton("Browse...")
        # self.browse_button.clicked.connect(self.select_image_directory)
        # path_layout = QtWidgets.QHBoxLayout()
        # path_layout.addWidget(self.image_path_input)
        # path_layout.addWidget(self.browse_button)
        # layout.addRow("Image Directory", path_layout)

        # 确认/取消按钮
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def select_image_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Image Directory")
        if directory:
            self.image_path_input.setText(directory)

    def get_settings(self):
        return {
            'inner_corners': (self.inner_corners_width.value(), self.inner_corners_height.value()),
            'image_dir': self.image_path_input.text(),
            'pattern_type': self.pattern_type_combo.currentText(),  # 返回选中的检测类型
            # 'square_size': self.square_size.currentText()  # 返回选中的检测类型
        }


class CalibratorWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(int)
    result_ready = QtCore.pyqtSignal(object)
    error_occurred = QtCore.pyqtSignal(str)

    def __init__(self, calibrator, parent=None):
        super().__init__(parent)
        self.calibrator = calibrator

    def run(self, mode='Stereo'):
        try:
            # 执行耗时操作
            if mode == 'Stereo':
                ret = self.calibrator.calibrate()
            elif mode == 'Mono':
                ret = self.calibrator.calibrate_single_camera('_l')
            else:
                ret = self.calibrator.calibrate_single_camera('_r')
            self.report_progress(100)
            self.result_ready.emit(ret)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()

    def report_progress(self, value):
        self.progress.emit(value)

    def return_result(self, result):
        self.result_ready.emit(result)


class CalibrationDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, detector=None, square_size=40, image_dir=None):
        super().__init__(parent)
        self.load_calib = None
        self.setWindowTitle("Camera Calibrator")
        self.detector = detector
        if self.detector is None:
            self.detector = CalibrationDetector()
        self.inner_corners = self.detector.inner_corners
        self.pattern_type = self.detector.pattern_type
        self.square_size = square_size
        self.image_dir = image_dir

        # 任务队列相关
        self.task_queue = []
        self.current_task_index = -1
        self.calibration_thread = None
        self.calibrator_worker = None
        self.mono_stereo_combo = None
        self.left_name_input = None
        self.right_name_input = None
        self.load_calib_button = None
        self.eval_error_button = None
        self.init_ui()

    def init_ui(self):
        # 主布局
        main_layout = QtWidgets.QVBoxLayout(self)

        # 创建标签页
        self.tab_widget = QtWidgets.QTabWidget()

        # 添加各个功能页
        self.add_calibration_settings_page()
        self.add_task_list_page()  # 新增的任务列表页面
        self.add_image_detection_page()
        # self.add_calibration_results_page()
        # self.add_error_analysis_page()

        # 添加标签页到主界面
        main_layout.addWidget(self.tab_widget)

        # 状态栏
        self.status_bar = QtWidgets.QStatusBar()
        main_layout.addWidget(self.status_bar)

        # 设置主窗口大小
        self.resize(1200, 800)

    def add_task_list_page(self):
        """添加任务列表页面"""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        # 任务列表
        self.task_list = QtWidgets.QListWidget()
        self.task_list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        layout.addWidget(QtWidgets.QLabel("任务列表:"))
        layout.addWidget(self.task_list)

        # 任务操作按钮
        button_layout = QtWidgets.QHBoxLayout()

        self.add_task_button = QtWidgets.QPushButton("添加任务")
        self.add_task_button.clicked.connect(self.show_add_task_dialog)

        self.remove_task_button = QtWidgets.QPushButton("移除任务")
        self.remove_task_button.clicked.connect(self.remove_selected_task)

        self.clear_task_button = QtWidgets.QPushButton("清空任务")
        self.clear_task_button.clicked.connect(self.clear_all_tasks)

        self.start_tasks_button = QtWidgets.QPushButton("开始处理任务")
        self.start_tasks_button.clicked.connect(self.start_processing_tasks)

        button_layout.addWidget(self.add_task_button)
        button_layout.addWidget(self.remove_task_button)
        button_layout.addWidget(self.clear_task_button)
        button_layout.addWidget(self.start_tasks_button)

        layout.addLayout(button_layout)

        # 任务详细信息显示
        details_group = QtWidgets.QGroupBox("任务详情")
        details_layout = QtWidgets.QFormLayout()

        self.task_name_label = QtWidgets.QLabel("未选择任务")
        self.task_status_label = QtWidgets.QLabel("状态: 待处理")
        self.task_params_label = QtWidgets.QLabel("参数: 无")

        details_layout.addRow("当前任务:", self.task_name_label)
        details_layout.addRow("", self.task_status_label)
        details_layout.addRow("", self.task_params_label)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # 进度条
        self.tasks_progress_bar = QtWidgets.QProgressBar()
        layout.addWidget(self.tasks_progress_bar)

        layout.addStretch()
        page.setLayout(layout)
        self.tab_widget.addTab(page, "任务列表")

    def show_add_task_dialog(self):
        """显示添加任务对话框"""
        dialog = AddTaskDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            task_info = dialog.get_task_info()
            self.add_task_to_list(task_info)

    def add_task_to_list(self, task_info):
        """将任务添加到任务列表中"""
        task_item = QtWidgets.QListWidgetItem(f"{task_info['name']} ({task_info['type']})")
        task_item.setData(QtCore.Qt.UserRole, task_info)
        self.task_list.addItem(task_item)
        self.task_queue.append(task_info)

        # 更新状态栏
        self.status_bar.showMessage(f"已添加任务: {task_info['name']}")

    def remove_selected_task(self):
        """移除选中的任务"""
        current_row = self.task_list.currentRow()
        if current_row >= 0:
            removed_task = self.task_list.item(current_row).data(QtCore.Qt.UserRole)
            self.task_list.takeItem(current_row)
            del self.task_queue[current_row]

            # 更新状态栏
            self.status_bar.showMessage(f"已移除任务: {removed_task['name']}")

    def clear_all_tasks(self):
        """清空所有任务"""
        self.task_list.clear()
        self.task_queue.clear()

        # 更新状态栏
        self.status_bar.showMessage("任务列表已清空")

    def start_processing_tasks(self):
        """开始处理任务队列"""
        if not self.task_queue:
            QtWidgets.QMessageBox.information(self, "提示", "任务列表为空，请先添加任务。")
            return

        # 初始化进度条
        self.tasks_progress_bar.setMaximum(len(self.task_queue))
        self.tasks_progress_bar.setValue(0)

        # 开始处理第一个任务
        self.current_task_index = 0
        self.process_next_task()

    def process_next_task(self):
        """处理下一个任务"""
        if self.current_task_index >= len(self.task_queue):
            # 所有任务已完成
            self.current_task_index = -1
            self.update_task_details()
            self.status_bar.showMessage("所有任务已完成！")
            self.tasks_progress_bar.setValue(self.tasks_progress_bar.maximum())
            return

        # 获取当前任务
        current_task = self.task_queue[self.current_task_index]
        self.update_task_details(current_task)

        # 根据任务类型执行不同操作
        if current_task["type"] == "calibrate":
            self.start_calibration_task(current_task)
        elif current_task["type"] == "analyze_error":
            self.evaluate_error_task(current_task)
        elif current_task["type"] == "save_result":
            self.save_calibration_task(current_task)

    def update_task_details(self, task_info=None):
        """更新任务详情显示"""
        if task_info is None:
            self.task_name_label.setText("未选择任务")
            self.task_status_label.setText("状态: 待处理")
            self.task_params_label.setText("参数: 无")
        else:
            self.task_name_label.setText(task_info["name"])
            self.task_status_label.setText(f"状态: 正在处理 ({self.current_task_index + 1}/{len(self.task_queue)})")
            params_text = ", ".join([f"{k}: {v}" for k, v in task_info.items() if k not in ["name", "type"]])
            self.task_params_label.setText(f"参数: {params_text}")

    def start_calibration_task(self, task_info):
        """开始执行标定任务"""
        try:
            # 获取用户设置
            square_size = task_info.get("square_size", float(self.square_size_input.text()))
            pattern_size = task_info.get("pattern_size", tuple(map(int, self.pattern_size_input.text().split(','))))
            image_dir = task_info.get("image_dir", self.image_dir_input.text())
            detect_shape = task_info.get("detect_shape", self.pattern_type_combo.currentText())
            detect_num = task_info.get("detect_num", self.detect_num_spinbox.value())
            shuffle = task_info.get("shuffle", self.shuffle_checkbox.isChecked())
            filter_files = task_info.get("filter_files", self.filter_files_checkbox.isChecked())
            gen_detector = task_info.get("gen_detector", self.gen_detector_checkbox.isChecked())

            # 初始化标定器
            self.calibrator_worker = CameraCalibrator(
                pattern_size=pattern_size,
                square_size=square_size,
                image_dir=image_dir,
                detect_shape=detect_shape,
                detect_num=detect_num,
                shuffle=shuffle,
                filter_files=filter_files,
                gen_detector=gen_detector
            )

            self.log_message("标定器初始化成功")

            # 创建并启动线程
            self.calibration_thread = QtCore.QThread()
            self.calibrator_worker.moveToThread(self.calibration_thread)

            # 连接信号和槽
            self.calibration_thread.started.connect(self.calibrator_worker.calibrate)
            self.calibrator_worker.finished.connect(self.on_task_finished)
            self.calibrator_worker.finished.connect(self.calibrator_worker.deleteLater)
            self.calibration_thread.finished.connect(self.calibration_thread.deleteLater)
            self.calibrator_worker.progress.connect(self.update_progress)
            self.calibrator_worker.result_ready.connect(self.display_results)

            # 启动线程
            self.calibration_thread.start()

        except Exception as e:
            error_msg = f"初始化标定任务失败: {str(e)}"
            self.log_message(error_msg, error=True)
            self.status_bar.showMessage(error_msg)
            self.on_task_finished(False)

    def evaluate_error_task(self, task_info):
        """开始执行误差分析任务"""
        try:
            if not hasattr(self, 'calibrator') or self.calibrator is None:
                raise ValueError("请先进行标定！")

            # 获取任务参数
            num_points = task_info.get("num_points", 5)

            # 在单独的线程中执行
            self.calibration_thread = QtCore.QThread()
            self.calibrator.moveToThread(self.calibration_thread)

            def run_error_evaluation():
                try:
                    align_error, max_error, mean_error = self.calibrator.evaluate_error(num=num_points)

                    # 将结果保存到calibrator对象上
                    self.calibrator.align_error = align_error
                    self.calibrator.max_error = max_error
                    self.calibrator.mean_error = mean_error

                    self.calibrator.result_ready.emit({
                        "align_error": align_error,
                        "max_error": max_error,
                        "mean_error": mean_error
                    })
                except Exception as e:
                    self.calibrator.error_occurred.emit(str(e))

            # 连接信号和槽
            self.calibration_thread.started.connect(run_error_evaluation)
            self.calibrator.result_ready.connect(self.on_error_evaluation_finished)
            self.calibrator.error_occurred.connect(lambda e: self.on_task_finished(False, e))
            self.calibration_thread.finished.connect(self.calibration_thread.deleteLater)

            # 启动线程
            self.calibration_thread.start()

        except Exception as e:
            error_msg = f"初始化误差分析任务失败: {str(e)}"
            self.log_message(error_msg, error=True)
            self.status_bar.showMessage(error_msg)
            self.on_task_finished(False, error_msg)

    def on_error_evaluation_finished(self, result):
        """误差分析任务完成后的处理"""
        # 更新显示
        self.reprojection_error_label.setText(f"Reprojection Error: {self.calibrator.ret:.4f} pixels")
        self.alignment_error_label.setText(f"Alignment Error: {result.get('align_error', 0):.2f} pixels")
        self.max_error_label.setText(f"Max Error: {result.get('max_error', 0):.2f} mm")
        self.mean_error_label.setText(f"Mean Error: {result.get('mean_error', 0):.2f} mm")

        self.on_task_finished(True)

    def save_calibration_task(self, task_info):
        """开始执行保存标定结果任务"""
        try:
            if not hasattr(self, 'calibrator') or self.calibrator is None:
                raise ValueError("请先进行标定！")

            # 获取文件路径
            file_path = task_info.get("file_path")
            if not file_path:
                file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存标定结果", "", "JSON文件 (*.json)")
                if not file_path:
                    self.on_task_finished(False, "未选择保存路径")
                    return

            # 在单独的线程中执行
            self.calibration_thread = QtCore.QThread()

            def run_save_calibration():
                try:
                    self.calibrator.save_json(file_path)
                    return file_path
                except Exception as e:
                    raise e

            # 使用QtConcurrent运行耗时操作
            future = QtCore.QtConcurrent.run(run_save_calibration)
            watcher = QtCore.QFutureWatcher()
            watcher.setFuture(future)

            def handle_save_result():
                saved_path = future.result()
                self.log_message(f"标定结果已保存至: {saved_path}")
                self.on_task_finished(True)

            def handle_save_error():
                if future.isCanceled() or future.isFinished():
                    error = future.errorString()
                    self.on_task_finished(False, f"保存失败: {error}")

            watcher.finished.connect(handle_save_result)
            watcher.finished.connect(watcher.deleteLater)

        except Exception as e:
            error_msg = f"初始化保存任务失败: {str(e)}"
            self.log_message(error_msg, error=True)
            self.status_bar.showMessage(error_msg)
            self.on_task_finished(False, error_msg)

    def on_task_finished(self, success, error=None):
        """任务完成后的处理"""
        # 更新进度条
        self.tasks_progress_bar.setValue(self.current_task_index + 1)

        if success:
            self.status_bar.showMessage(f"任务 {self.current_task_index + 1} 已完成")
            self.log_message(f"任务 {self.current_task_index + 1} 成功完成")
        else:
            self.status_bar.showMessage(f"任务 {self.current_task_index + 1} 失败: {error}")
            self.log_message(f"任务 {self.current_task_index + 1} 失败: {error}", error=True)

        # 停止当前线程
        if self.calibration_thread and self.calibration_thread.isRunning():
            self.calibration_thread.quit()
            self.calibration_thread.wait()

        # 移动到下一个任务
        self.current_task_index += 1
        QtCore.QTimer.singleShot(100, self.process_next_task)  # 使用定时器确保线程正确释放

    def add_calibration_settings_page(self):
        """添加标定参数设置页面"""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        # 参数输入区域
        form_group = QtWidgets.QGroupBox("Calibration Parameters")
        form_layout = QtWidgets.QFormLayout()

        # 模式选择（单目/双目）
        self.mono_stereo_combo = QtWidgets.QComboBox()
        self.mono_stereo_combo.addItems(["Stereo", "Mono", "MonoR"])
        self.mono_stereo_combo.currentIndexChanged.connect(self.on_mono_stereo_changed)
        form_layout.addRow("模式:", self.mono_stereo_combo)

        # 左右相机文件名前缀输入
        left_right_layout = QtWidgets.QHBoxLayout()
        self.left_name_input = QtWidgets.QLineEdit("_l")
        self.right_name_input = QtWidgets.QLineEdit("_r")
        left_right_layout.addWidget(QtWidgets.QLabel("左相机前缀:"))
        left_right_layout.addWidget(self.left_name_input)
        left_right_layout.addWidget(QtWidgets.QLabel("右相机前缀:"))
        left_right_layout.addWidget(self.right_name_input)
        form_layout.addRow("左右图像前缀:", left_right_layout)

        # 棋盘格尺寸输入
        self.square_size_input = QtWidgets.QLineEdit(str(self.square_size))
        form_layout.addRow("Square Size (mm):", self.square_size_input)

        # 模式尺寸输入
        self.pattern_size_input = QtWidgets.QLineEdit(str(self.inner_corners[1]) + ','+ str(self.inner_corners[1]))
        form_layout.addRow("Pattern Size (width,height):", self.pattern_size_input)

        # 检测类型选择
        self.pattern_type_combo = QtWidgets.QComboBox()
        self.pattern_type_combo.addItems(["chessboard", "circles", "asymmetric_circles"])
        self.pattern_type_combo.setCurrentText(self.pattern_type)
        form_layout.addRow("Pattern Type:", self.pattern_type_combo)

        # 图像目录选择
        image_dir_layout = QtWidgets.QHBoxLayout()
        self.image_dir_input = QtWidgets.QLineEdit(str(self.image_dir))
        self.browse_button = QtWidgets.QPushButton("Browse...")
        self.browse_button.clicked.connect(self.select_image_directory)
        image_dir_layout.addWidget(self.image_dir_input)
        image_dir_layout.addWidget(self.browse_button)
        form_layout.addRow("Image Directory:", image_dir_layout)

        # 图像目录选择
        load_calib_layout = QtWidgets.QHBoxLayout()
        self.load_calib_input = QtWidgets.QLineEdit()
        self.load_calib_button = QtWidgets.QPushButton("Load stereo...")
        self.load_calib_button.clicked.connect(self.load_calibration_parameters)
        self.load_left_input = QtWidgets.QLineEdit()
        self.load_left_button = QtWidgets.QPushButton("Load left...")
        self.load_left_button.clicked.connect(self.load_calibration_parameters_l)
        self.load_right_input = QtWidgets.QLineEdit()
        self.load_right_button = QtWidgets.QPushButton("Load right...")
        self.load_right_button.clicked.connect(self.load_calibration_parameters_r)
        load_calib_layout.addWidget(self.load_calib_input)
        load_calib_layout.addWidget(self.load_calib_button)
        load_calib_layout.addWidget(self.load_left_input)
        load_calib_layout.addWidget(self.load_left_button)
        load_calib_layout.addWidget(self.load_right_input)
        load_calib_layout.addWidget(self.load_right_button)
        form_layout.addRow("Load calibration:", load_calib_layout)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # 高级选项区域
        advanced_group = QtWidgets.QGroupBox("Advanced Options")
        advanced_layout = QtWidgets.QGridLayout()

        # 复选框选项
        self.shuffle_checkbox = QtWidgets.QCheckBox("Shuffle Images")
        self.filter_files_checkbox = QtWidgets.QCheckBox("Filter Bad Files")
        self.gen_detector_checkbox = QtWidgets.QCheckBox("Generate Detector")

        advanced_layout.addWidget(self.shuffle_checkbox, 0, 0)
        advanced_layout.addWidget(self.filter_files_checkbox, 0, 1)
        advanced_layout.addWidget(self.gen_detector_checkbox, 1, 0)

        # 最大图像数量
        self.detect_num_spinbox = QtWidgets.QSpinBox()
        self.detect_num_spinbox.setRange(1, 10000)
        self.detect_num_spinbox.setValue(1000)
        advanced_layout.addWidget(QtWidgets.QLabel("Max Image Pairs:"), 1, 1)
        advanced_layout.addWidget(self.detect_num_spinbox, 1, 2)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        # 操作按钮
        button_layout = QtWidgets.QHBoxLayout()
        self.start_calib_button = QtWidgets.QPushButton("Start Calibration")
        self.start_calib_button.clicked.connect(self.start_calibration)
        self.save_calib_button = QtWidgets.QPushButton("Save Calibration")
        self.save_calib_button.clicked.connect(self.save_calibration)
        # 添加“从当前设置创建任务”按钮
        self.create_task_button = QtWidgets.QPushButton("从当前设置创建任务")
        self.create_task_button.clicked.connect(self.show_add_task_dialog)

        button_layout.addWidget(self.start_calib_button)
        button_layout.addWidget(self.save_calib_button)
        button_layout.addStretch()

        self.eval_error_button = QtWidgets.QPushButton("评估误差")
        self.eval_error_button.clicked.connect(self.evaluate_error)

        # self.load_calib_button = QtWidgets.QPushButton("加载预标定参数")
        # self.load_calib_button.clicked.connect(self.load_calibration_parameters)

        button_layout.addWidget(self.eval_error_button)
        button_layout.addWidget(self.create_task_button)
        layout.addLayout(button_layout)

        # 日志输出
        # 日志输出区域 - 替换为 Tab 形式
        self.log_tab_widget = QtWidgets.QTabWidget()

        # 创建原始日志输出区域
        log_widget = QtWidgets.QWidget()
        log_layout = QtWidgets.QVBoxLayout(log_widget)
        self.log_output = QtWidgets.QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(QtWidgets.QLabel("Log Output:"))
        log_layout.addWidget(self.log_output)
        self.log_tab_widget.addTab(log_widget, "Log Output")

        self.result_text_edit = QtWidgets.QTextEdit()
        self.result_text_edit.setReadOnly(True)
        self.log_tab_widget.addTab(self.result_text_edit, "Calibration Results")

        self.error_text_edit = QtWidgets.QTextEdit()
        self.error_text_edit.setReadOnly(True)
        self.log_tab_widget.addTab(self.error_text_edit, "Error Analysis")

        # 插入到布局中
        layout.addWidget(self.log_tab_widget)

        layout.addStretch()
        page.setLayout(layout)
        self.tab_widget.addTab(page, "Settings")

    def on_mono_stereo_changed(self, index):
        is_stereo = index == 0  # 0 表示 Stereo
        # self.right_name_input.setEnabled(is_stereo)
        # 其他双目专属控件也可以在这里启/禁用

    def load_calibration_parameters(self, event):
        # if self.calibrator is None:
        #     self.calibrator = CameraCalibrator()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择标定参数文件", "", "JSON 文件 (*.json)"
        )
        if file_path:
            self.load_calib_input.setText(file_path)

    def load_calibration_parameters_l(self, event):
        # if self.calibrator is None:
        #     self.calibrator = CameraCalibrator()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择标定参数文件", "", "JSON 文件 (*.json)"
        )
        if file_path:
            self.load_left_input.setText(file_path)

    def load_calibration_parameters_r(self, event):
        # if self.calibrator is None:
        #     self.calibrator = CameraCalibrator()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择标定参数文件", "", "JSON 文件 (*.json)"
        )
        if file_path:
            self.load_right_input.setText(file_path)

    def evaluate_error(self):
        """评估误差并显示在 QTextEdit 中"""
        if not hasattr(self, 'calibrator') or self.calibrator is None:
            try:
                calibrator = self.load_calibrator()
                if not calibrator:
                    return
                calibrator = self.load_args(calibrator)
                # self.display_results()
                self.log_message(f"标定参数已加载")
                # 开始标定过程（在单独的线程中运行）
                if calibrator.image_paths is None and calibrator.image_paths_test is None:
                    calibrator.image_paths, calibrator.image_paths_test, calibrator.imageSize = calibrator._load_image_pairs(
                        self.left_name_input.text(), self.right_name_input.text(), int(self.detect_num_spinbox.value()))
                    if calibrator.image_paths is None and calibrator.image_paths_test is None:
                        raise Exception("未找到任何图片")
                self.calibrator = CalibratorWorker(calibrator)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "错误", f"加载失败: {str(e)}")
                return None

        try:
            self.log_message(f"开始评估")
            align_error, max_error, mean_error = self.calibrator.calibrator.evaluate_error(num=20, train=True)

            error_str = ""
            error_str += f"Reprojection Error: {self.calibrator.calibrator.ret:.4f} pixels\n"
            error_str += f"Alignment Error: {align_error:.2f} pixels\n"
            error_str += f"Max Error: {max_error:.2f} mm\n"
            error_str += f"Mean Error: {mean_error:.2f} mm\n"

            # 更新 QTextEdit 内容
            if hasattr(self, 'error_text_edit'):
                self.error_text_edit.setText(error_str)

            self.log_message(f"误差评估完成 - 重投影误差: {self.calibrator.calibrator.ret:.4f} 像素")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"误差评估失败: {str(e)}")
            self.log_message(f"错误: {str(e)}", error=True)

    def add_image_detection_page(self):
        """添加图像检测页面"""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        # 图像显示区域
        image_group = QtWidgets.QGroupBox("Image Preview")
        image_layout = QtWidgets.QHBoxLayout()

        self.left_image_label = QtWidgets.QLabel("Left Camera")
        self.left_image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.right_image_label = QtWidgets.QLabel("Right Camera")
        self.right_image_label.setAlignment(QtCore.Qt.AlignCenter)

        image_layout.addWidget(self.left_image_label, 1)
        image_layout.addWidget(self.right_image_label, 1)
        image_group.setLayout(image_layout)
        layout.addWidget(image_group)

        # 控制按钮
        control_layout = QtWidgets.QHBoxLayout()
        self.load_images_button = QtWidgets.QPushButton("Load Images")
        self.load_images_button.clicked.connect(self.load_images)
        self.detect_corners_button = QtWidgets.QPushButton("Detect Corners")
        self.detect_corners_button.clicked.connect(self.detect_corners)

        control_layout.addWidget(self.load_images_button)
        control_layout.addWidget(self.detect_corners_button)
        control_layout.addStretch()

        layout.addLayout(control_layout)

        # 进度条
        self.progress_bar = QtWidgets.QProgressBar()
        layout.addWidget(self.progress_bar)

        layout.addStretch()
        page.setLayout(layout)
        self.tab_widget.addTab(page, "Image Detection")

    def add_calibration_results_page(self):
        """添加标定结果页面"""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        # 结果显示区域
        result_group = QtWidgets.QGroupBox("Calibration Results")
        result_layout = QtWidgets.QFormLayout()

        self.camera_matrix_left_text = QtWidgets.QTextEdit()
        self.camera_matrix_left_text.setReadOnly(True)
        self.camera_matrix_left_text.setFixedHeight(100)
        result_layout.addRow("Left Camera Matrix:", self.camera_matrix_left_text)

        self.dist_coeffs_left_text = QtWidgets.QLineEdit()
        self.dist_coeffs_left_text.setReadOnly(True)
        result_layout.addRow("Left Distortion Coefficients:", self.dist_coeffs_left_text)

        self.camera_matrix_right_text = QtWidgets.QTextEdit()
        self.camera_matrix_right_text.setReadOnly(True)
        self.camera_matrix_right_text.setFixedHeight(100)
        result_layout.addRow("Right Camera Matrix:", self.camera_matrix_right_text)

        self.dist_coeffs_right_text = QtWidgets.QLineEdit()
        self.dist_coeffs_right_text.setReadOnly(True)
        result_layout.addRow("Right Distortion Coefficients:", self.dist_coeffs_right_text)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # 基础矩阵结果显示
        matrix_group = QtWidgets.QGroupBox("Stereo Calibration Matrices")
        matrix_layout = QtWidgets.QFormLayout()

        self.rotation_text = QtWidgets.QTextEdit()
        self.rotation_text.setReadOnly(True)
        self.rotation_text.setFixedHeight(100)
        matrix_layout.addRow("Rotation Matrix:", self.rotation_text)

        self.translation_text = QtWidgets.QTextEdit()
        self.translation_text.setReadOnly(True)
        self.translation_text.setFixedHeight(100)
        matrix_layout.addRow("Translation Vector:", self.translation_text)

        matrix_group.setLayout(matrix_layout)
        layout.addWidget(matrix_group)

        layout.addStretch()
        page.setLayout(layout)
        self.tab_widget.addTab(page, "Results")

    def add_error_analysis_page(self):
        """添加误差分析页面"""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        # 误差显示区域
        error_group = QtWidgets.QGroupBox("Error Analysis")
        error_layout = QtWidgets.QVBoxLayout()

        # 重投影误差
        self.reprojection_error_label = QtWidgets.QLabel("Reprojection Error: N/A")
        error_layout.addWidget(self.reprojection_error_label)

        # 对齐误差
        self.alignment_error_label = QtWidgets.QLabel("Alignment Error: N/A")
        error_layout.addWidget(self.alignment_error_label)

        # 最大误差
        self.max_error_label = QtWidgets.QLabel("Max Error: N/A")
        error_layout.addWidget(self.max_error_label)

        # 平均误差
        self.mean_error_label = QtWidgets.QLabel("Mean Error: N/A")
        error_layout.addWidget(self.mean_error_label)

        error_group.setLayout(error_layout)
        layout.addWidget(error_group)

        # 可视化区域
        visualization_group = QtWidgets.QGroupBox("Visualization")
        visualization_layout = QtWidgets.QHBoxLayout()

        self.error_chart = QtWidgets.QLabel("Error Chart Display Area")
        self.error_chart.setAlignment(QtCore.Qt.AlignCenter)
        visualization_layout.addWidget(self.error_chart)

        visualization_group.setLayout(visualization_layout)
        layout.addWidget(visualization_group)

        # 操作按钮
        button_layout = QtWidgets.QHBoxLayout()
        self.evaluate_error_button = QtWidgets.QPushButton("Evaluate Error")
        self.evaluate_error_button.clicked.connect(self.evaluate_error)
        self.show_3d_button = QtWidgets.QPushButton("Show 3D View")
        self.show_3d_button.clicked.connect(self.show_3d_view)

        button_layout.addWidget(self.evaluate_error_button)
        button_layout.addWidget(self.show_3d_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)
        layout.addStretch()

        page.setLayout(layout)
        self.tab_widget.addTab(page, "Error Analysis")

    def select_image_directory(self):
        """选择图像目录"""
        # 使用 self.image_dir 作为默认打开路径
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Image Directory",
            self.image_dir if self.image_dir else "",# 设置默认路径
        )
        if directory:
            self.image_dir_input.setText(directory)

    def load_calibrator(self):
        try:
            # 获取用户设置
            square_size = float(self.square_size_input.text())
            pattern_size = tuple(map(int, self.pattern_size_input.text().split(',')))
            image_dir = self.image_dir_input.text()
            detect_shape = self.pattern_type_combo.currentText()
            detect_num = self.detect_num_spinbox.value()
            shuffle = self.shuffle_checkbox.isChecked()
            filter_files = self.filter_files_checkbox.isChecked()
            gen_detector = self.gen_detector_checkbox.isChecked()
            # 参数校验
            if not square_size:
                raise ValueError("棋盘格尺寸 (Square Size) 不能为空")
            if not pattern_size:
                raise ValueError("模式尺寸 (Pattern Size) 不能为空")
            if not image_dir or not os.path.isdir(image_dir):
                raise ValueError(f"图像目录无效: {image_dir}")
            if not detect_shape:
                raise ValueError("检测类型 (Pattern Type) 不能为空")

            # 转换数值
            try:
                square_size = float(square_size)
            except ValueError:
                raise ValueError("棋盘格尺寸必须为数字")

            # 初始化标定器
            calibrator = CameraCalibrator(
                pattern_size=pattern_size,
                square_size=square_size,
                image_dir=image_dir,
                detect_shape=detect_shape,
                detect_num=detect_num,
                shuffle=shuffle,
                filter_files=filter_files,
                gen_detector=gen_detector
            )
            self.log_message("标定器初始化成功")
            return calibrator
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"初始化标定失败: {str(e)}")
            self.log_message(f"错误: {str(e)}", error=True)

    def load_args(self, calibrator):
        if self.mono_stereo_combo.currentText() == "Stereo":
            if self.load_calib_input.text():
                calibrator.load_from_json(self.load_calib_input.text())
            elif self.load_left_input.text() and self.load_right_input.text():
                calibrator.load_single_json(self.load_left_input.text(), 'left')
                calibrator.load_single_json(self.load_right_input.text(), 'right')
            else:
                QtWidgets.QMessageBox.warning(self, "警告", "请先进行标定！")
                return None
        else:
            camera_side = "left" if self.mono_stereo_combo.currentText() == 'Mono' else "right"
            if self.load_left_input.text():
                calibrator.load_single_json(self.load_left_input.text(), camera_side)
            elif self.load_right_input.text():
                calibrator.load_single_json(self.load_right_input.text(), camera_side)
            else:
                QtWidgets.QMessageBox.warning(self, "警告", "请先进行标定！")
                return None
        return calibrator

    def start_calibration(self):
        """开始标定"""
        try:
            calibrator = self.load_calibrator()
            if not calibrator:
                return
            try:
                calibrator = self.load_args(calibrator)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "错误", f"加载失败: {str(e)}")
            # 开始标定过程（在单独的线程中运行）
            self.calibration_thread = QtCore.QThread()
            self.calibrator = CalibratorWorker(calibrator)
            self.calibrator.moveToThread(self.calibration_thread)

            # 连接信号和槽
            self.calibration_thread.started.connect(lambda: self.calibrator.run(self.mono_stereo_combo.currentText()))
            self.calibrator.finished.connect(self.finish_calibration)
            self.calibrator.progress.connect(self.update_progress)
            self.calibrator.result_ready.connect(self.display_results)

            # 启动线程
            self.calibration_thread.start()
            self.start_calib_button.setEnabled(False)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"初始化标定失败: {str(e)}")
            self.log_message(f"错误: {str(e)}", error=True)

    def finish_calibration(self):
        self.calibration_thread.quit()
        self.calibration_thread.deleteLater()
        # self.calibrator
        time.sleep(0.1)
        self.calibration_thread = None
        # self.calibrator = None
        self.start_calib_button.setEnabled(True)

    def save_calibration(self):
        """保存标定结果"""
        if not hasattr(self, 'calibrator') or self.calibrator is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先进行标定！")
            return

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存标定结果", "", "JSON文件 (*.json)")
        if file_path:
            self.calibrator.calibrator.save_json(file_path)
            self.log_message(f"标定结果已保存至: {file_path}")

    def load_images(self):
        """加载图像"""
        if not hasattr(self, 'calibrator') or self.calibrator is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先设置标定参数！")
            return

        try:
            left_name = '_l'
            right_name = '_r'

            # 加载图像对
            self.calibrator.image_paths, _, _ = self.calibrator._load_image_pairs(left_name, right_name,
                                                                                  self.calibrator.detect_num)

            # 显示第一对图像
            if self.calibrator.image_paths:
                left_path, right_path = self.calibrator.image_paths[0]
                self.display_images(left_path, right_path)
                self.log_message("图像加载完成")
            else:
                raise ValueError("未找到图像对")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"加载图像失败: {str(e)}")
            self.log_message(f"错误: {str(e)}", error=True)

    def detect_corners(self):
        """检测角点"""
        if not hasattr(self, 'calibrator') or self.calibrator is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先设置标定参数！")
            return

        try:
            # 获取当前显示的图像路径
            if not hasattr(self, 'current_image_pair'):
                if self.calibrator.image_paths:
                    left_path, right_path = self.calibrator.image_paths[0]
                else:
                    raise ValueError("没有加载图像")
            else:
                left_path, right_path = self.current_image_pair

            # 读取图像
            img_left = cv2.imread(left_path)
            img_right = cv2.imread(right_path)

            # 检测角点
            corners_left, corners_right = self.calibrator._find_corners(img_left, img_right)

            # 绘制角点
            if corners_left is not None and corners_right is not None:
                cv2.drawChessboardCorners(img_left, self.calibrator.pattern_size, corners_left, True)
                cv2.drawChessboardCorners(img_right, self.calibrator.pattern_size, corners_right, True)

                # 显示带角点的图像
                self.display_processed_images(img_left, img_right)
                self.log_message("角点检测成功")
            else:
                raise ValueError("未检测到角点")

        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "警告", f"角点检测失败: {str(e)}")
            self.log_message(f"警告: {str(e)}", warning=True)

    # def evaluate_error(self):
    #     """评估误差"""
    #     if not hasattr(self, 'calibrator') or self.calibrator is None:
    #         QtWidgets.QMessageBox.warning(self, "警告", "请先进行标定！")
    #         return
    #
    #     try:
    #         align_error, max_error, mean_error = self.calibrator.calibrator.evaluate_error(num=10)
    #
    #         # 更新显示
    #         self.reprojection_error_label.setText(f"Reprojection Error: {self.calibrator.calibrator.ret:.4f} pixels")
    #         self.alignment_error_label.setText(f"Alignment Error: {align_error:.2f} pixels")
    #         self.max_error_label.setText(f"Max Error: {max_error:.2f} mm")
    #         self.mean_error_label.setText(f"Mean Error: {mean_error:.2f} mm")
    #
    #         self.log_message(f"误差评估完成 - 重投影误差: {self.calibrator.calibrator.ret:.4f} 像素")
    #
    #     except Exception as e:
    #         QtWidgets.QMessageBox.critical(self, "错误", f"误差评估失败: {str(e)}")
    #         self.log_message(f"错误: {str(e)}", error=True)

    def show_3d_view(self):
        """显示3D视图"""
        if not hasattr(self, 'calibrator') or self.calibrator is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先进行标定！")
            return

        try:
            # 获取3D点数据
            points_3d = []
            for obj_points in self.calibrator.obj_points:
                points_3d.extend(obj_points[:, :3])

            # 创建3D可视化
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection='3d')

            # 转换为numpy数组
            points_array = np.array(points_3d)

            # 绘制点云
            ax.scatter(points_array[:, 0],
                       points_array[:, 1],
                       points_array[:, 2],
                       c='r', marker='o', s=50)

            # 设置标签和标题
            ax.set_xlabel('X Axis')
            ax.set_ylabel('Y Axis')
            ax.set_zlabel('Z Axis')
            ax.set_title('3D Points Visualization')

            # 显示图表
            plt.show()

            self.log_message("3D视图已显示")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"3D视图生成失败: {str(e)}")
            self.log_message(f"错误: {str(e)}", error=True)

    def display_images(self, left_path, right_path):
        """显示左右相机图像"""
        # 保存当前图像对
        self.current_image_pair = (left_path, right_path)

        # 加载并显示图像
        left_img = QtGui.QPixmap(left_path).scaled(
            self.left_image_label.size(), QtCore.Qt.KeepAspectRatio)
        right_img = QtGui.QPixmap(right_path).scaled(
            self.right_image_label.size(), QtCore.Qt.KeepAspectRatio)

        self.left_image_label.setPixmap(left_img)
        self.right_image_label.setPixmap(right_img)

    def display_processed_images(self, img_left, img_right):
        """显示处理后的图像"""
        # 将OpenCV图像转换为QPixmap
        img_left = cv2.cvtColor(img_left, cv2.COLOR_BGR2RGB)
        height, width, channel = img_left.shape
        bytes_per_line = 3 * width
        qt_image = QtGui.QImage(img_left.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888)
        left_pixmap = QtGui.QPixmap.fromImage(qt_image).scaled(
            self.left_image_label.size(), QtCore.Qt.KeepAspectRatio)

        img_right = cv2.cvtColor(img_right, cv2.COLOR_BGR2RGB)
        height, width, channel = img_right.shape
        bytes_per_line = 3 * width
        qt_image = QtGui.QImage(img_right.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888)
        right_pixmap = QtGui.QPixmap.fromImage(qt_image).scaled(
            self.right_image_label.size(), QtCore.Qt.KeepAspectRatio)

        self.left_image_label.setPixmap(left_pixmap)
        self.right_image_label.setPixmap(right_pixmap)

    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)

    def display_results(self, results):
        """显示标定结果"""
        if isinstance(results, dict):
            result_str = ""
            if 'M' in results:
                result_str += "M:\n" + str(results['M']) + "\n\n"
            if 'd' in results:
                result_str += "d:\n" + str(results['d']) + "\n\n"

            if 'M1' in results:
                result_str += "Left Camera Matrix:\n"
                result_str += str(results['M1']) + "\n\n"

            if 'd1' in results:
                result_str += "Left Distortion Coefficients:\n"
                result_str += str(results['d1'].flatten()) + "\n\n"

            if 'M2' in results:
                result_str += "Right Camera Matrix:\n"
                result_str += str(results['M2']) + "\n\n"

            if 'd2' in results:
                result_str += "Right Distortion Coefficients:\n"
                result_str += str(results['d2'].flatten()) + "\n\n"

            if 'R' in results:
                result_str += "Rotation Matrix:\n"
                result_str += str(results['R']) + "\n\n"

            if 'T' in results:
                result_str += "Translation Vector:\n"
                result_str += str(results['T']) + "\n\n"

            if 'epe' in results:
                result_str += f"Reprojection Error: {results['epe']:.4f} pixels\n"

            self.result_text_edit.setText(result_str)
        self.start_calib_button.setEnabled(True)
        self.log_message("标定完成")

    def log_message(self, message, error=False, warning=False):
        """记录日志消息"""
        if error:
            self.status_bar.setStyleSheet("color: red;")
        elif warning:
            self.status_bar.setStyleSheet("color: orange;")
        else:
            self.status_bar.setStyleSheet("")

        self.status_bar.showMessage(message)

        # 同时在文本区域显示
        if error:
            self.log_output.append(f"<font color='red'>错误: {message}</font>")
        elif warning:
            self.log_output.append(f"<font color='orange'>警告: {message}</font>")
        else:
            self.log_output.append(f"<font color='black'>{message}</font>")

        # 自动滚动到底部
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def select_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Image Directory")
        if directory:
            self.image_dir_input.setText(directory)

    def get_settings(self):
        return {
            'square_size': float(self.square_size_input.text()),
            'pattern_size': tuple(map(int, self.pattern_size_input.text().split(','))),
            'image_dir': self.image_dir_input.text()
        }


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
            "analyze_error",  # 误差分析任务
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

        # 误差分析任务参数面板
        analyze_error_panel = QtWidgets.QWidget()
        analyze_error_layout = QtWidgets.QFormLayout()

        self.analyze_error_points = QtWidgets.QSpinBox()
        self.analyze_error_points.setRange(1, 100)
        self.analyze_error_points.setValue(5)

        analyze_error_layout.addRow("分析点数:", self.analyze_error_points)
        analyze_error_layout.addRow(QtWidgets.QLabel("需要前置标定任务"))

        analyze_error_panel.setLayout(analyze_error_layout)

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
        self.param_layout.addWidget(analyze_error_panel)
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
        elif task_type == "analyze_error":
            base_info.update({
                "num_points": self.analyze_error_points.value()
            })
        elif task_type == "save_result":
            base_info.update({
                "file_path": self.save_file_path.text()
            })

        return base_info


# 如果作为主程序运行，创建应用实例
if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = CalibrationDialog()
    window.show()
    sys.exit(app.exec_())
