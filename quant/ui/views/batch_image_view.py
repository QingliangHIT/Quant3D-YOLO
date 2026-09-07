"""批量图像视图：批处理检测、导出与三维体素视图入口。"""

import os

import cv2

from quant.analysis import volume_view
from quant.core.config import cache_image
from quant.io import label_export
from quant.ui.views.image_view import ImageViewer
from quant.ui.views import batch_toolbar, batch_actions


class ImagesViewer(ImageViewer):
    def __init__(self, parent=None):
        # Initialize viewer with parent widget
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Images Viewer")
        self.setup_toolbar()
        self.plotter_3d = None
        self.cache = cache_image

    def setup_toolbar(self):
        return batch_toolbar.build_toolbar(self)

    def _set_save_path(self):
        batch_toolbar.set_save_path(self)

    def _get_save_path(self, file_name):
        return batch_toolbar.get_save_path(self, file_name)

    def _on_auto_save_toggled(self, checked):
        batch_toolbar.on_auto_save_toggled(self, checked)

    def process_all_images(self, checked, save=False):
        return batch_actions.process_all_images(self, checked, save)

    def save_results_label(self, file_path, save_type, task_type):
        return batch_actions.save_results_label(self, file_path, save_type, task_type)

    def _on_save_format_changed(self, format_type, checked):
        return batch_toolbar.on_save_format_changed(self, format_type, checked)

    def _save_with_current_format(self):
        return batch_actions.save_with_current_format(self)

    def show_toolbar(self):
        # Show toolbar
        if hasattr(self, 'images_viewer_toolbar'):
            self.images_viewer_toolbar.show()

    def hide_toolbar(self):
        # Hide toolbar
        if hasattr(self, 'images_viewer_toolbar'):
            self.images_viewer_toolbar.hide()

    def load_images(self, file_paths):
        # Load images into cache
        if self.cache:
            for index, file_path in enumerate(file_paths):
                if file_path not in self.image_cache.keys():
                    self.image_cache[file_path] = cv2.imread(file_path, cv2.IMREAD_COLOR)
        if self.image_cache:
            self.load_file(file_paths[0])

    def toggle_3d_view(self, checked):
        volume_view.toggle_3d_view(self, checked)

    def show_3d(self):
        return volume_view.show_3d(self)

    def refresh_3d_view(self, colormap="viridis"):
        return volume_view.refresh_3d_view(self, colormap)

    def hide_3d(self):
        volume_view.hide_3d(self)

    def on_3d_window_close(self):
        volume_view.on_3d_window_close(self)

    def clear_cache(self):
        # Clear image cache
        self.image_cache.clear()
        self.parent.statusbar.showMessage("Image cache cleared", 2000)

    def _save_image(self, file_path, save_path):
        # Save image to file
        img = self.yolo_cache[file_path]['img'] if file_path in self.yolo_cache else cv2.imread(file_path)
        if img is not None:
            return cv2.imwrite(save_path, img)
        else:
            return False

    def _export_mask(self, results_label, save_path):
        # Export mask image
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        try:
            mask_img = self.results_to_mask(results_label)
            return cv2.imwrite(save_path, mask_img)
        except Exception as e:
            self.parent.statusbar.showMessage(f"Error saving mask: {str(e)}", 3000)
            return False

    def results_to_mask(self, results_label):
        return label_export.results_to_mask(self, results_label)

    def _export_labels_to_txt(self, results_label, save_path):
        return label_export.export_labels_to_txt(self, results_label, save_path)

    def _export_labels_to_json(self, results_label, save_path, json_format="labelme"):
        return label_export.export_labels_to_json(self, results_label, save_path, json_format)

    def _convert_to_labelme_format(self, results_label, task_type):
        return label_export.convert_to_labelme_format(self, results_label, task_type)

    def _convert_to_coco_format(self, results_label, task_type):
        return label_export.convert_to_coco_format(self, results_label, task_type)

    def reset_cache(self):
        # Reset image cache
        if self.parent.control3D_dock.all_process_checkbox.isChecked():
            self.image_cache.clear()
            self.image_cache = {file_path: cv2.imread(file_path, cv2.IMREAD_COLOR) for file_path in
                                self.parent.files_dock.file_paths}
            self.parent.statusbar.showMessage("Image cache reset", 2000)
        else:
            self.image_cache[self.img[0]] = cv2.imread(self.img[0], cv2.IMREAD_COLOR)
            self.parent.statusbar.showMessage(f"Reset cache: {self.img[0]}", 2000)
        if self.image_cache:
            self.load_file(self.parent.files_dock.file_paths[0])

    def batch_detect(self):
        return batch_actions.batch_detect(self)
