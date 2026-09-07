"""标定流程对话框：图像采集、角点预览、执行标定与结果展示。"""

import os
import time

from PyQt5 import QtWidgets, QtCore

from quant.calibration.camera_calibrator import CameraCalibrator
from quant.calibration.pattern_detector import CalibrationDetector
from quant.calibration.worker import CalibratorWorker
from quant.ui.dialogs import calibration_pages, calibration_tasks


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
        self.calibrator = None
        self.load_calib_button = None
        self.init_ui()

    def init_ui(self):
        calibration_pages.build_ui(self)

    def add_task_list_page(self):
        calibration_pages.build_task_list_page(self)

    def show_add_task_dialog(self):
        calibration_tasks.show_add_task_dialog(self)

    def add_task_to_list(self, task_info):
        calibration_tasks.add_task_to_list(self, task_info)

    def remove_selected_task(self):
        calibration_tasks.remove_selected_task(self)

    def clear_all_tasks(self):
        calibration_tasks.clear_all_tasks(self)

    def start_processing_tasks(self):
        return calibration_tasks.start_processing_tasks(self)

    def process_next_task(self):
        return calibration_tasks.process_next_task(self)

    def update_task_details(self, task_info=None):
        calibration_tasks.update_task_details(self, task_info)

    def start_calibration_task(self, task_info):
        calibration_tasks.start_calibration_task(self, task_info)

    def save_calibration_task(self, task_info):
        return calibration_tasks.save_calibration_task(self, task_info)

    def on_task_finished(self, success, error=None):
        calibration_tasks.on_task_finished(self, success, error)

    def add_calibration_settings_page(self):
        calibration_pages.build_settings_page(self)

    def load_calibration_parameters(self, event):
        """选择已有标定参数文件并回填到输入框。"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择标定参数文件", "", "JSON 文件 (*.json)"
        )
        if file_path:
            self.load_calib_input.setText(file_path)

    def add_image_detection_page(self):
        calibration_pages.build_image_detection_page(self)

    def select_image_directory(self):
        """选择图像目录。"""
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Image Directory",
            self.image_dir if self.image_dir else "",
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
        if self.load_calib_input.text():
            calibrator.load_single_json(self.load_calib_input.text(), 'left')
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
            self.calibration_thread.started.connect(lambda: self.calibrator.run('left'))
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
        """标定线程收尾：释放线程并恢复按钮状态。"""
        self.calibration_thread.quit()
        self.calibration_thread.deleteLater()
        time.sleep(0.1)
        self.calibration_thread = None
        self.start_calib_button.setEnabled(True)

    def save_calibration(self):
        """保存标定结果"""
        if not getattr(self, 'calibrator', None):
            QtWidgets.QMessageBox.warning(self, "警告", "请先进行标定！")
            return

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存标定结果", "", "JSON文件 (*.json)")
        if file_path:
            self.calibrator.calibrator.save_single_json(file_path)
            self.log_message(f"标定结果已保存至: {file_path}")

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

    def get_settings(self):
        return {
            'square_size': float(self.square_size_input.text()),
            'pattern_size': tuple(map(int, self.pattern_size_input.text().split(','))),
            'image_dir': self.image_dir_input.text()
        }
