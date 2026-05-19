import os
import torch
import pyvista as pv
from copy import deepcopy
from collections import deque
import matplotlib.colors as mcolors
from PyQt5 import QtWidgets, QtCore, QtGui
from ultralytics.engine.results import Boxes, Masks, Keypoints, OBB
from UI.control.config import JSON
from UI.viewer.viewerImage import ImageViewer
from UI.control.config import IconSize
from UI.tools.tool_plot_yolo import *
from UI.tools.utils import print_gpu_memory_usage
from UI.control.config import *


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
        # Setup toolbar for image operations
        if hasattr(self, 'images_viewer_toolbar') and self.images_viewer_toolbar:
            return

        # Create toolbar
        self.images_viewer_toolbar = QtWidgets.QToolBar("Images Viewer Tools", self.parent)
        self.images_viewer_toolbar.setFont(QtGui.QFont("Times New Roman", 12))
        self.images_viewer_toolbar.setIconSize(QtCore.QSize(IconSize, IconSize))
        self.images_viewer_toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.images_viewer_toolbar.setObjectName("imagesViewerToolBar")

        # Add to main window
        self.parent.addToolBar(QtCore.Qt.TopToolBarArea, self.images_viewer_toolbar)
        self.images_viewer_toolbar.hide()

        # Create actions
        self.action_batch_detect = QtWidgets.QAction(self.parent)
        self.action_batch_detect.setIcon(QtGui.QIcon("UI/icons/ico/DetectionBatch.ico"))
        self.action_batch_detect.setText("Batch Detect")
        self.action_batch_detect.setToolTip("Detect all images with one click")

        self.action_3d_view = QtWidgets.QAction(self.parent)
        self.action_3d_view.setIcon(QtGui.QIcon("UI/icons/ico/Tools3D.ico"))
        self.action_3d_view.setText("3D View")
        self.action_3d_view.setCheckable(True)
        self.action_3d_view.setToolTip("Show 3D view")

        self.action_reset_view = QtWidgets.QAction(self.parent)
        self.action_reset_view.setIcon(QtGui.QIcon("UI/icons/ico/Reset.ico"))
        self.action_reset_view.setText("Reset View")
        self.action_reset_view.setToolTip("Reset")

        self.action_save_view = QtWidgets.QAction(self.parent)
        self.action_save_view.setIcon(QtGui.QIcon("UI/icons/ico/SaveIMG.ico"))
        self.action_save_view.setText("Save View")
        self.action_save_view.setToolTip("Save current view")

        # Create save menu
        self.save_menu = QtWidgets.QMenu(self.parent)

        self.action_save_image = QtWidgets.QAction("Save as Image", self.parent)
        self.action_save_image.setCheckable(True)
        self.action_save_txt = QtWidgets.QAction("Save as TXT", self.parent)
        self.action_save_txt.setCheckable(True)
        self.action_save_json = QtWidgets.QAction("Save as JSON", self.parent)
        self.action_save_json.setCheckable(True)
        self.action_save_mask = QtWidgets.QAction("Save Mask", self.parent)
        self.action_save_mask.setCheckable(True)

        self.action_save_image.setChecked(True)

        self.action_auto_save = QtWidgets.QAction("Auto Save", self.parent)
        self.action_auto_save.setCheckable(True)
        self.action_save_all = QtWidgets.QAction("Save All", self.parent)

        # Add actions to menu
        self.save_menu.addAction(self.action_save_txt)
        self.save_menu.addAction(self.action_save_json)
        self.save_menu.addAction(self.action_save_mask)
        self.save_menu.addAction(self.action_save_image)
        self.save_menu.addAction(self.action_auto_save)
        self.save_menu.addSeparator()
        self.save_menu.addAction(self.action_save_all)

        # Add set save path action
        self.action_set_save_path = QtWidgets.QAction("Set Save Path", self.parent)
        self.save_menu.addSeparator()
        self.save_menu.addAction(self.action_set_save_path)

        # Connect menu to action
        self.action_save_view.setMenu(self.save_menu)

        # Add actions to toolbar
        self.images_viewer_toolbar.addAction(self.action_batch_detect)
        self.images_viewer_toolbar.addAction(self.action_reset_view)
        self.images_viewer_toolbar.addAction(self.action_save_view)
        self.images_viewer_toolbar.addSeparator()
        self.images_viewer_toolbar.addAction(self.action_3d_view)

        # Connect signals
        self.action_batch_detect.triggered.connect(lambda checked: self.process_all_images(checked, False))
        self.action_3d_view.triggered.connect(self.toggle_3d_view)
        self.action_reset_view.triggered.connect(self.reset_cache)
        self.action_set_save_path.triggered.connect(self._set_save_path)
        self.action_save_view.triggered.connect(self._save_with_current_format)
        self.action_save_image.triggered.connect(lambda checked: self._on_save_format_changed("image", checked))
        self.action_save_txt.triggered.connect(lambda checked: self._on_save_format_changed("txt", checked))
        self.action_save_json.triggered.connect(lambda checked: self._on_save_format_changed("json", checked))
        self.action_save_mask.triggered.connect(lambda checked: self._on_save_format_changed("mask", checked))
        self.action_auto_save.triggered.connect(self._on_auto_save_toggled)
        self.action_save_all.triggered.connect(lambda checked: self.process_all_images(checked, True))

        def set_save_button_popup_mode():
            save_button = self.images_viewer_toolbar.widgetForAction(self.action_save_view)
            if save_button:
                save_button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
                self.save_menu.setToolTipsVisible(True)

        self.images_viewer_toolbar.visibilityChanged.connect(lambda: set_save_button_popup_mode())

    def _set_save_path(self):
        # Set default save directory
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            self.parent,
            "Select Default Save Path",
            self.default_save_path or "./'output'"
        )

        if folder_path:
            self.default_save_path = folder_path
            self.parent.statusbar.showMessage(f"Default save path set to: {folder_path}", 3000)

    def _get_save_path(self, file_name):
        # Get full save path
        if self.default_save_path:
            return os.path.join(self.default_save_path, file_name)
        else:
            self.default_save_path = "./output"
            return os.path.join(self.default_save_path, file_name)

    def _on_auto_save_toggled(self, checked):
        # Toggle auto save feature
        if checked:
            self.auto_save = True
            self.parent.statusbar.showMessage("Auto save enabled", 2000)
        else:
            self.auto_save = False
            self.parent.statusbar.showMessage("Auto save disabled", 2000)

    def process_all_images(self, checked, save=False):
        # Process all images with optional saving
        try:
            save_type = "image"

            # Determine save format
            if self.action_save_txt.isChecked():
                save_type = "txt"
            elif self.action_save_json.isChecked():
                save_type = "json"
            elif self.action_save_mask.isChecked():
                save_type = "mask"

            yolo_params = self.parent.yolo_dock.get_parameters()
            task_type = yolo_params['task']

            total_files = len(self.parent.files_dock.file_paths)
            if total_files == 0:
                self.parent.statusbar.showMessage("No files to save", 2000)
                return
            ret = self.parent.load_model()
            if not ret:
                return
            os.makedirs(self._get_save_path(""), exist_ok=True)

            # Create progress dialog
            progress_dialog = QtWidgets.QProgressDialog("Saving all files...", "Cancel", 0, total_files, self.parent)
            progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
            progress_dialog.setWindowTitle("Save All Files")
            progress_dialog.show()

            count, count_saved = 0, 0
            for i, file_path in enumerate(self.parent.files_dock.file_paths):
                if progress_dialog.wasCanceled():
                    break

                progress_dialog.setValue(i)
                progress_dialog.setLabelText(f"Processing: {os.path.basename(file_path)}")

                QtWidgets.QApplication.processEvents()
                if file_path not in self.yolo_results and (save_type != "image" or not save):
                    img = self.image_cache[file_path] if file_path in self.image_cache else cv2.imread(file_path,
                                                                                                       cv2.IMREAD_COLOR)
                    if img is not None:
                        yolo_params = self.parent.yolo_dock.get_parameters()
                        results = self.parent.yolo_model(
                            img,
                            conf=yolo_params["conf_threshold"],
                            iou=yolo_params["iou_threshold"],
                            retina_masks=True,
                        )
                    else:
                        continue

                    if len(results) > 0:
                        results_label = self.result_to_label(results[0])
                        self.yolo_results[file_path] = results_label

                        ret = print_gpu_memory_usage(ret=True)
                        self.parent.statusbar.showMessage(ret, 2000)
                        del results
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    count += 1
                if save:
                    if self.save_results_label(file_path, save_type, task_type):
                        count_saved += 1

            progress_dialog.setValue(total_files)
            progress_dialog.close()
            self.load_image()
            self.parent.statusbar.showMessage(f"Processed {count} images (save {count_saved})", 3000)
        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.close()
            self.parent.statusbar.showMessage(f"Save failed: {str(e)}", 3000)

    def save_results_label(self, file_path, save_type, task_type):
        # Save results in specified format
        if save_type == "image":
            format_type = "png"
        elif save_type == "mask":
            format_type = "png"
        elif save_type == "txt":
            format_type = "txt"
        elif save_type == "json":
            format_type = "json"
        else:
            format_type = "png"
        ext = "." + format_type
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        save_path = self._get_save_path(f"{base_name}{ext}")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        if save_type in {"mask", "txt", "json"}:
            selected_classes = self.parent.yolo_dock.get_selected_classes() if self.parent.annos_dock.show_filtered else None
            results_label = deepcopy(self.yolo_results[file_path])
            results_label = self.parent.plotter.filter_results_label(results_label, classes_names=selected_classes)
            if task_type != "segment":
                results_label['masks'] = []
            if task_type != "obb":
                results_label['obb'] = []
            if task_type != "pose":
                results_label['keypoints'] = []
            if format_type == "txt":
                return self._export_labels_to_txt(results_label, save_path), save_path
            elif format_type == "json":
                if JSON == "coco":
                    return self._export_labels_to_json(results_label, save_path, "coco"), save_path
                else:
                    return self._export_labels_to_json(results_label, save_path, "labelme"), save_path
            else:
                return self._export_mask(results_label, save_path), save_path
        else:
            return self._save_image(file_path, save_path), save_path

    def _on_save_format_changed(self, format_type, checked):
        # Handle save format change
        if checked:
            if format_type != "image":
                self.action_save_image.setChecked(False)
            if format_type != "txt":
                self.action_save_txt.setChecked(False)
            if format_type != "json":
                self.action_save_json.setChecked(False)
            if format_type != "mask":
                self.action_save_mask.setChecked(False)

            format_names = {"image": "Image", "txt": "TXT", "json": "JSON", "mask": "Mask"}
            self.action_save_view.setToolTip(
                f"Save current results as {format_names.get(format_type, format_type)}")
        return False

    def _save_with_current_format(self):
        # Save current image with selected format
        current_item = self.parent.files_dock.list_widget.currentItem()
        if not current_item:
            self.parent.statusbar.showMessage("No image selected", 2000)
            return

        file_path = current_item.data(QtCore.Qt.UserRole)
        if file_path not in self.yolo_results:
            self.parent.statusbar.showMessage("No YOLO results for current image", 2000)
            return
        save_type = "image"

        if self.action_save_txt.isChecked():
            save_type = "txt"
        elif self.action_save_json.isChecked():
            save_type = "json"
        elif self.action_save_mask.isChecked():
            save_type = "mask"

        yolo_params = self.parent.yolo_dock.get_parameters()
        task_type = yolo_params['task']
        ret, save_path = self.save_results_label(file_path, save_type, task_type)
        if ret:
            self.parent.statusbar.showMessage(f"File({save_type}) saved to: {save_path}", 3000)
        else:
            self.parent.statusbar.showMessage("Save failed", 3000)

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
        # Toggle 3D view
        if checked:
            self.parent.control3D_dock.show()
            self.parent.control3D_dock.show_toolbar()
        else:
            self.parent.control3D_dock.hide()
            self.parent.control3D_dock.hide_toolbar()
            self.parent.statusbar.showMessage("3D mode closed", 2000)

    def show_3d(self):
        # Show 3D visualization
        if not self.parent.files_dock.file_paths:
            self.parent.statusbar.showMessage("No images to display", 2000)
            if hasattr(self.parent, 'control3D_dock'):
                self.parent.control3D_dock.action_3d_view.setChecked(False)
            return

        try:
            image_stack = []
            total_files = len(self.parent.files_dock.file_paths)

            progress_dialog = QtWidgets.QProgressDialog("Preparing 3D data...", "Cancel", 0, total_files, self.parent)
            progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
            progress_dialog.setWindowTitle("3D View Preparation")
            progress_dialog.show()

            for i, file_path in enumerate(self.parent.files_dock.file_paths):
                progress_dialog.setValue(i)
                progress_dialog.setLabelText(f"Loading: {os.path.basename(file_path)}")

                QtWidgets.QApplication.processEvents()

                if progress_dialog.wasCanceled():
                    progress_dialog.close()
                    self.parent.statusbar.showMessage("3D view display canceled", 2000)
                    if hasattr(self.parent, 'control3D_dock'):
                        self.parent.control3D_dock.action_3d_view.setChecked(False)
                    return
                else:
                    if file_path in self.image_cache:
                        img = self.image_cache[file_path]
                        if len(img.shape) == 3:
                            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        else:
                            gray_img = img
                        image_stack.append(gray_img)
                    else:
                        img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            image_stack.append(img)

            progress_dialog.setValue(total_files)
            progress_dialog.close()

            if not image_stack:
                self.parent.statusbar.showMessage("Failed to load image data for 3D display", 3000)
                if hasattr(self.parent, 'control3D_dock'):
                    self.parent.control3D_dock.action_3d_view.setChecked(False)
                return
            self.parent.statusbar.showMessage(f"3D view displayed ({len(image_stack)} slices)", 3000)

            volume = np.stack(image_stack, axis=0)
            grid = pv.wrap(volume)

            colormap = self.parent.control3D_dock.colormap_combo.currentData()
            self.plotter_3d = pv.Plotter()
            if self.parent.control3D_dock.binary_checkbox.isChecked():
                color_value = self.parent.control3D_dock.color_slider.value()
                hue = color_value / 255.0
                saturation = 1.0
                value = 1.0
                hsv_color = np.array([[hue, saturation, value]])
                rgb_color = mcolors.hsv_to_rgb(hsv_color)[0]
                custom_cmap = mcolors.ListedColormap([rgb_color])
                self.plotter_3d.add_volume(grid, cmap=custom_cmap, opacity="linear")
            else:
                self.plotter_3d.add_volume(grid, cmap=colormap, opacity="linear")
            # self.plotter_3d.add_axes()
            # self.plotter_3d.show_grid()
            self.plotter_3d._before_close_callback = self.on_3d_window_close
            self.plotter_3d.show(title="3D Image Stack View", auto_close=True)

        except ImportError as e:
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Missing Dependencies",
                f"The following libraries are required to use 3D view functionality:\npyvista, scikit-image, matplotlib\n\nError: {str(e)}"
            )
            self.parent.statusbar.showMessage("Missing 3D visualization dependencies", 3000)
            if hasattr(self.parent, 'control3D_dock'):
                self.parent.control3D_dock.action_3d_view.setChecked(False)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.parent,
                "3D View Error",
                f"Error occurred while displaying 3D view:\n{str(e)}"
            )
            self.parent.statusbar.showMessage("3D view display failed", 3000)
            if hasattr(self.parent, 'control3D_dock'):
                self.parent.control3D_dock.action_3d_view.setChecked(False)

    def refresh_3d_view(self, colormap="viridis"):
        # Refresh 3D view with new colormap
        images_viewer = self.parent.tab_widget.currentWidget()

        if images_viewer.plotter_3d is not None:
            try:
                images_viewer.plotter_3d.close()
            except:
                pass
            images_viewer.plotter_3d = None

        if not self.parent.files_dock.file_paths:
            self.parent.statusbar.showMessage("No images to display", 2000)
            return

        try:
            image_stack = []
            for file_path in self.parent.files_dock.file_paths:
                if file_path in images_viewer.image_cache:
                    img = images_viewer.image_cache[file_path]
                    if len(img.shape) == 3:
                        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    else:
                        gray_img = img
                    image_stack.append(gray_img)
                else:
                    img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        image_stack.append(img)

            if not image_stack:
                self.parent.statusbar.showMessage("Failed to load image data for 3D display", 3000)
                return

            volume = np.stack(image_stack, axis=0)
            grid = pv.wrap(volume)

            images_viewer.plotter_3d = pv.Plotter()
            images_viewer.plotter_3d.add_volume(grid, cmap=colormap, opacity="linear")
            # self.plotter_3d.add_axes()
            # self.plotter_3d.show_grid()
            images_viewer.plotter_3d._before_close_callback = images_viewer.on_3d_window_close

            images_viewer.plotter_3d.show(title="3D Image Stack View", auto_close=True)

            self.parent.statusbar.showMessage(f"3D view refreshed with {colormap} colormap", 3000)

        except ImportError as e:
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Missing Dependencies",
                f"The following libraries are required to use 3D view functionality:\npyvista, scikit-image, matplotlib\n\nError: {str(e)}"
            )
            self.parent.statusbar.showMessage("Missing 3D visualization dependencies", 3000)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.parent,
                "3D View Error",
                f"Error occurred while displaying 3D view:\n{str(e)}"
            )
            self.parent.statusbar.showMessage("3D view display failed", 3000)

    def hide_3d(self):
        # Hide 3D view
        if self.plotter_3d is not None:
            try:
                self.plotter_3d.close()
            except:
                pass
            self.plotter_3d = None
            self.parent.statusbar.showMessage("3D view closed", 2000)

    def on_3d_window_close(self):
        # Handle 3D window close
        self.plotter_3d = None
        if hasattr(self.parent, 'control3D_dock'):
            self.parent.control3D_dock.action_3d_view.setChecked(False)
        self.parent.statusbar.showMessage("3D view closed", 2000)

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
        shape = results_label.get('shape', None)
        height, width = shape[:2]
        mask_img = np.zeros((height, width, 3), dtype=np.uint8)

        if len(results_label) > 0:
            if hasattr(self.parent, 'plotter'):
                black_background = np.zeros((height, width, 3), dtype=np.uint8)
                mask_img = self.parent.plotter.process_mini(black_background, results_label,
                                                            show_boxes=self.parent.annos_dock.show_boxes,
                                                            show_conf=self.parent.annos_dock.show_confidence,
                                                            show_labels=self.parent.annos_dock.show_labels)
        return mask_img

    def _export_results(self, results, save_path, format_type):
        # Export results to specified format
        try:
            results = results[0]

            if format_type == "txt":
                if os.path.exists(save_path):
                    os.remove(save_path)
                results.save_txt(save_path)
            elif format_type == "json":
                self.parent.statusbar.showMessage("Failed to save json labels", 3000)
                return False
            return True
        except Exception as e:
            print(f"Error exporting labels: {str(e)}")
            return False

    def _export_labels_to_txt(self, results_label, save_path):
        # Export labels to YOLO format txt file
        try:
            yolo_params = self.parent.yolo_dock.get_parameters()
            task_type = yolo_params["task"]
            if os.path.exists(save_path):
                os.remove(save_path)

            shape = results_label.get("shape")
            if not shape:
                self.parent.statusbar.showMessage("Image shape information missing", 3000)
                return False

            height, width = shape

            with open(save_path, 'w') as f:
                if task_type == "detect":
                    boxes_data = results_label.get("boxes", [])
                    for box in boxes_data:
                        if len(box) >= 6:
                            class_id = int(box[5])
                            x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
                            center_x = ((x1 + x2) / 2) / width
                            center_y = ((y1 + y2) / 2) / height
                            box_width = (x2 - x1) / width
                            box_height = (y2 - y1) / height

                            f.write(f"{class_id} {center_x:.6f} {center_y:.6f} {box_width:.6f} {box_height:.6f}\n")

                elif task_type == "segment":
                    masks_data = results_label.get("masks", [])
                    for mask in masks_data:
                        if len(mask) >= 3:
                            class_id = int(mask[0])
                            points = mask[1:]
                            line = str(class_id)
                            for i in range(0, len(points), 2):
                                x_norm = points[i] / width
                                y_norm = points[i + 1] / height
                                line += f" {x_norm:.6f} {y_norm:.6f}"
                            f.write(line + "\n")

                elif task_type == "pose":
                    keypoints_data = results_label.get("keypoints", [])
                    for kps in keypoints_data:
                        for kp in kps:
                            if len(kp) >= 3:
                                x_norm = kp[0] / width
                                y_norm = kp[1] / height
                                conf = kp[2]
                                f.write(f"{x_norm:.6f} {y_norm:.6f} {conf:.6f} ")
                        f.write("\n")

                elif task_type == "obb":
                    obb_data = results_label.get("obb", [])
                    for obb in obb_data:
                        if len(obb) >= 9:
                            class_id = int(obb[0])
                            points = obb[1:]
                            line = str(class_id)
                            for i in range(0, len(points), 2):
                                x_norm = points[i] / width
                                y_norm = points[i + 1] / height
                                line += f" {x_norm:.6f} {y_norm:.6f}"
                            f.write(line + "\n")

            return True
        except Exception as e:
            print(f"Error exporting labels to txt: {str(e)}")
            return False

    def _export_labels_to_json(self, results_label, save_path, json_format="labelme"):
        # Export labels to JSON format
        try:
            import json
            yolo_params = self.parent.yolo_dock.get_parameters()
            task_type = yolo_params["task"]
            if json_format.lower() == "labelme":
                json_data = self._convert_to_labelme_format(results_label, task_type)
            elif json_format.lower() == "coco":
                json_data = self._convert_to_coco_format(results_label, task_type)
            else:
                self.parent.statusbar.showMessage(f"Unsupported JSON format: {json_format}", 3000)
                return False

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"Error exporting labels to JSON: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _convert_to_labelme_format(self, results_label, task_type):
        # Convert to LabelMe JSON format
        try:
            file_path = results_label.get("file_path", "")
            shape = results_label.get("shape", [])
            height, width = shape if len(shape) >= 2 else (0, 0)

            labelme_data = {
                "version": "5.1.1",
                "flags": {},
                "shapes": [],
                "imagePath": os.path.basename(file_path) if file_path else "",
                "imageData": None,
                "imageHeight": height,
                "imageWidth": width
            }

            names = results_label.get("names", {})

            if task_type == "detect":
                boxes_data = results_label.get("boxes", [])
                for i, box in enumerate(boxes_data):
                    if len(box) >= 6:
                        class_id = int(box[5])
                        class_name = names.get(class_id, f"class_{class_id}")

                        x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
                        shape_data = {
                            "label": class_name,
                            "points": [[x1, y1], [x2, y2]],
                            "group_id": None,
                            "shape_type": "rectangle",
                            "flags": {}
                        }
                        labelme_data["shapes"].append(shape_data)

            elif task_type == "segment":
                masks_data = results_label.get("masks", [])
                for i, mask in enumerate(masks_data):
                    if len(mask) >= 3:
                        class_id = int(mask[0])
                        class_name = names.get(class_id, f"class_{class_id}")
                        points = mask[1:]

                        polygon_points = []
                        for j in range(0, len(points), 2):
                            if j + 1 < len(points):
                                polygon_points.append([float(points[j]), float(points[j + 1])])

                        if len(polygon_points) >= 3:
                            shape_data = {
                                "label": class_name,
                                "points": polygon_points,
                                "group_id": None,
                                "shape_type": "polygon",
                                "flags": {}
                            }
                            labelme_data["shapes"].append(shape_data)

            elif task_type == "pose":
                keypoints_data = results_label.get("keypoints", [])
                for i, kps in enumerate(keypoints_data):
                    for j, kp in enumerate(kps):
                        if len(kp) >= 3:
                            x, y, conf = float(kp[0]), float(kp[1]), float(kp[2])
                            if conf > 0:
                                class_name = f"keypoint_{j}"
                                shape_data = {
                                    "label": class_name,
                                    "points": [[x, y]],
                                    "group_id": None,
                                    "shape_type": "point",
                                    "flags": {}
                                }
                                labelme_data["shapes"].append(shape_data)

            elif task_type == "obb":
                obb_data = results_label.get("obb", [])
                for i, obb in enumerate(obb_data):
                    if len(obb) >= 9:
                        class_id = int(obb[0])
                        class_name = names.get(class_id, f"class_{class_id}")
                        points = obb[1:]

                        polygon_points = []
                        for j in range(0, len(points), 2):
                            if j + 1 < len(points):
                                polygon_points.append([float(points[j]), float(points[j + 1])])

                        if len(polygon_points) >= 3:
                            shape_data = {
                                "label": class_name,
                                "points": polygon_points,
                                "group_id": None,
                                "shape_type": "polygon",
                                "flags": {}
                            }
                            labelme_data["shapes"].append(shape_data)

            return labelme_data
        except Exception as e:
            print(f"Error converting to LabelMe format: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "version": "5.1.1",
                "flags": {},
                "shapes": [],
                "imagePath": "",
                "imageData": None,
                "imageHeight": 0,
                "imageWidth": 0
            }

    def _convert_to_coco_format(self, results_label, task_type):
        # Convert to COCO JSON format
        try:
            file_path = results_label.get("file_path", "")
            shape = results_label.get("shape", [])
            height, width = shape if len(shape) >= 2 else (0, 0)

            coco_data = {
                "info": {
                    "description": "Exported from Quant3D",
                    "version": "1.0",
                    "year": 2024,
                    "contributor": "Quant3D",
                    "date_created": QtCore.QDateTime.currentDateTime().toString("yyyy/MM/dd")
                },
                "licenses": [{
                    "id": 1,
                    "name": "Unknown",
                    "url": ""
                }],
                "images": [{
                    "id": 1,
                    "width": width,
                    "height": height,
                    "file_name": os.path.basename(file_path) if file_path else "",
                    "license": 1,
                    "flickr_url": "",
                    "coco_url": "",
                    "date_captured": QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
                }],
                "annotations": [],
                "categories": []
            }

            names = results_label.get("names", {})

            category_map = {}
            for class_id, class_name in names.items():
                category_id = len(coco_data["categories"]) + 1
                category_map[class_id] = category_id
                coco_data["categories"].append({
                    "id": category_id,
                    "name": class_name,
                    "supercategory": "object"
                })

            if not names:
                unique_class_ids = set()

                if task_type == "detect":
                    boxes_data = results_label.get("boxes", [])
                    for box in boxes_data:
                        if len(box) >= 6:
                            unique_class_ids.add(int(box[5]))
                elif task_type == "segment":
                    masks_data = results_label.get("masks", [])
                    for mask in masks_data:
                        if len(mask) >= 1:
                            unique_class_ids.add(int(mask[0]))
                elif task_type == "obb":
                    obb_data = results_label.get("obb", [])
                    for obb in obb_data:
                        if len(obb) >= 1:
                            unique_class_ids.add(int(obb[0]))

                for class_id in unique_class_ids:
                    category_id = len(coco_data["categories"]) + 1
                    category_map[class_id] = category_id
                    coco_data["categories"].append({
                        "id": category_id,
                        "name": f"class_{class_id}",
                        "supercategory": "object"
                    })

            annotation_id = 1

            if task_type == "detect":
                boxes_data = results_label.get("boxes", [])
                for i, box in enumerate(boxes_data):
                    if len(box) >= 6:
                        class_id = int(box[5])
                        category_id = category_map.get(class_id, class_id)

                        x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
                        width_bbox = x2 - x1
                        height_bbox = y2 - y1
                        area = width_bbox * height_bbox
                        confidence = float(box[4]) if len(box) > 4 else 1.0

                        annotation = {
                            "id": annotation_id,
                            "image_id": 1,
                            "category_id": category_id,
                            "bbox": [x1, y1, width_bbox, height_bbox],
                            "area": area,
                            "iscrowd": 0,
                            "confidence": confidence
                        }
                        coco_data["annotations"].append(annotation)
                        annotation_id += 1

            elif task_type == "segment":
                masks_data = results_label.get("masks", [])
                for i, mask in enumerate(masks_data):
                    if len(mask) >= 3:
                        class_id = int(mask[0])
                        category_id = category_map.get(class_id, class_id)
                        points = mask[1:]

                        x_coords = [float(points[j]) for j in range(0, len(points), 2)]
                        y_coords = [float(points[j]) for j in range(1, len(points), 2)]
                        x_min, x_max = min(x_coords), max(x_coords)
                        y_min, y_max = min(y_coords), max(y_coords)
                        width_bbox = x_max - x_min
                        height_bbox = y_max - y_min
                        area = width_bbox * height_bbox

                        segmentation = []
                        seg_points = []
                        for j in range(0, len(points), 2):
                            if j + 1 < len(points):
                                seg_points.extend([float(points[j]), float(points[j + 1])])
                        segmentation.append(seg_points)

                        annotation = {
                            "id": annotation_id,
                            "image_id": 1,
                            "category_id": category_id,
                            "bbox": [x_min, y_min, width_bbox, height_bbox],
                            "segmentation": segmentation,
                            "area": area,
                            "iscrowd": 0
                        }
                        coco_data["annotations"].append(annotation)
                        annotation_id += 1

            elif task_type == "obb":
                obb_data = results_label.get("obb", [])
                for i, obb in enumerate(obb_data):
                    if len(obb) >= 9:
                        class_id = int(obb[0])
                        category_id = category_map.get(class_id, class_id)
                        points = obb[1:]

                        x_coords = [float(points[j]) for j in range(0, len(points), 2)]
                        y_coords = [float(points[j]) for j in range(1, len(points), 2)]
                        x_min, x_max = min(x_coords), max(x_coords)
                        y_min, y_max = min(y_coords), max(y_coords)
                        width_bbox = x_max - x_min
                        height_bbox = y_max - y_min
                        area = width_bbox * height_bbox

                        segmentation = []
                        seg_points = []
                        for j in range(0, len(points), 2):
                            if j + 1 < len(points):
                                seg_points.extend([float(points[j]), float(points[j + 1])])
                        segmentation.append(seg_points)

                        annotation = {
                            "id": annotation_id,
                            "image_id": 1,
                            "category_id": category_id,
                            "bbox": [x_min, y_min, width_bbox, height_bbox],
                            "segmentation": segmentation,
                            "area": area,
                            "iscrowd": 0
                        }
                        coco_data["annotations"].append(annotation)
                        annotation_id += 1

            return coco_data
        except Exception as e:
            print(f"Error converting to COCO format: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "info": {
                    "description": "Exported from Quant3D",
                    "version": "1.0",
                    "year": 2024,
                    "contributor": "Quant3D",
                    "date_created": QtCore.QDateTime.currentDateTime().toString("yyyy/MM/dd")
                },
                "licenses": [{
                    "id": 1,
                    "name": "Unknown",
                    "url": ""
                }],
                "images": [],
                "annotations": [],
                "categories": []
            }

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

    def update_cache_settings(self, max_size=10):
        # Update cache settings
        self.max_cache_size = max_size
        self.image_data_cache = deque(self.image_data_cache, maxlen=max_size)

    def batch_detect(self):
        # Run batch detection on all images
        if not self.parent.files_dock.file_paths:
            self.parent.statusbar.showMessage("No images to detect", 2000)
            return

        yolo_params = self.parent.yolo_dock.get_parameters()

        progress_dialog = QtWidgets.QProgressDialog("Performing batch detection...", "Cancel", 0,
                                                    len(self.parent.files_dock.file_paths),
                                                    self.parent)
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setWindowTitle("Batch Detection")
        progress_dialog.show()
        ret = self.parent.load_model()
        if not ret:
            return
        try:
            for i, file_path in enumerate(self.parent.files_dock.file_paths):
                if progress_dialog.wasCanceled():
                    break

                progress_dialog.setValue(i)
                progress_dialog.setLabelText(f"Detecting: {os.path.basename(file_path)}")

                QtWidgets.QApplication.processEvents()
                img = self.image_cache[file_path] if file_path in self.image_cache else cv2.imread(file_path,
                                                                                                   cv2.IMREAD_COLOR)

                if img is not None:
                    results = self.parent.yolo_model(
                        img,
                        conf=yolo_params["conf_threshold"],
                        iou=yolo_params["iou_threshold"],
                        retina_masks=True,
                    )
                    self.yolo_results[file_path] = self.result_to_label(results[0])

            progress_dialog.setValue(len(self.parent.files_dock.file_paths))
            self.parent.statusbar.showMessage(f"Batch detection completed, processed {len(self.yolo_results)} images",
                                              3000)
            self.load_image()

        except Exception as e:
            self.parent.statusbar.showMessage(f"Batch detection error: {str(e)}", 5000)
            import traceback
            traceback.print_exc()

    def move_results_to_cpu(self, results, file_path):
        # Move tensor data to CPU
        new_result = results[0].__class__(
            orig_img=results[0].orig_img,
            path=results[0].path,
            names=results[0].names
        )
        if isinstance(results, list) and len(results) > 0:
            results = results[0]

        if hasattr(results, 'boxes') and results.boxes is not None:
            if isinstance(results.boxes, Boxes):
                new_result.boxes = Boxes(
                    boxes=results.boxes.data.cpu(),
                    orig_shape=results.boxes.orig_shape
                )

        if hasattr(results, 'masks') and results.masks is not None:
            if isinstance(results.masks, Masks):
                new_result.masks = Masks(
                    masks=results.masks.data.cpu(),
                    orig_shape=results.masks.orig_shape
                )

        if hasattr(results, 'keypoints') and results.keypoints is not None:
            if isinstance(results.keypoints, Keypoints):
                new_result.keypoints = Keypoints(
                    keypoints=results.keypoints.data.cpu(),
                    orig_shape=results.keypoints.orig_shape
                )

        if hasattr(results, 'obb') and results.obb is not None:
            if isinstance(results.obb, OBB):
                new_result.obb = OBB(
                    boxes=results.obb.data.cpu(),
                    orig_shape=results.obb.orig_shape
                )
        new_result.orig_img = self.image_cache[file_path]

        if hasattr(new_result, '__dict__'):
            for attr_name, attr_value in new_result.__dict__.items():
                if hasattr(attr_value, 'cpu'):
                    setattr(new_result, attr_name, attr_value.cpu())

        return [new_result]
