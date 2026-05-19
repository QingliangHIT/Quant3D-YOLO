import time
import cv2
import wmi
import os
from queue import Empty
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QThreadPool, QRunnable, pyqtSlot
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread
import multiprocessing as mp
from multiprocessing import Queue, Process, Pipe
from queue import Queue as q_Queue
from queue import Full


def get_cameras_from_windows():
    """Get camera devices from Windows"""
    c = wmi.WMI()
    cameras = []

    for device in c.Win32_PnPEntity():
        if device.Name and ("camera" in device.Name.lower() or "webcam" in device.Name.lower()):
            cameras.append(device.Name)

    return cameras


def detect_available_cameras():
    """
    Detect available cameras in system
    :return: List of available camera indices
    """
    available = []
    available_cameras = get_cameras_from_windows()
    for i, name in enumerate(available_cameras):
        available.append(i)
    return available


def capture_frames(camera_index, width, height, frame_queue, barrier=None, conn=None):
    """Capture frames from camera and put into queue"""

    def process_cap(camera_index, width, height):
        if conn:
            conn.send({"type": "status", "message": "🎥 Camera loading...", "value": 0})

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            if conn:
                conn.send({"type": "error", "message": "Camera cannot be opened", "value": 3000})
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        if conn:
            conn.send({"type": "ready", "message": f"🎥 Camera ready: {width}x{height} @ {fps} FPS", "value": 3000,
                       "width": width, "height": height, "fps": fps})
        return cap

    # Status variables
    running = True
    capture = True
    cap = process_cap(camera_index, width, height)
    while running:
        if conn and conn.poll():
            try:
                msg = conn.recv()
                if msg["cmd"] == 'run':
                    capture = True
                    conn.send({"type": "status", "message": "Capturing...", "value": 3000})
                elif msg["cmd"] == 'stop':
                    running = False
                    capture = False
                elif msg["cmd"] == 'stay':
                    capture = False
                elif msg["cmd"] == 'set':
                    cap = process_cap(msg["camera_index"], msg["width"], msg["height"])
                elif msg["cmd"] == 'focus':
                    if msg['val'] == 0:
                        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                    elif msg['val'] == -1:
                        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                    else:
                        cap.set(cv2.CAP_PROP_FOCUS, msg['val'])

            except EOFError:
                pass  # Pipe has been closed

        if capture:
            if barrier:
                barrier.wait()
            ret_grab = cap.grab()
            if ret_grab:
                ret_retrieve, frame = cap.retrieve()
                if ret_retrieve:
                    time_stamp = time.time()
                    try:
                        frame_queue.put((time_stamp, frame), block=False)  # Wait max 0.1 sec
                    except Full:
                        pass  # Drop current frame
        else:
            if conn:
                conn.send({"type": "status", "message": "Video paused", "value": 0})
            time.sleep(0.1)


class FrameProcessingTask(QRunnable):
    """Frame processing task for thread pool"""

    def __init__(self, frame, output_queue):
        super().__init__()
        self.frame = frame
        self.output_queue = output_queue

    @pyqtSlot()
    def run(self):
        h, w, ch = self.frame.shape
        bytes_per_line = ch * w
        qt_image = QtGui.QImage(self.frame.data, w, h, bytes_per_line, QtGui.QImage.Format_BGR888)
        pixmap = QtGui.QPixmap.fromImage(qt_image)
        self.output_queue.put(pixmap)


class DisplayWorkerThreadPool(QObject):
    """Display worker using thread pool"""
    update_pixmap = pyqtSignal(QtGui.QPixmap)

    def __init__(self, frame_queue, out_queue, thread_count=1):
        super().__init__()
        self.running = True
        self.frame_queue = frame_queue
        self.out_queue = out_queue
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(thread_count)

    def process_frames(self):
        while self.running:
            frame = self.frame_queue.get()
            task = FrameProcessingTask(frame, self.out_queue)
            self.thread_pool.start(task)

    def stop(self):
        self.running = False
        self.thread_pool.clear()

    def run(self):
        self.running = True


class RecordingWorker(QThread):
    """Worker for recording video"""

    def __init__(self, record_queue, video_writer, parent=None):
        super().__init__(parent)
        self.record_queue = record_queue
        self.video_writer = video_writer
        self.running = True

    def run(self):
        while self.running and self.video_writer is not None:
            try:
                frame = self.record_queue.get(timeout=1)  # Read frame from main queue
                self.video_writer.write(frame)
            except Empty:
                continue
            except Exception as e:
                print("Single directory recording error:", str(e))
                break

    def stop(self):
        """Stop recording thread"""
        self.running = False


