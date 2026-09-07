"""实时相机视图：预览、录像、实时检测与标定采集。"""

from multiprocessing import Queue
from queue import Queue as q_Queue

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt

from quant.ui.views import camera_stream, camera_recorder, camera_interaction


class CameraWindow(QtWidgets.QWidget):
    """Main camera window widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Reader process
        self.communication_timer = None
        self.capture = None
        self.camera_process = None
        self.parent_conn = None
        self.child_conn = None
        self.display_worker = None
        self.display_thread = None
        self.setWindowTitle("Real-time Camera Feed")
        self.parent = parent
        self.camera_index = 0  # Current camera index
        self.fps = None
        self.width = 1920
        self.height = 1080

        self.recording_start_time = None
        self.frame_count_record = 0
        self.frame_timer = None
        self.camera_available = None
        self.record_thread = None
        self.video_writer = None

        self.frame_queue = Queue(maxsize=30)  # Max length to prevent memory explosion
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

    def change_camera(self, camera_index):
        """
        Switch camera index
        """
        self.camera_index = camera_index
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
        event.accept()

    def update_fps(self):
        fps = self.frame_counter
        self.fps_label.setText(f"FPS: {fps}")
        self.frame_counter = 0  # Reset counter

    def check_pipe(self, conn):
        camera_stream.check_pipe(self, conn)

    def init_camera(self):
        camera_stream.init_camera(self)

    def start_camera(self, shortcut=False, mode='mono'):
        camera_stream.start_camera(self, shortcut, mode)

    def update_display(self, frame):
        camera_stream.update_display(self, frame)

    def stop_camera(self):
        camera_stream.stop_camera(self)

    def on_update_pixmap(self, pixmap, resize):
        camera_stream.on_update_pixmap(self, pixmap, resize)

    def close_camera(self):
        camera_stream.close_camera(self)

    def cleanup(self):
        camera_stream.cleanup(self)

    def start_snapshot(self):
        camera_recorder.start_snapshot(self)

    def start_recording(self):
        camera_recorder.start_recording(self)

    def clear_frame_queue(self):
        camera_recorder.clear_frame_queue(self)

    def stop_recording(self):
        camera_recorder.stop_recording(self)

    def update_recording_info(self):
        camera_recorder.update_recording_info(self)

    # ===== Mouse interaction methods =====
    def zoom_in(self):
        self.graphics_view.scale(1.1, 1.1)

    def zoom_out(self):
        self.graphics_view.scale(0.9, 0.9)

    def wheelEvent(self, event):
        camera_interaction.on_wheel(self, event)

    def mousePressEvent(self, event):
        camera_interaction.on_mouse_press(self, event)

    def mouseMoveEvent(self, event):
        camera_interaction.on_mouse_move(self, event)

    def mouseReleaseEvent(self, event):
        camera_interaction.on_mouse_release(self, event)

    def mouseDoubleClickEvent(self, event):
        camera_interaction.on_mouse_double_click(self, event)

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
        camera_interaction.reset_hide_timer(self)

    def hide_floating_button(self):
        camera_interaction.hide_floating_button(self)
