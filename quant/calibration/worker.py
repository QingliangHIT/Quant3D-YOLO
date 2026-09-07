"""后台标定线程：在 QThread 中执行相机标定并回报进度。"""

from PyQt5 import QtCore


class CalibratorWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(int)
    result_ready = QtCore.pyqtSignal(object)
    error_occurred = QtCore.pyqtSignal(str)

    def __init__(self, calibrator, parent=None):
        super().__init__(parent)
        self.calibrator = calibrator

    def run(self, camera_side='left'):
        try:
            # 执行耗时操作（单目标定）
            ret = self.calibrator.calibrate_single_camera(camera_side)
            self.report_progress(100)
            self.result_ready.emit(ret)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()

    def report_progress(self, value):
        self.progress.emit(value)