class StereoRecordingWorker(QThread):
    """Worker for stereo recording"""

    def __init__(self, record_queue, video_writer, video_writer2, parent=None):
        super().__init__(parent)
        self.record_queue = record_queue
        self.video_writer = video_writer
        self.video_writer2 = video_writer2
        if self.video_writer is not None and self.video_writer2 is not None:
            self.running = True

    def run(self):
        while self.running:
            try:
                frame, frame2 = self.record_queue.get(timeout=1)  # Read stereo frames from main queue
                self.video_writer.write(frame)
                self.video_writer2.write(frame2)
            except Empty:
                continue
            except Exception as e:
                print("Stereo recording error:", str(e))
                break

    def stop(self):
        """Stop recording thread"""
        self.running = False


class DisplayWorker(QObject):
    """Worker for displaying camera frames"""
    update_pixmap = pyqtSignal(QtGui.QPixmap, bool)

    def __init__(self, frame_queue, out_queue=None, realtime_detect=False, detector=None):
        super().__init__()
        self.running = True
        self.output = False
        self.w = 0
        self.h = 0
        self.frame_queue = frame_queue
        self.out_queue = out_queue
        self.realtime_detect = realtime_detect
        if self.realtime_detect:
            self.detector = detector
            if self.detector is None:
                from UI.tools.tools import CalibrationDetector
                self.detector = CalibrationDetector()

    def run(self):
        while self.running:
            time_stamp, frame = self.frame_queue.get()
            if self.realtime_detect:
                ret, frame = self.detector.detect(frame)
            if self.output and self.out_queue:
                self.out_queue.put(frame)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QtGui.QImage(frame.data, w, h, bytes_per_line, QtGui.QImage.Format_BGR888)
            pixmap = QtGui.QPixmap.fromImage(qt_image)
            if self.w != w or self.h != h:
                self.update_pixmap.emit(pixmap, True)
            else:
                self.update_pixmap.emit(pixmap, False)
            self.w, self.h = w, h

    def clear_frame_queue(self):
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except Empty:
                break


class StereoDisplayWorker(QObject):
    """Worker for displaying stereo camera frames"""
    update_pixmap = pyqtSignal(QtGui.QPixmap, bool)

    def __init__(self, left_queue: Queue, right_queue, out_queue=None, realtime_detect=False, detector=None,
                 reverse=False):
        super().__init__()
        self.running = True
        self.output = False
        self.left_queue = left_queue
        self.right_queue = right_queue
        self.out_queue = out_queue
        self.reverse = reverse
        self.w = 0
        self.h = 0
        self.realtime_detect = realtime_detect
        if self.realtime_detect:
            self.detector = detector
            if self.detector is None:
                from UI.tools.tools import CalibrationDetector
                self.detector = CalibrationDetector()

    def run(self):
        while self.running:
            stamp1, left_frame = self.left_queue.get()
            stamp2, right_frame = self.right_queue.get()
            if self.reverse:
                left_frame, right_frame = right_frame, left_frame
            if self.realtime_detect:
                ret, left_frame = self.detector.detect(left_frame)
                ret, right_frame = self.detector.detect(right_frame)
            if self.output and self.out_queue is not None:
                self.out_queue.put((left_frame, right_frame))
            combined_frame = cv2.vconcat([left_frame, right_frame])
            w, h, ch = combined_frame.shape[1], combined_frame.shape[0], combined_frame.strides[0]
            qt_image = QtGui.QImage(combined_frame.data, w, h, ch, QtGui.QImage.Format_BGR888)
            pixmap = QtGui.QPixmap.fromImage(qt_image)
            if self.w != w or self.h != h:
                self.update_pixmap.emit(pixmap, True)
            else:
                self.update_pixmap.emit(pixmap, False)
            self.w, self.h = w, h


