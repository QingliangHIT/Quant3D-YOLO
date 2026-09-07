"""相机采集流控制：管道探测、初始化、进程启动、帧刷新与资源回收。"""

import time
import multiprocessing as mp
from multiprocessing import Process, Pipe
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QThread
from quant.camera.capture_process import capture_frames
from quant.camera.discovery import detect_available_cameras
from quant.camera.workers import DisplayWorker, frame_to_pixmap


def check_pipe(view, conn):
    if conn.poll():  # If message arrived
        try:
            msg = conn.recv()
            if msg["type"] == "status":
                view.parent.statusbar.showMessage(msg["message"], msg["value"])
            elif msg["type"] == "ready":
                view.parent.statusbar.showMessage(msg["message"], msg["value"])
                view.width = msg["width"]
                view.height = msg["height"]
                view.fps = msg["fps"] or 30
                view.capture = True
                view.label.hide()
                view.graphics_view.setVisible(True)
            elif msg["type"] == "error":
                view.capture = True  # 释放 start_camera 的等待，避免无相机时永久阻塞
                QtWidgets.QMessageBox.warning(view, "Camera Error", msg["message"])
        except EOFError:
            pass
        except (OSError, KeyError) as exc:
            # 管道断裂或消息字段缺失时仅提示，不把异常抛进定时器槽
            view.parent.statusbar.showMessage(f"Camera pipe error: {exc}", 3000)


def init_camera(view):
    """Initialize camera"""
    view.camera_available = detect_available_cameras()
    # Find next camera in list
    if len(view.camera_available) > 0:
        view.camera_index = view.camera_available[0]
    else:
        view.camera_index = None
    if view.camera_index is None:
        QtWidgets.QMessageBox.information(view, "Info", "No available cameras found.")
        return


def start_camera(view, shortcut=False, mode='mono'):
    """Start camera with multi-threading for capture and display"""
    view.label.setText('Camera loading...')

    if view.camera_process and isinstance(view.camera_process, Process):
        if view.camera_process.is_alive():
            if shortcut:
                view.capture = False
                view.stop_camera()
                view.parent_conn.send(
                    {"cmd": "set", "camera_index": view.camera_index, "width": view.width, "height": view.height})
                # 等待子进程回 ready/error；带超时，相机不可用时不能永久阻塞 GUI 线程
                deadline = time.time() + 5
                while not view.capture and time.time() < deadline:
                    view.check_pipe(view.parent_conn)
                    QtWidgets.QApplication.processEvents()
                    time.sleep(0.05)
                if not view.capture:
                    view.parent.statusbar.showMessage("⚠️ Camera did not respond", 3000)
                    return
            view.parent_conn.send({"cmd": "run"})
            view.capture = True
            view.label.hide()
            view.graphics_view.setVisible(True)
    else:
        # Start subprocess
        view.parent_conn, view.child_conn = Pipe()  # Create pipe ends
        view.camera_process = Process(
            target=capture_frames,
            args=(view.camera_index, view.width, view.height, view.frame_queue, None, view.child_conn),
            daemon=True
        )
        view.camera_process.start()
        # Listen for messages from subprocess in main thread
        view.communication_timer = QtCore.QTimer()
        view.communication_timer.timeout.connect(lambda: view.check_pipe(view.parent_conn))
        view.communication_timer.start(100)  # Check every 100ms for new messages

    if not view.display_thread:
        view.display_worker = DisplayWorker(view.frame_queue, view.record_queue, view.realtime_detect,
                                            view.parent.detector)
        view.display_thread = QThread()
        view.display_worker.moveToThread(view.display_thread)
        view.display_worker.update_pixmap.connect(view.on_update_pixmap)
        view.display_thread.started.connect(view.display_worker.run)
    view.display_worker.running = True
    view.display_thread.start()


def update_display(view, frame):
    """Update display with frame"""
    pixmap = frame_to_pixmap(frame)
    if pixmap is None:
        return
    if view.pixmap_item is None:
        view.pixmap_item = view.graphics_scene.addPixmap(pixmap)
        view.graphics_scene.setSceneRect(QtCore.QRectF(pixmap.rect()))
        view._first_fit = False
    else:
        view.pixmap_item.setPixmap(pixmap)
    if not view._first_fit:
        view.graphics_scene.setSceneRect(QtCore.QRectF(view.pixmap_item.pixmap().rect()))
        view.graphics_view.fitInView(view.pixmap_item, Qt.KeepAspectRatio)
        view._first_fit = True
    # Update frame count
    view.frame_counter += 1


def stop_camera(view):
    """Stop camera"""
    view.capture = False
    if view.camera_process and isinstance(view.camera_process, Process):
        if view.camera_process.is_alive():
            try:
                view.parent_conn.send({"cmd": "stay"})
            except OSError:
                pass
    if view.display_thread and view.display_thread.isRunning():
        view.display_worker.running = False
        view.display_thread.quit()
        # 工作线程每 0.5s 检查一次 running，超时意味着线程卡死，不能无限等待 GUI
        if not view.display_thread.wait(2000):
            print("Warning: display thread did not stop within 2s")
    view.display_thread = None
    if view.pixmap_item is not None:
        view.graphics_scene.removeItem(view.pixmap_item)
        view.pixmap_item = None
    view.graphics_view.setVisible(False)
    view.label.setText('Click to open camera')
    view.label.show()
    time.sleep(0.2)


def on_update_pixmap(view, pixmap, resize):
    """Update pixmap"""
    if view.pixmap_item is None:
        view.pixmap_item = view.graphics_scene.addPixmap(pixmap)
    else:
        view.pixmap_item.setPixmap(pixmap)

    if resize:
        view.graphics_scene.setSceneRect(QtCore.QRectF(view.pixmap_item.pixmap().rect()))
        view.graphics_view.fitInView(view.pixmap_item, Qt.KeepAspectRatio)

    # Update frame count
    if view.frame_counter >= 0:
        view.frame_counter += 1


def close_camera(view):
    """Close camera and release resources"""
    view.stop_camera()


def cleanup(view):
    """Clean up camera resources"""
    view.stop_camera()

    # Close video writer
    if getattr(view, "video_writer", None):
        view.video_writer.release()
        view.video_writer = None

    if view.camera_process and isinstance(view.camera_process, mp.Process):
        if view.camera_process.is_alive():
            try:
                view.parent_conn.send({"cmd": "stop"})
            except OSError:
                pass
            view.camera_process.join(timeout=1)
            if view.camera_process.is_alive():
                view.camera_process.terminate()
                view.camera_process.join()
        view.camera_process = None
        try:
            view.parent_conn.close()
            view.child_conn.close()
        except OSError:
            pass

    # Clean up timers
    if view.communication_timer and view.communication_timer.isActive():
        view.communication_timer.stop()
        view.communication_timer.deleteLater()
        view.communication_timer = None

    # Clean up FPS related resources
    if view.fps_timer and view.fps_timer.isActive():
        view.fps_timer.stop()
    view.parent.statusbar.showMessage("✅ CameraWindow resources released", 3000)
