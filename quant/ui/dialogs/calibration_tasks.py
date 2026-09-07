"""标定任务队列：任务增删、逐条执行、参数载入与结果落盘。"""

from PyQt5 import QtWidgets, QtCore

from quant.calibration.camera_calibrator import CameraCalibrator
from quant.calibration.worker import CalibratorWorker
from quant.ui.dialogs.add_task_dialog import AddTaskDialog


def show_add_task_dialog(dialog):
    """显示添加任务对话框"""
    picker = AddTaskDialog(dialog)
    if picker.exec_() == QtWidgets.QDialog.Accepted:
        dialog.add_task_to_list(picker.get_task_info())


def add_task_to_list(dialog, task_info):
    """将任务添加到任务列表中"""
    task_item = QtWidgets.QListWidgetItem(f"{task_info['name']} ({task_info['type']})")
    task_item.setData(QtCore.Qt.UserRole, task_info)
    dialog.task_list.addItem(task_item)
    dialog.task_queue.append(task_info)

    # 更新状态栏
    dialog.status_bar.showMessage(f"已添加任务: {task_info['name']}")


def remove_selected_task(dialog):
    """移除选中的任务"""
    current_row = dialog.task_list.currentRow()
    if current_row >= 0:
        removed_task = dialog.task_list.item(current_row).data(QtCore.Qt.UserRole)
        dialog.task_list.takeItem(current_row)
        del dialog.task_queue[current_row]

        # 更新状态栏
        dialog.status_bar.showMessage(f"已移除任务: {removed_task['name']}")


def clear_all_tasks(dialog):
    """清空所有任务"""
    dialog.task_list.clear()
    dialog.task_queue.clear()

    # 更新状态栏
    dialog.status_bar.showMessage("任务列表已清空")


def start_processing_tasks(dialog):
    """开始处理任务队列"""
    if not dialog.task_queue:
        QtWidgets.QMessageBox.information(dialog, "提示", "任务列表为空，请先添加任务。")
        return

    # 初始化进度条
    dialog.tasks_progress_bar.setMaximum(len(dialog.task_queue))
    dialog.tasks_progress_bar.setValue(0)

    # 开始处理第一个任务
    dialog.current_task_index = 0
    dialog.process_next_task()


def process_next_task(dialog):
    """处理下一个任务"""
    if dialog.current_task_index >= len(dialog.task_queue):
        # 所有任务已完成
        dialog.current_task_index = -1
        dialog.update_task_details()
        dialog.status_bar.showMessage("所有任务已完成！")
        dialog.tasks_progress_bar.setValue(dialog.tasks_progress_bar.maximum())
        return

    # 获取当前任务
    current_task = dialog.task_queue[dialog.current_task_index]
    dialog.update_task_details(current_task)

    # 根据任务类型执行不同操作
    if current_task["type"] == "calibrate":
        dialog.start_calibration_task(current_task)
    elif current_task["type"] == "save_result":
        dialog.save_calibration_task(current_task)


def update_task_details(dialog, task_info=None):
    """更新任务详情显示"""
    if task_info is None:
        dialog.task_name_label.setText("未选择任务")
        dialog.task_status_label.setText("状态: 待处理")
        dialog.task_params_label.setText("参数: 无")
    else:
        dialog.task_name_label.setText(task_info["name"])
        dialog.task_status_label.setText(f"状态: 正在处理 ({dialog.current_task_index + 1}/{len(dialog.task_queue)})")
        params_text = ", ".join([f"{k}: {v}" for k, v in task_info.items() if k not in ["name", "type"]])
        dialog.task_params_label.setText(f"参数: {params_text}")


def start_calibration_task(dialog, task_info):
    """开始执行标定任务"""
    try:
        # 获取用户设置
        square_size = task_info.get("square_size", float(dialog.square_size_input.text()))
        pattern_size = task_info.get("pattern_size", tuple(map(int, dialog.pattern_size_input.text().split(','))))
        image_dir = task_info.get("image_dir", dialog.image_dir_input.text())
        detect_shape = task_info.get("detect_shape", dialog.pattern_type_combo.currentText())
        detect_num = task_info.get("detect_num", dialog.detect_num_spinbox.value())
        shuffle = task_info.get("shuffle", dialog.shuffle_checkbox.isChecked())
        filter_files = task_info.get("filter_files", dialog.filter_files_checkbox.isChecked())
        gen_detector = task_info.get("gen_detector", dialog.gen_detector_checkbox.isChecked())

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

        dialog.log_message("标定器初始化成功")

        # CameraCalibrator 不是 QObject，须由 CalibratorWorker 承载后才能 moveToThread
        dialog.calibration_thread = QtCore.QThread()
        dialog.calibrator = CalibratorWorker(calibrator)
        dialog.calibrator.moveToThread(dialog.calibration_thread)

        # 连接信号和槽：result_ready / error_occurred 二者之一即代表本条任务终结
        dialog.calibration_thread.started.connect(lambda: dialog.calibrator.run('left'))
        dialog.calibrator.progress.connect(dialog.update_progress)
        dialog.calibrator.result_ready.connect(dialog.display_results)
        dialog.calibrator.result_ready.connect(lambda _result: dialog.on_task_finished(True))
        dialog.calibrator.error_occurred.connect(lambda message: dialog.on_task_finished(False, message))

        # 启动线程
        dialog.calibration_thread.start()

    except Exception as e:
        error_msg = f"初始化标定任务失败: {str(e)}"
        dialog.log_message(error_msg, error=True)
        dialog.status_bar.showMessage(error_msg)
        dialog.on_task_finished(False)


def save_calibration_task(dialog, task_info):
    """开始执行保存标定结果任务"""
    try:
        if not getattr(dialog, 'calibrator', None):
            raise ValueError("请先进行标定！")

        # 获取文件路径
        file_path = task_info.get("file_path")
        if not file_path:
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(dialog, "保存标定结果", "", "JSON文件 (*.json)")
            if not file_path:
                dialog.on_task_finished(False, "未选择保存路径")
                return

        # 写单个 JSON 的开销可以忽略，直接同步落盘（PyQt5 未绑定 QtConcurrent）
        dialog.calibrator.calibrator.save_single_json(file_path)
        dialog.log_message(f"标定结果已保存至: {file_path}")
        dialog.on_task_finished(True)

    except Exception as e:
        error_msg = f"保存标定结果失败: {str(e)}"
        dialog.log_message(error_msg, error=True)
        dialog.status_bar.showMessage(error_msg)
        dialog.on_task_finished(False, error_msg)


def on_task_finished(dialog, success, error=None):
    """任务完成后的处理"""
    # 更新进度条
    dialog.tasks_progress_bar.setValue(dialog.current_task_index + 1)

    if success:
        dialog.status_bar.showMessage(f"任务 {dialog.current_task_index + 1} 已完成")
        dialog.log_message(f"任务 {dialog.current_task_index + 1} 成功完成")
    else:
        dialog.status_bar.showMessage(f"任务 {dialog.current_task_index + 1} 失败: {error}")
        dialog.log_message(f"任务 {dialog.current_task_index + 1} 失败: {error}", error=True)

    # 停止当前线程
    if dialog.calibration_thread and dialog.calibration_thread.isRunning():
        dialog.calibration_thread.quit()
        dialog.calibration_thread.wait()

    # 移动到下一个任务
    dialog.current_task_index += 1
    QtCore.QTimer.singleShot(100, dialog.process_next_task)  # 使用定时器确保线程正确释放
