"""帧处理与显示/录制的工作线程（QRunnable / QThread）。"""

from queue import Empty

import numpy as np
from PyQt5 import QtGui
from PyQt5.QtCore import QThreadPool, QRunnable, pyqtSlot, pyqtSignal, QObject, QThread


def frame_to_pixmap(frame):
    """把 OpenCV BGR 帧转为 QPixmap；帧非法时返回 None。

    QImage 直接引用 numpy 缓冲区：非连续内存会画出乱码，灰度帧会直接崩溃，
    因此这里统一做连续化与通道数校验，所有显示路径共用。
    """
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        return None
    frame = np.ascontiguousarray(frame)
    height, width, channels = frame.shape
    image = QtGui.QImage(frame.data, width, height, channels * width, QtGui.QImage.Format_BGR888)
    return QtGui.QPixmap.fromImage(image)


class FrameProcessingTask(QRunnable):
    """Frame processing task for thread pool"""

    def __init__(self, frame, output_queue):
        super().__init__()
        self.frame = frame
        self.output_queue = output_queue

    @pyqtSlot()
    def run(self):
        pixmap = frame_to_pixmap(self.frame)
        if pixmap is not None:
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
            try:
                frame = self.frame_queue.get(timeout=0.5)  # 带超时，保证 stop() 能退出循环
            except Empty:
                continue
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
                if frame is not None:
                    self.video_writer.write(frame)
            except Empty:
                continue
            except Exception as e:
                print("Single directory recording error:", str(e))
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
                from quant.calibration.pattern_detector import CalibrationDetector
                self.detector = CalibrationDetector()

    def run(self):
        while self.running:
            try:
                time_stamp, frame = self.frame_queue.get(timeout=0.5)
            except Empty:
                continue  # 超时后回到循环检查 running，否则 stop_camera 的 wait() 会永久挂起
            if self.realtime_detect:
                try:
                    ret, frame = self.detector.detect(frame)
                except Exception as exc:  # noqa: BLE001 - 检测失败不应中断取流，退回原始帧继续显示
                    print(f"Realtime detection error: {exc}")
            if self.output and self.out_queue:
                self.out_queue.put(frame)
            pixmap = frame_to_pixmap(frame)
            if pixmap is None:
                continue
            height, width = frame.shape[:2]
            resize = (self.w != width or self.h != height)
            self.update_pixmap.emit(pixmap, resize)
            self.w, self.h = width, height

    def clear_frame_queue(self):
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except Empty:
                break