class CameraWindow(QtWidgets.QWidget):
    """Main camera window widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Reader process
        self.communication_timer = None
        self.file_path2 = None
        self.reverse = False
        self.capture = None
        self.capture2 = None
        self.camera_process = None
        self.camera_process2 = None
        self.parent_conn = None
        self.parent_conn2 = None
        self.child_conn = None
        self.child_conn2 = None
        self.display_worker = None
        self.display_thread = None
        self.setWindowTitle("Real-time Camera Feed")
        self.parent = parent
        self.camera_index = 0  # Current camera index
        self.camera_index2 = None  # Current camera index
        self.fps = None
        self.width = 1920
        self.height = 1080
        self.barrier = None

        self.recording_start_time = None
        self.frame_count_record = 0
        self.frame_timer = None
        self.camera_available = None
        self.record_thread = None
        self.video_writer = None

        self.frame_queue = Queue(maxsize=30)  # Max length to prevent memory explosion
        self.frame_queue2 = Queue(maxsize=30)  # Max length to prevent memory explosion
        self.record_queue = q_Queue(maxsize=15)  # Max length to prevent memory explosion

        # Create QGraphicsView and QGraphicsScene
        self.graphics_view = QtWidgets.QGraphicsView(self)
        self.graphics_scene = QtWidgets.QGraphicsScene(self)
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.graphics_view)

        # Add hint text
        self.label = QtWidgets.QLabel("Click to open camera", self)
        self.layout().addWidget(self.label)
        self.label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.graphics_view.setVisible(False)
        self.label.show()

        # Close button (X)
        self.close_button = QtWidgets.QLabel("×", self.graphics_view)
        self.close_button.setStyleSheet("""
                    font-size: 20px;
                    color: red;
                    background-color: rgba(255, 255, 255, 180);
                    border-radius: 10px;
                    padding: 2px 6px;
                """)
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.setAlignment(Qt.AlignCenter)
        self.close_button.setToolTip("Click to close camera")
        self.close_button.mousePressEvent = lambda e: self.close_camera()
        self.close_button.hide()

        # Switch camera button (index)
        self.switch_camera_btn = QtWidgets.QLabel(" ", self.graphics_view)
        self.switch_camera_btn.setStyleSheet("""
            font-size: 20px;
            color: grey;
            background-color: rgba(255, 255, 255, 180);
            border-radius: 10px;
            padding: 2px 6px;
        """)
        self.switch_camera_btn.setCursor(Qt.PointingHandCursor)
        self.switch_camera_btn.setAlignment(Qt.AlignCenter)
        self.switch_camera_btn.setToolTip("Click to switch camera")
        self.switch_camera_btn.mousePressEvent = self.on_switch_camera_click
        self.switch_camera_btn.mouseDoubleClickEvent = self.on_switch_camera_double_click
        self.switch_camera_btn.hide()

        # FPS label
        self.fps_label = QtWidgets.QLabel("FPS:     ", self.graphics_view)
        self.fps_label.setStyleSheet("""
            font-size: 14px;
            color: grey;
            background-color: transparent;  /* Transparent background */
            padding: 0px;
        """)
        self.fps_label.setAlignment(Qt.AlignCenter)
        self.fps_label.hide()  # Hidden by default, show when mouse enters

        # Timer for updating display
        self.frame_counter = -1
        self.fps_timer = QtCore.QTimer(self)
        self.fps_timer.timeout.connect(self.update_fps)

        # Image container
        self.pixmap_item = None
        self._first_fit = False

        # Mouse interaction variables
        self.mouse_pressed = False
        self.last_mouse_pos = None
        self.realtime_detect = False

        # Bind mouse events
        self.graphics_view.wheelEvent = self.wheelEvent
        self.graphics_view.mousePressEvent = self.mousePressEvent
        self.graphics_view.mouseMoveEvent = self.mouseMoveEvent
        self.graphics_view.mouseReleaseEvent = self.mouseReleaseEvent
        self.graphics_view.mouseDoubleClickEvent = self.mouseDoubleClickEvent

    def resizeEvent(self, event):
        """Resize image when window size changes"""
        super().resizeEvent(event)
        if self.pixmap_item:
            self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def set_fps(self, visible):
        self.fps_label.setVisible(visible)
        self.fps_label.move(10, 10)
        if self.fps_label.isVisible():
            self.frame_counter = 0
            self.fps_timer.start(1000)  # Update every second
        else:
            self.fps_label.hide()
            self.fps_timer.stop()
            self.frame_counter = -1

    def change_camera(self, camera_index, camera_index2):
        """
        Switch camera index
        """
        self.camera_index = camera_index
        self.camera_index2 = camera_index2
        self.start_camera(True, mode=self.parent.mode)  # Open new camera

    def change_resolution(self, width, height):
        """
        Change camera resolution
        """
        self.width = width
        self.height = height
        self.parent.statusbar.showMessage("⚠️ Resolution change will take effect next time...", 3000)

    def on_switch_camera_click(self, event):
        if self.camera_available is None:
            self.init_camera()
        self.parent.statusbar.showMessage(f'Camera available: {self.camera_available}', 3000)

    def on_switch_camera_double_click(self, event):
        if self.camera_available is None:
            self.init_camera()

        if self.parent.mode == "stereo":
            self.parent.statusbar.showMessage(f'Camera exchanged!', 3000)
            self.reverse = not self.reverse
            if self.reverse:
                self.switch_camera_btn.setText(f"{self.camera_index2}|{self.camera_index}")
            else:
                self.switch_camera_btn.setText(f"{self.camera_index}|{self.camera_index2}")
            self.stop_camera()
            self.start_camera(mode=self.parent.mode)
        else:
            return
        event.accept()

    def update_fps(self):
        fps = self.frame_counter
        self.fps_label.setText(f"FPS: {fps}")
        self.frame_counter = 0  # Reset counter

    def check_pipe(self, conn, conn2=None):
        if conn.poll():  # If message arrived
            try:
                msg = conn.recv()
                if msg["type"] == "status":
                    self.parent.statusbar.showMessage(msg["message"], msg["value"])
                elif msg["type"] == "ready":
                    self.parent.statusbar.showMessage(msg["message"], msg["value"])
                    self.width = msg["width"]
                    self.height = msg["height"]
                    self.fps = msg["fps"]
                    self.capture = True
                    self.label.hide()
                    self.graphics_view.setVisible(True)
                elif msg["type"] == "error":
                    QtWidgets.QMessageBox.warning(self, "Camera Error", msg["message"])
            except EOFError:
                pass
        if conn2 and conn2.poll():  # If message arrived
            try:
                msg = conn2.recv()
                if msg["type"] == "status":
                    self.parent.statusbar.showMessage(msg["message"], msg["value"])
                elif msg["type"] == "ready":
                    self.parent.statusbar.showMessage(msg["message"], msg["value"])
                    self.width = msg["width"]
                    self.height = msg["height"]
                    self.fps = msg["fps"]
                    self.capture2 = True
                    self.label.hide()
                    self.graphics_view.setVisible(True)
                elif msg["type"] == "error":
                    QtWidgets.QMessageBox.warning(self, "Camera Error", msg["message"])
            except EOFError:
                pass

    def init_camera(self):
        """Initialize camera"""
        self.camera_available = detect_available_cameras()
        # Find next camera in list
        if len(self.camera_available) > 0:
            self.camera_index = self.camera_available[0]
        else:
            self.camera_index = None
        if len(self.camera_available) > 1:
            self.camera_index2 = self.camera_available[1]
        else:
            self.camera_index2 = None
        if self.camera_index is None and self.camera_index2 is None:
            QtWidgets.QMessageBox.information(self, "Info", "No available cameras found.")
            return

    def start_camera(self, shortcut=False, mode='mono'):
        """Start camera with multi-threading for capture and display"""
        self.label.setText('Camera loading...')
        if self.parent.mode == "mono":
            self.barrier = None
        elif self.parent.mode == "stereo":
            self.barrier = mp.Barrier(2)

        if self.camera_process and isinstance(self.camera_process, Process):
            if self.camera_process.is_alive():
                if shortcut:
                    self.capture = False
                    self.stop_camera()
                    self.parent_conn.send(
                        {"cmd": "set", "camera_index": self.camera_index, "width": self.width, "height": self.height})
                    while not self.capture:
                        time.sleep(0.1)
                self.parent_conn.send({"cmd": "run"})
                self.capture = True
                self.label.hide()
                self.graphics_view.setVisible(True)
        else:
            # Start subprocess
            self.parent_conn, self.child_conn = Pipe()  # Create pipe ends
            self.camera_process = Process(
                target=capture_frames,
                args=(self.camera_index, self.width, self.height, self.frame_queue, self.barrier, self.child_conn),
                daemon=True
            )
            self.camera_process.start()
            # Listen for messages from subprocess in main thread
            self.communication_timer = QtCore.QTimer()
            self.communication_timer.timeout.connect(lambda: self.check_pipe(self.parent_conn, self.parent_conn2))
            self.communication_timer.start(100)  # Check every 100ms for new messages

        if mode == 'stereo':
            if self.camera_process2 and isinstance(self.camera_process2, Process):
                if self.camera_process2.is_alive():
                    if shortcut:
                        self.capture2 = False
                        self.stop_camera()
                        self.parent_conn2.send(
                            {"cmd": "set", "camera_index": self.camera_index2, "width": self.width,
                             "height": self.height})
                        while not self.capture2:
                            time.sleep(0.1)
                    self.parent_conn2.send({"cmd": "run"})
                    self.capture2 = True
                    self.label.hide()
                    self.graphics_view.setVisible(True)
            else:
                # Start subprocess
                self.parent_conn2, self.child_conn2 = Pipe()  # Create pipe ends
                self.camera_process2 = Process(
                    target=capture_frames,
                    args=(self.camera_index2, self.width, self.height, self.frame_queue2, self.barrier,
                          self.child_conn2),
                    daemon=True
                )
                self.camera_process2.start()

        if mode == 'mono':
            if not self.display_thread:
                self.display_worker = DisplayWorker(self.frame_queue, self.record_queue, self.realtime_detect,
                                                    self.parent.detector)
                self.display_thread = QThread()
                self.display_worker.moveToThread(self.display_thread)
                self.display_worker.update_pixmap.connect(self.on_update_pixmap)
                self.display_thread.started.connect(self.display_worker.run)
            self.display_worker.running = True
            self.display_thread.start()
        elif mode == 'stereo':
            if not self.display_thread:
                self.display_worker = StereoDisplayWorker(self.frame_queue, self.frame_queue2, self.record_queue,
                                                          self.realtime_detect, self.parent.detector, self.reverse)
                self.display_thread = QThread()
                self.display_worker.moveToThread(self.display_thread)
                self.display_worker.update_pixmap.connect(self.on_update_pixmap)
                self.display_thread.started.connect(self.display_worker.run)
            self.display_worker.running = True
            self.display_thread.start()

    def update_display(self, frame):
        """Update display with frame"""
        h, w, ch = frame.shape
        qt_image = QtGui.QImage(frame.data, w, h, ch * w, QtGui.QImage.Format_BGR888)
        pixmap = QtGui.QPixmap.fromImage(qt_image)
        if self.pixmap_item is None:
            self.pixmap_item = self.graphics_scene.addPixmap(pixmap)
            self.graphics_scene.setSceneRect(QtCore.QRectF(pixmap.rect()))
            self._first_fit = False
        else:
            self.pixmap_item.setPixmap(pixmap)
        if not self._first_fit:
            self.graphics_scene.setSceneRect(QtCore.QRectF(self.pixmap_item.pixmap().rect()))
            self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            self._first_fit = True
        # Update frame count
        self.frame_counter += 1

    def stop_camera(self):
        """Stop camera"""
        self.capture = False
        if self.camera_process and isinstance(self.camera_process, Process):
            if self.camera_process.is_alive():
                self.parent_conn.send({"cmd": "stay"})
                if self.parent.mode == 'stereo' and self.parent_conn2:
                    self.parent_conn2.send({"cmd": "stay"})
        if self.display_thread and self.display_thread.isRunning():
            self.display_worker.running = False
            self.display_thread.quit()
            self.display_thread.wait()
        self.display_thread = None
        self.graphics_scene.removeItem(self.pixmap_item)
        self.pixmap_item = None
        self.graphics_view.setVisible(False)
        self.label.setText('Click to open camera')
        self.label.show()
        time.sleep(0.2)

    def on_update_pixmap(self, pixmap, resize):
        """Update pixmap"""
        if self.pixmap_item is None:
            self.pixmap_item = self.graphics_scene.addPixmap(pixmap)
        else:
            self.pixmap_item.setPixmap(pixmap)

        if resize:
            self.graphics_scene.setSceneRect(QtCore.QRectF(self.pixmap_item.pixmap().rect()))
            self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

        # Update frame count
        if self.frame_counter >= 0:
            self.frame_counter += 1

    def close_camera(self):
        """Close camera and release resources"""
        self.stop_camera()

    def cleanup(self):
        """Clean up camera resources"""
        self.stop_camera()

        # Close video writer
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

        if self.camera_process and isinstance(self.camera_process, mp.Process):
            if self.camera_process.is_alive():
                self.parent_conn.send({"cmd": "stop"})
                self.camera_process.join(timeout=1)
                if self.camera_process.is_alive():
                    self.camera_process.terminate()
                    self.camera_process.join()
            self.camera_process = None

        if self.camera_process2 and isinstance(self.camera_process2, mp.Process):
            if self.camera_process2.is_alive():
                self.parent_conn2.send({"cmd": "stop"})
                self.camera_process2.join(timeout=1)
                if self.camera_process2.is_alive():
                    self.camera_process2.terminate()
                    self.camera_process2.join()
            self.camera_process2 = None

        # Clean up timers
        if self.communication_timer and self.communication_timer.isActive():
            self.communication_timer.stop()
            self.communication_timer.deleteLater()
            self.communication_timer = None

        # Clean up FPS related resources
        if self.fps_timer and self.fps_timer.isActive():
            self.fps_timer.stop()
        self.parent.statusbar.showMessage(f"✅ CameraWindow resources released", 3000)

    def start_snapshot(self):
        """
        Capture current camera frame and save as image file
        """
        from datetime import datetime
        save_dir = os.path.join(self.parent.project_manager.current_project_dir,
                                self.parent.project_manager.save_dir)

        # Create save directory if not exists
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # Generate filename, e.g.: IMG20250406_120000_left.jpg
        ms = datetime.now().microsecond // 1000  # Microseconds to milliseconds
        filename = f"IMG{datetime.now().strftime('%Y%m%d_%H%M%S')}{ms:03d}"

        if self.parent.mode == 'mono':
            file_path = os.path.join(save_dir, filename + ".jpg")
            try:
                # Get current frame
                self.display_worker.output = True
                frame = self.record_queue.get(timeout=2)  # Wait max 2 seconds to get a frame
                self.display_worker.output = False
                cv2.imwrite(file_path, frame)
                self.parent.statusbar.showMessage(f"📸 Snapshot saved: {file_path}", 3000)
                self.parent.project_manager.i_img += 1

                # Add to file list
                self.parent.camera_files_dock.update_file_list([file_path], -1)

            except Empty:
                QtWidgets.QMessageBox.warning(self, "Snapshot Error", "Cannot get current frame, queue is empty.")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Snapshot Error", f"Save failed: {str(e)}")

        elif self.parent.mode == 'stereo':
            file_path = os.path.join(save_dir, filename)
            left_path = file_path + "_l.jpg"
            right_path = file_path + "_r.jpg"

            try:
                # Get stereo frames
                self.display_worker.output = True
                left_frame, right_frame = self.record_queue.get(timeout=2)
                self.display_worker.output = False
                cv2.imwrite(left_path, left_frame)
                cv2.imwrite(right_path, right_frame)

                self.parent.statusbar.showMessage(f"📸 Stereo snapshot saved: {save_dir}", 3000)
                self.parent.project_manager.i_img += 1

                # Add to file list
                self.parent.camera_files_dock.update_file_list([file_path], -1)
            except Empty:
                QtWidgets.QMessageBox.warning(self, "Snapshot Error", "Cannot get current frame, queue is empty.")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Snapshot Error", f"Save failed: {str(e)}")

    def start_recording(self):
        """Start recording"""
        from datetime import datetime
        save_dir = os.path.join(self.parent.project_manager.current_project_dir,
                                self.parent.project_manager.save_dir)

        filename = f"VID{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.file_path = os.path.join(str(save_dir), filename)

        fourcc = cv2.VideoWriter_fourcc(*'XVID')

        self.display_worker.output = True

        if self.parent.mode == 'mono':
            self.video_writer = cv2.VideoWriter(self.file_path + '.avi', fourcc, self.fps, (self.width, self.height))
            self.recording_worker = RecordingWorker(self.record_queue, self.video_writer)

        elif self.parent.mode == 'stereo':
            self.video_writer = cv2.VideoWriter(self.file_path + '_l.avi', fourcc, self.fps,
                                                (self.width, self.height))
            self.video_writer2 = cv2.VideoWriter(self.file_path + '_r.avi', fourcc, self.fps,
                                                 (self.width, self.height))
            self.recording_worker = StereoRecordingWorker(self.record_queue, self.video_writer, self.video_writer2)

        self.recording_worker.start()

        self.recording_start_time = QtCore.QTime.currentTime()
        self.frame_count_record = 0
        if self.frame_timer is None:
            self.frame_timer = QtCore.QTimer(self)
            self.frame_timer.timeout.connect(self.update_recording_info)
        self.frame_timer.start(1000)

    def clear_frame_queue(self):
        """Clear frame queue"""
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except Empty:
                break

    def stop_recording(self):
        """Stop recording"""
        if hasattr(self, 'video_writer') and self.video_writer:
            self.display_worker.output = False
            self.recording_worker.stop()
            self.recording_worker.wait()  # Wait for thread to finish

            # Release video writer
            self.video_writer.release()
            del self.video_writer
            self.video_writer = None
            if self.parent.mode == 'stereo' and hasattr(self, 'video_writer2') and self.video_writer2:
                self.video_writer2.release()
                del self.video_writer2
                self.video_writer2 = None

            if self.frame_timer and self.frame_timer.isActive():
                self.frame_timer.stop()
                self.frame_timer = None

            self.parent.statusbar.showMessage(
                f"🛑 Recording ended, duration {self.time_str}", 3000)

            self.parent.project_manager.i_vid += 1
            self.parent.camera_files_dock.update_file_list([self.file_path], -1)

    def update_recording_info(self):
        """Update recording info"""
        if self.recording_start_time:
            elapsed = self.recording_start_time.msecsTo(QtCore.QTime.currentTime())
            self.time_str = QtCore.QTime(0, 0).addMSecs(elapsed).toString("hh:mm:ss")
            self.parent.statusbar.showMessage(
                f"✅ Recording... Duration: {self.time_str}, fps: {self.frame_count_record}")
            self.frame_count_record = 0  # Calculate frame count per second at 20fps

    # ===== Mouse interaction methods =====
    def zoom_in(self):
        self.graphics_view.scale(1.1, 1.1)

    def zoom_out(self):
        self.graphics_view.scale(0.9, 0.9)

    def wheelEvent(self, event):
        if not self.parent.is_fixed_size:
            delta = event.angleDelta().y()
            if delta > 0:
                self.graphics_view.scale(1.1, 1.1)
            elif delta < 0:
                self.graphics_view.scale(0.9, 0.9)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or event.button() == Qt.MouseButton.RightButton:
            self.mouse_pressed = True
            self.last_mouse_pos = event.pos()
            self.graphics_view.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton and self.label.isVisible() and self.label.geometry().contains(
                event.pos()):
            self.start_camera(mode=self.parent.mode)
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.close_button.isVisible():
                self.reset_hide_timer()
            else:
                self.close_button.show()
                if self.parent.mode == 'mono':
                    self.switch_camera_btn.setText(str(self.camera_index))
                elif self.parent.mode == 'stereo':
                    self.switch_camera_btn.setText(f"{self.camera_index}|{self.camera_index + 1}")
                self.switch_camera_btn.show()
                self.close_button.move(self.graphics_view.width() - self.close_button.width() - 10, 10)
                self.switch_camera_btn.move(
                    self.close_button.x() - self.switch_camera_btn.width() - 8,
                    self.close_button.y()
                )
        else:
            QtWidgets.QGraphicsView.mousePressEvent(self.graphics_view, event)

    def mouseMoveEvent(self, event):
        if self.mouse_pressed:
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            h_scroll = self.graphics_view.horizontalScrollBar()
            v_scroll = self.graphics_view.verticalScrollBar()
            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.mouse_pressed = False
            self.graphics_view.setCursor(Qt.ArrowCursor)
        else:
            QtWidgets.QGraphicsView.mouseReleaseEvent(self.graphics_view, event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def enterEvent(self, event):
        """Show buttons when mouse enters window area"""
        if self.close_button.isVisible():
            self.reset_hide_timer()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide buttons when mouse leaves window area"""
        self.reset_hide_timer()
        super().leaveEvent(event)

    def reset_hide_timer(self):
        """Reset hide button timer"""
        if hasattr(self, 'hide_timer'):
            self.hide_timer.stop()
        self.hide_timer = QtCore.QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_floating_button)
        self.hide_timer.start(2000)

    def hide_floating_button(self):
        """Hide close button"""
        self.close_button.hide()
        self.switch_camera_btn.hide()
