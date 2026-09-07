"""图像视图基类：场景/视图搭建、鼠标交互、标注与检测结果的重绘入口。"""

import os
import traceback

import cv2
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt

from quant.core.config import dx, dy, dz
from quant.core.qt_image import get_image_format_name
from quant.detection import result_codec
from quant.imaging.colorize import get_img_color
from quant.io import label_import


class Viewer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Image Viewer")
        self.resize(640, 480)
        self.dx, self.dy, self.dz = dx, dy, dz
        self.threshold = 0.5

        # Create QGraphicsView and QGraphicsScene
        self.graphics_view = QtWidgets.QGraphicsView(self)
        self.graphics_scene = QtWidgets.QGraphicsScene(self)
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setRenderHint(QtGui.QPainter.Antialiasing)

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.graphics_view)

        self.switch_display_btn = QtWidgets.QLabel("1", self.graphics_view)
        self.switch_display_btn.setStyleSheet("""
            font-size: 20px;
            color: grey;
            background-color: rgba(255, 255, 255, 180);
            border-radius: 10px;
            padding: 2px 6px;
        """)
        self.switch_display_btn.setCursor(Qt.PointingHandCursor)
        self.switch_display_btn.setAlignment(Qt.AlignCenter)
        self.switch_display_btn.mousePressEvent = self.on_switch_display_click
        self.switch_display_btn.hide()

        # Image container
        self.pixmap_item = None
        # self.mask = None
        self.img = None
        self.show_label = False
        self.show_results = False
        self.show_detect_results = False
        self.load_yolo_results = False
        self.show_yolo_point_results = False
        self.default_save_path = None
        self.mask_opacity = 0.5  # Mask opacity
        self.label_file_path = None

        # Point detection related properties
        self.point_detection_mode = False
        self.last_click_point = None
        self.image_cache = {}  # Cache loaded images
        self.label_cache = {}
        self.yolo_cache = {}

        # YOLO model related properties
        self.yolo_mode = 'detect'
        self.yolo_results = {}  # Store YOLO detection results

        # Mouse interaction variables
        self.mouse_pressed = False
        self.ctrl_pressed = False
        self.last_mouse_pos = None

        # Multi-image display control
        self.display_modes = [1, 2, 4, 8]
        self.current_mode_index = 0  # Default to 1 image
        self.pixmap_items = []  # Store multiple pixmap items

        # Properties for displaying detection area box
        self.patch_size = 320  # Default detection area size
        self.patch_rect_item = None  # Graphics item for displaying detection area box
        self.patch_hide_timer = None

        self.graphics_view.wheelEvent = self.wheelEvent
        self.graphics_view.mousePressEvent = self.mousePressEvent
        self.graphics_view.mouseMoveEvent = self.mouseMoveEvent
        self.graphics_view.mouseReleaseEvent = self.mouseReleaseEvent

    def on_context_menu(self, point):
        pass

    def update_patch_rect(self, patch_size_percent):
        """
        Update detection area box size (by image ratio)
        :param patch_size_percent: Detection area percentage of image size (10-100)
        """
        if not self.pixmap_item or not self.point_detection_mode:
            return

        pixmap = self.pixmap_item.pixmap()
        if pixmap.isNull():
            return

        img_width = pixmap.width()
        img_height = pixmap.height()

        patch_size = int(min(img_width, img_height) * patch_size_percent / 100)
        patch_size = min(patch_size, img_width, img_height)

        if self.patch_rect_item is None:
            self.patch_rect_item = QtWidgets.QGraphicsRectItem()
            self.patch_rect_item.setPen(QtGui.QPen(QtCore.Qt.red, 3, QtCore.Qt.DashLine))
            self.graphics_scene.addItem(self.patch_rect_item)

        x = (img_width - patch_size) / 2
        y = (img_height - patch_size) / 2

        self.patch_rect_item.setRect(x, y, patch_size, patch_size)
        self.patch_rect_item.setZValue(1000)
        self.patch_rect_item.show()

    def update_display_layout(self):
        if not self.pixmap_item:
            return
        pixmap = self.pixmap_item.pixmap()
        if pixmap.isNull():
            return

        width = pixmap.width()
        height = pixmap.height()

        # Clear all image items
        for item in self.pixmap_items:
            self.graphics_scene.removeItem(item)
        self.pixmap_items.clear()

        current_mode = self.display_modes[self.current_mode_index]
        cols = int(current_mode ** 0.5)
        rows = (current_mode + cols - 1) // cols

        # Add multiple pixmap items
        for i in range(current_mode):
            item = self.graphics_scene.addPixmap(pixmap)
            x = (i % cols) * width
            y = (i // cols) * height
            item.setPos(x, y)
            self.pixmap_items.append(item)

        # Update scene rect and fit to view
        new_rect = QtCore.QRectF(0, 0, cols * width, rows * height)
        self.graphics_scene.setSceneRect(new_rect)
        self.graphics_view.fitInView(new_rect, Qt.KeepAspectRatio)

    def update_image(self, img):
        """Update displayed image with point detection results"""
        if len(img.shape) == 2:  # Grayscale
            height, width = img.shape
            bytes_per_line = width
            q_image = QtGui.QImage(img.data, width, height, bytes_per_line, QtGui.QImage.Format_Grayscale8)
        else:  # Color image
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            height, width, channel = img.shape
            bytes_per_line = 3 * width
            q_image = QtGui.QImage(img.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888)

        fmt = get_image_format_name(q_image.format())
        pixmap = QtGui.QPixmap.fromImage(q_image)

        if self.pixmap_item is not None:
            self.graphics_scene.removeItem(self.pixmap_item)
        self.pixmap_item = self.graphics_scene.addPixmap(pixmap)
        self.graphics_scene.setSceneRect(QtCore.QRectF(pixmap.rect()))
        return fmt

    def load_aval_mask(self, img, mask, opacity):
        if mask.shape[:2] != img.shape[:2]:
            mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
        mask = get_img_color(mask, 3 + self.parent.plotter.offset)
        annotated_img = cv2.addWeighted(img, opacity, mask, 1 - opacity, 0)
        img[mask > 0] = annotated_img[mask > 0]
        # mask = np.squeeze(mask)
        # img[mask != 0] = 0
        return True, img

    def load_mask(self, img, file_path, reverse=False):
        if os.path.exists(file_path):
            mask = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
            if mask is None:
                return False, img
            if reverse:
                return self.load_aval_mask(img, ~mask, self.mask_opacity)
            else:
                return self.load_aval_mask(img, mask, self.mask_opacity)
        else:
            return False, img

    def load_label_file_txt(self, img, file_path):
        return label_import.load_label_file_txt(self, img, file_path)

    def load_label_file_json(self, img, file_path):
        return label_import.load_label_file_json(self, img, file_path)

    def load_label_file_xml(self, img, file_path):
        return label_import.load_label_file_xml(self, img, file_path)

    def show_annotations_with_results(self, img, yolo_labels):
        """
        Display various types of annotations using ultralytics Results and plot methods
        """
        try:
            selected_classes = self.parent.yolo_dock.get_selected_classes() if self.parent.annos_dock.show_filtered else None
            annotated_img = self.parent.plotter.process_mini(img, yolo_labels, selected_classes,
                                                             show_boxes=self.parent.annos_dock.show_boxes,
                                                             show_conf=self.parent.annos_dock.show_confidence,
                                                             show_labels=self.parent.annos_dock.show_labels)
            return annotated_img

        except Exception as e:
            print(f"Error displaying annotations with Results: {e}")
            traceback.print_exc()
            return img

    def result_to_label(self, results):
        return result_codec.result_to_label(self, results)

    def merge_results_label(self, file_path, new_label):
        result_codec.merge_results_label(self, file_path, new_label)

    def reset_results(self):
        """Clear image cache"""
        current_item = self.parent.files_dock.list_widget.currentItem()
        if not current_item:
            self.parent.statusbar.showMessage("No image selected", 2000)
            return
        file_path = current_item.data(QtCore.Qt.UserRole)
        if self.yolo_results:
            self.yolo_results.clear()
        if self.yolo_cache:
            self.yolo_cache.clear()
        self.parent.statusbar.showMessage("All inspection results reset", 2000)
        self.load_file(file_path)

    def reset_view(self):
        """Reset view and reset currently displayed image to image_cache"""
        current_item = self.parent.files_dock.list_widget.currentItem()
        if not current_item:
            self.parent.statusbar.showMessage("No image selected", 2000)
            return

        file_path = current_item.data(QtCore.Qt.UserRole)
        if file_path not in self.parent.files_dock.file_paths:
            self.parent.statusbar.showMessage("Current image not in image list", 2000)
            return

        try:
            if file_path in self.yolo_results:
                del self.yolo_results[file_path]
            if file_path in self.yolo_cache:
                del self.yolo_cache[file_path]
            self.parent.statusbar.showMessage(f"Detection results reset: {os.path.basename(file_path)}", 3000)
            self.load_file(file_path)
        except Exception as e:
            self.parent.statusbar.showMessage(f"Failed to reset image: {str(e)}", 3000)

    def on_switch_display_click(self, event):
        self.current_mode_index = (self.current_mode_index + 1) % len(self.display_modes)
        self.update_display_layout()
        event.accept()

    def hide_patch_rect(self):
        """
        Hide detection area box
        """
        if self.patch_rect_item:
            self.patch_rect_item.hide()
        if self.patch_hide_timer:
            self.patch_hide_timer.stop()

    # ===== mouse =====
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.pixmap_item:
            self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

        if self.switch_display_btn.isVisible():
            self.switch_display_btn.move(
                self.graphics_view.width() - self.switch_display_btn.width() - 10,
                10
            )

    def enterEvent(self, event):
        if self.switch_display_btn.isVisible():
            self.reset_hide_timer()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.reset_hide_timer()
        super().leaveEvent(event)

    def reset_hide_timer(self):
        """Reset button hide timer"""
        if hasattr(self, 'hide_timer'):
            self.hide_timer.stop()
        self.hide_timer = QtCore.QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_floating_button)
        self.hide_timer.start(2000)

    def hide_floating_button(self):
        """Hide display switch button"""
        self.switch_display_btn.hide()

    def zoom_in(self):
        self.graphics_view.scale(1.1, 1.1)

    def zoom_out(self):
        self.graphics_view.scale(0.9, 0.9)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.graphics_view.scale(1.1, 1.1)
            elif delta < 0:
                self.graphics_view.scale(0.9, 0.9)
            event.accept()
        elif self.parent.is_fixed_size:
            delta = event.angleDelta().y()
            current_mode = self.display_modes[self.current_mode_index]
            if delta > 0:
                self.parent.files_dock.prev_image(event, current_mode)
            elif delta < 0:
                self.parent.files_dock.next_image(event, current_mode)
            else:
                event.ignore()
            event.accept()
        else:
            delta = event.angleDelta().y()
            if delta > 0:
                self.graphics_view.scale(1.1, 1.1)
            elif delta < 0:
                self.graphics_view.scale(0.9, 0.9)
            event.accept()

    def mousePressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.button() == Qt.MouseButton.LeftButton:
            if self.point_detection_mode and self.pixmap_item:
                self.handle_point_detection(event, super=True)
            else:
                self.ctrl_pressed = True
        elif event.modifiers() == Qt.ControlModifier and event.button() == Qt.MouseButton.RightButton:
            if self.pixmap_item is not None:
                self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

        elif event.button() == Qt.MouseButton.RightButton and (self.show_label or self.show_results):
            self.on_context_menu(event.pos())
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.mouse_pressed = True
            self.last_mouse_pos = event.pos()
            self.graphics_view.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.point_detection_mode and self.pixmap_item:
                self.handle_point_detection(event)
            elif self.switch_display_btn.isVisible():
                self.reset_hide_timer()
            else:
                self.switch_display_btn.show()
                self.switch_display_btn.move(self.graphics_view.width() - self.switch_display_btn.width() - 10, 10)
        else:
            QtWidgets.QGraphicsView.mousePressEvent(self.graphics_view, event)

    def mouseMoveEvent(self, event):
        if self.pixmap_item and not self.mouse_pressed and self.ctrl_pressed:
            view_pos = event.pos()
            scene_pos = self.graphics_view.mapToScene(view_pos)
            pixmap_pos = self.pixmap_item.mapFromScene(scene_pos)

            x, y = int(pixmap_pos.x()), int(pixmap_pos.y())

            img = self.img[1] if self.img is not None else None
            if img is not None:
                img_h, img_w = img.shape[:2]
                if 0 <= x < img_w and 0 <= y < img_h:
                    if img.ndim == 2:
                        pixel_value = img[y, x]
                        self.parent.statusbar.showMessage(f"Position: ({x}, {y})  V: {pixel_value}", 1000)
                    else:
                        b, g, r = img[y, x]
                        self.parent.statusbar.showMessage(f"Position: ({x}, {y}) V: R={r}, G={g}, B={b}", 1000)
                else:
                    self.parent.statusbar.showMessage("", 1000)
        if self.mouse_pressed:
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            h_scroll = self.graphics_view.horizontalScrollBar()
            v_scroll = self.graphics_view.verticalScrollBar()
            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or event.button() == Qt.MouseButton.RightButton or event.button() == Qt.MouseButton.LeftButton:
            self.mouse_pressed = False
            self.graphics_view.setCursor(Qt.ArrowCursor)
            self.ctrl_pressed = False
        else:
            QtWidgets.QGraphicsView.mouseReleaseEvent(self.graphics_view, event)

    def cleanup(self):
        """Clean up resources occupied by ImageViewer"""
        if self.pixmap_item:
            self.graphics_scene.removeItem(self.pixmap_item)
            self.pixmap_item = None

        self.graphics_scene.clear()

        self.graphics_view.setScene(None)
        self.graphics_view = None
        self.graphics_scene = None

        self.label_file_path = None

        self.ctrl_pressed = False
        self.mouse_pressed = False
        self.last_mouse_pos = None
        self.parent.statusbar.showMessage(f"✅ ImageViewer resources released", 3000)
