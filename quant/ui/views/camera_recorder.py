"""相机抓拍与录像：快照保存、录像线程启停与录制状态刷新。"""

import os
from datetime import datetime
from queue import Empty
import cv2
from PyQt5 import QtWidgets, QtCore
from quant.camera.workers import RecordingWorker


def _snapshot_dir(view):
    """返回工程输出目录；工程未打开时返回 None 并提示。"""
    project = view.parent.project_manager
    if not getattr(project, "current_project_dir", None):
        QtWidgets.QMessageBox.information(view, "Notice", "Please create or open a project first.")
        return None
    save_dir = os.path.join(project.current_project_dir, project.save_dir or "capture")
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


def start_snapshot(view):
    """
    Capture current camera frame and save as image file
    """
    save_dir = _snapshot_dir(view)
    if save_dir is None:
        return

    # Generate filename, e.g.: IMG20250406_120000_left.jpg
    ms = datetime.now().microsecond // 1000  # Microseconds to milliseconds
    filename = f"IMG{datetime.now().strftime('%Y%m%d_%H%M%S')}{ms:03d}"

    file_path = os.path.join(save_dir, filename + ".jpg")
    try:
        # Get current frame
        view.display_worker.output = True
        frame = view.record_queue.get(timeout=2)  # Wait max 2 seconds to get a frame
        view.display_worker.output = False
        if not cv2.imwrite(file_path, frame):
            raise IOError(f"cannot write {file_path}")
        view.parent.statusbar.showMessage(f"📸 Snapshot saved: {file_path}", 3000)
        view.parent.project_manager.i_img += 1

        # Add to file list
        view.parent.camera_files_dock.update_file_list([file_path], -1)

    except Empty:
        view.display_worker.output = False
        QtWidgets.QMessageBox.warning(view, "Snapshot Error", "Cannot get current frame, queue is empty.")
    except Exception as e:
        view.display_worker.output = False
        QtWidgets.QMessageBox.warning(view, "Snapshot Error", f"Save failed: {str(e)}")


def start_recording(view):
    """Start recording"""
    save_dir = _snapshot_dir(view)
    if save_dir is None:
        return

    if view.display_worker is None or not view.capture:
        QtWidgets.QMessageBox.information(view, "Notice", "Please start the camera before recording.")
        return
    # 相机驱动可能上报 fps=0，VideoWriter 用 0 会打不开，退回常见默认值
    fps = float(view.fps) if view.fps else 30.0

    filename = f"VID{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    view.file_path = os.path.join(str(save_dir), filename)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')

    view.display_worker.output = True

    view.video_writer = cv2.VideoWriter(view.file_path + '.avi', fourcc, fps, (int(view.width), int(view.height)))
    if not view.video_writer.isOpened():
        view.display_worker.output = False
        view.video_writer.release()
        view.video_writer = None
        QtWidgets.QMessageBox.warning(view, "Recording Error", "Cannot open video writer for this resolution.")
        return

    view.recording_worker = RecordingWorker(view.record_queue, view.video_writer)

    view.recording_worker.start()

    view.recording_start_time = QtCore.QTime.currentTime()
    view.frame_count_record = 0
    if view.frame_timer is None:
        view.frame_timer = QtCore.QTimer(view)
        view.frame_timer.timeout.connect(view.update_recording_info)
    view.frame_timer.start(1000)


def clear_frame_queue(view):
    """Clear frame queue"""
    while not view.frame_queue.empty():
        try:
            view.frame_queue.get_nowait()
        except Empty:
            break


def stop_recording(view):
    """Stop recording"""
    if getattr(view, 'video_writer', None):
        view.display_worker.output = False
        view.recording_worker.stop()
        view.recording_worker.wait()  # Wait for thread to finish

        # Release video writer
        view.video_writer.release()
        view.video_writer = None

        if view.frame_timer and view.frame_timer.isActive():
            view.frame_timer.stop()
        view.frame_timer = None

        view.parent.statusbar.showMessage(
            f"🛑 Recording ended, duration {getattr(view, 'time_str', '00:00:00')}", 3000)

        view.parent.project_manager.i_vid += 1
        view.parent.camera_files_dock.update_file_list([view.file_path], -1)


def update_recording_info(view):
    """Update recording info"""
    if view.recording_start_time:
        elapsed = view.recording_start_time.msecsTo(QtCore.QTime.currentTime())
        view.time_str = QtCore.QTime(0, 0).addMSecs(elapsed).toString("hh:mm:ss")
        view.parent.statusbar.showMessage(
            f"✅ Recording... Duration: {view.time_str}, fps: {view.frame_count_record}")
        view.frame_count_record = 0  # Calculate frame count per second at 20fps
