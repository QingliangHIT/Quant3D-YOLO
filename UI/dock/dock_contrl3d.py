import os
import cv2
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from copy import deepcopy
from UI.control.config import IconSize


class Control3DDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__("3D Control", parent)
        self.all_process = True
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        """Set up UI interface"""
        self.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)

        # Create main widget and layout
        self.widget = QtWidgets.QWidget()
        self.setWidget(self.widget)
        self.layout = QtWidgets.QVBoxLayout(self.widget)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 10, 10, 10)

        # Mask control section
        self.control_group = QtWidgets.QGroupBox("Process Control")
        self.control_layout = QtWidgets.QVBoxLayout(self.control_group)
        self.control_bt_layout = QtWidgets.QHBoxLayout()

        # Process all switch
        self.all_process_checkbox = QtWidgets.QCheckBox("Process All")
        self.all_process_checkbox.setChecked(True)
        self.control_bt_layout.addWidget(self.all_process_checkbox)
        self.binary_checkbox = QtWidgets.QCheckBox("Binarization")
        self.binary_checkbox.setChecked(True)
        self.control_bt_layout.addWidget(self.binary_checkbox)
        self.control_layout.addLayout(self.control_bt_layout)

        # Threshold input field
        self.threshold_layout = QtWidgets.QHBoxLayout()
        self.threshold_label = QtWidgets.QLabel("Threshold:")
        self.color_layout = QtWidgets.QHBoxLayout()
        self.color_label = QtWidgets.QLabel("Color:")

        self.threshold_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(255)
        self.threshold_slider.setValue(128)
        self.threshold_slider.setToolTip("Adjust segmentation threshold")
        self.color_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.color_slider.setMinimum(0)
        self.color_slider.setMaximum(255)
        self.color_slider.setValue(128)
        self.color_slider.setToolTip("Adjust binarization color value")

        self.threshold_value_label = QtWidgets.QLabel("128")
        self.threshold_value_label.setMinimumWidth(40)
        self.threshold_value_label.setAlignment(QtCore.Qt.AlignCenter)
        self.color_value_label = QtWidgets.QLabel("128")
        self.color_value_label.setMinimumWidth(40)
        self.color_value_label.setAlignment(QtCore.Qt.AlignCenter)
        self.threshold_layout.addWidget(self.threshold_label, 2)
        self.threshold_layout.addWidget(self.threshold_slider, 4)
        self.threshold_layout.addWidget(self.threshold_value_label, 1)
        self.color_layout.addWidget(self.color_label, 2)
        self.color_layout.addWidget(self.color_slider, 4)
        self.color_layout.addWidget(self.color_value_label, 1)

        self.control_layout.addLayout(self.threshold_layout)

        # Colormap options
        self.colormap_layout = QtWidgets.QHBoxLayout()
        # Colormap selection
        self.colormap_layout_label = QtWidgets.QLabel("Colormap:")
        self.colormap_combo = QtWidgets.QComboBox()
        self.colormap_combo.addItem("Viridis", "viridis")
        self.colormap_combo.addItem("Plasma", "plasma")
        self.colormap_combo.addItem("Inferno", "inferno")
        self.colormap_combo.addItem("Magma", "magma")
        self.colormap_combo.addItem("Jet", "jet")
        self.colormap_combo.addItem("Hot", "hot")
        self.colormap_combo.addItem("Gray", "gray")
        self.colormap_combo.setCurrentText("Viridis")

        self.colormap_layout.addWidget(self.colormap_layout_label)
        self.colormap_layout.addWidget(self.colormap_combo)
        self.control_layout.addLayout(self.colormap_layout)
        self.control_layout.addLayout(self.color_layout)

        # Add to main layout
        self.layout.addWidget(self.control_group)
        self.layout.addStretch()

    def create_toolbar(self):
        """Create and add toolbar to parent window"""
        self.toolbar_3d = QtWidgets.QToolBar("3D Control Tools", self.parent)
        self.toolbar_3d.setFont(QtGui.QFont("Times New Roman", 12))
        self.toolbar_3d.setIconSize(QtCore.QSize(IconSize, IconSize))
        self.toolbar_3d.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.toolbar_3d.setObjectName("3DControlToolBar")

        # 3D view button
        self.action_3d_view = QtWidgets.QAction(self.parent)
        self.action_3d_view.setIcon(QtGui.QIcon("UI/icons/ico/View3D.ico"))
        self.action_3d_view.setText("3D View")
        self.action_3d_view.setCheckable(True)
        self.action_3d_view.setToolTip("Show/Hide 3D view")
        self.toolbar_3d.addAction(self.action_3d_view)

        self.toolbar_3d.addSeparator()

        # Operation buttons
        self.action_hole = QtWidgets.QAction(self.parent)
        self.action_hole.setIcon(QtGui.QIcon("UI/icons/ico/Segmentation.ico"))
        self.action_hole.setText("Hole")
        self.action_hole.setToolTip("Apply hole operation to selected class areas")
        self.toolbar_3d.addAction(self.action_hole)

        self.action_highlight = QtWidgets.QAction(self.parent)
        self.action_highlight.setIcon(QtGui.QIcon("UI/icons/ico/Highlight.ico"))
        self.action_highlight.setText("Highlight")
        self.action_highlight.setToolTip("Highlight selected class areas")
        self.toolbar_3d.addAction(self.action_highlight)

        self.action_holeleave = QtWidgets.QAction(self.parent)
        self.action_holeleave.setIcon(QtGui.QIcon("UI/icons/ico/Leave.ico"))
        self.action_holeleave.setText("Show Hole")
        self.action_holeleave.setToolTip("Show only selected class areas")
        self.toolbar_3d.addAction(self.action_holeleave)

        self.action_mark = QtWidgets.QAction(self.parent)
        self.action_mark.setIcon(QtGui.QIcon("UI/icons/ico/Tag.ico"))
        self.action_mark.setText("Mark")
        self.action_mark.setToolTip("Mark selected class areas on image")
        self.toolbar_3d.addAction(self.action_mark)

        self.toolbar_3d.addSeparator()

        self.action_threshold = QtWidgets.QAction(self.parent)
        self.action_threshold.setIcon(QtGui.QIcon("UI/icons/ico/SegmentationThreshold.ico"))
        self.action_threshold.setText("Threshold Segmentation")
        self.action_threshold.setToolTip("Segment image based on input threshold")
        self.toolbar_3d.addAction(self.action_threshold)

        self.action_calcu_2d = QtWidgets.QAction(self.parent)
        self.action_calcu_2d.setIcon(QtGui.QIcon("UI/icons/ico/Information2D.ico"))
        self.action_calcu_2d.setText("2D Calculation")
        self.action_calcu_2d.setToolTip("Calculate features for current page")
        self.toolbar_3d.addAction(self.action_calcu_2d)

        self.action_calcu_3d = QtWidgets.QAction(self.parent)
        self.action_calcu_3d.setIcon(QtGui.QIcon("UI/icons/ico/Information3D.ico"))
        self.action_calcu_3d.setText("3D Calculation")
        self.action_calcu_3d.setToolTip("Calculate features for voxels")
        self.toolbar_3d.addAction(self.action_calcu_3d)

    def show_toolbar(self):
        """Show toolbar"""
        # Add to main window's top toolbar area
        if hasattr(self, 'toolbar_3d'):
            self.toolbar_3d.show()
        else:
            self.create_toolbar()
            self.setup_connections()
            self.parent.addToolBar(QtCore.Qt.TopToolBarArea, self.toolbar_3d)

    def hide_toolbar(self):
        """Hide toolbar"""
        if hasattr(self, 'toolbar_3d'):
            self.toolbar_3d.hide()

    def setup_connections(self):
        """Connect signals and slots"""
        # Toolbar button connections
        self.action_3d_view.triggered.connect(self.on_3d_view_toggled)
        self.action_hole.triggered.connect(self.apply_hole_operation)
        self.action_highlight.triggered.connect(self.apply_highlight_operation)
        self.action_holeleave.triggered.connect(self.apply_holeshow_operation)
        self.action_mark.triggered.connect(self.apply_mark_operation)
        self.action_threshold.triggered.connect(self.apply_threshold_operation)
        self.action_calcu_2d.triggered.connect(self.calculate_2d_info)
        self.action_calcu_3d.triggered.connect(self.calculate_3d_info)

        # Dock internal button connections
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        self.colormap_combo.currentIndexChanged.connect(self.on_colormap_changed)
        self.color_slider.valueChanged.connect(self.on_color_changed)

        # Other connections
        self.all_process_checkbox.stateChanged.connect(self.on_process_changed)

    def on_colormap_changed(self, index):
        """Handle colormap changes"""
        # Get current ImagesViewer instance
        images_viewer = self.parent.tab_widget.currentWidget()
        colormap = self.colormap_combo.currentData()
        if hasattr(images_viewer, 'plotter_3d') and images_viewer.plotter_3d is not None:
            self.parent.statusbar.showMessage(f"Colormap changed to: {self.colormap_combo.currentText()}", 2000)
            images_viewer.refresh_3d_view(colormap)

    def get_colormap(self):
        """
        Get currently selected colormap
        :return: Colormap name string
        """
        return self.colormap_combo.currentData()

    def on_threshold_changed(self, value):
        """Handle threshold changes"""
        self.threshold_value_label.setText(str(value))
        # Process current image in real-time
        self.apply_threshold_to_current_image(value)

    def on_color_changed(self, value):
        """Handle color changes"""
        self.color_value_label.setText(str(value))
        # Process current 3d view in real-time
        # self.color_changed.emit(value)

    def apply_threshold_to_current_image(self, threshold_value):
        """
        Apply threshold segmentation to currently displayed image
        """
        # Get current ImagesViewer instance
        images_viewer = self.parent.tab_widget.currentWidget()
        if not hasattr(images_viewer, 'img') or images_viewer.img is None:
            return

        try:
            # Get current image
            file_path, img = images_viewer.img

            # Convert to grayscale image (if needed)
            if len(img.shape) == 3:
                gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray_img = img

            # Apply threshold segmentation
            if self.binary_checkbox.isChecked():
                # Apply threshold segmentation
                _, binary_img = cv2.threshold(gray_img, threshold_value, 255, cv2.THRESH_BINARY)
            else:
                gray_img[gray_img < threshold_value] = 0
                binary_img = gray_img
            # Convert binary image to 3-channel to maintain consistency
            if len(img.shape) == 3:
                result_img = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2BGR)
            else:
                result_img = binary_img

            # Update display
            images_viewer.update_image(result_img)

        except Exception as e:
            self.parent.statusbar.showMessage(f"Threshold segmentation processing error: {str(e)}", 5000)

    def on_3d_view_toggled(self, checked):
        """3D view toggle"""
        # Get current ImagesViewer instance
        images_viewer = self.parent.tab_widget.currentWidget()
        if checked:
            images_viewer.show_3d()
        else:
            images_viewer.hide_3d()

    def on_process_changed(self, state):
        """Mask display state change"""
        visible = state == QtCore.Qt.Checked
        self.all_process = visible
        # self.mask_visibility_changed.emit(visible)

    def apply_hole_operation(self):
        """
        Apply dilation to the selected category region (adapted to results_label format)
        """
        selected_classes = self.parent.yolo_dock.get_selected_classes() if self.parent.annos_dock.show_filtered else None

        if isinstance(selected_classes, (list, tuple)) and len(selected_classes) < 1:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select the category to process first")
            return

        # Get the current ImagesViewer instance
        images_viewer = self.parent.tab_widget.currentWidget()
        if not hasattr(images_viewer, 'image_cache') or not hasattr(images_viewer, 'yolo_results'):
            QtWidgets.QMessageBox.warning(self, "Warning", "The current view does not support this operation.")
            return

        # 检查 image_cache 是否为空，如果为空则根据处理范围临时加载
        if not images_viewer.image_cache:
            if self.all_process_checkbox.isChecked():
                # 处理所有图像：加载文件管理器中的所有图像
                total_files = self.parent.files_dock.list_widget.count()
                if total_files == 0:
                    QtWidgets.QMessageBox.warning(self, "Warning",
                                                  "No files available to load. Please add images first.")
                    return
                if len(images_viewer.image_cache) == 0:
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "Load Images",
                        f"No cached images found. Load {total_files} images temporarily?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                    )

                    if reply == QtWidgets.QMessageBox.Yes:
                        progress_dialog = QtWidgets.QProgressDialog("Loading images...", "Cancel", 0, total_files,
                                                                    self.parent)
                        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
                        progress_dialog.setWindowTitle("Loading Images")
                        progress_dialog.show()

                        for i in range(total_files):
                            progress_dialog.setValue(i)
                            progress_dialog.setLabelText(f"Loading: {i + 1}/{total_files}")

                            QtWidgets.QApplication.processEvents()

                            if progress_dialog.wasCanceled():
                                progress_dialog.close()
                                return

                            item = self.parent.files_dock.list_widget.item(i)
                            file_path = item.data(QtCore.Qt.UserRole)

                            if file_path not in images_viewer.image_cache:
                                try:
                                    img = cv2.imread(file_path)
                                    if img is not None:
                                        images_viewer.image_cache[file_path] = img
                                except Exception as e:
                                    print(f"Failed to load {file_path}: {str(e)}")
                                    continue

                        progress_dialog.setValue(total_files)
                        progress_dialog.close()

                        if not images_viewer.image_cache:
                            QtWidgets.QMessageBox.warning(self, "Warning", "Failed to load any images from file list.")
                            return
                    else:
                        return
            else:
                # 处理单个图像：只加载当前选中的图像
                current_item = self.parent.files_dock.list_widget.currentItem()
                if not current_item:
                    QtWidgets.QMessageBox.warning(self, "Warning", "No image selected")
                    return

                file_path = current_item.data(QtCore.Qt.UserRole)
                if file_path not in images_viewer.image_cache:
                    try:
                        img = cv2.imread(file_path)
                        if img is not None:
                            images_viewer.image_cache[file_path] = img
                        else:
                            QtWidgets.QMessageBox.warning(self, "Warning", f"Failed to load image: {file_path}")
                            return
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(self, "Warning", f"Error loading image: {str(e)}")
                        return

        # Confirm the file to process.
        if self.all_process_checkbox.isChecked():
            # Process all images
            files_to_process = list(images_viewer.image_cache.items())
        else:
            # Process only the current image
            current_item = self.parent.files_dock.list_widget.currentItem()
            if not current_item:
                QtWidgets.QMessageBox.warning(self, "Warning", "No image selected")
                return
            file_path = current_item.data(QtCore.Qt.UserRole)
            if file_path not in images_viewer.image_cache:
                QtWidgets.QMessageBox.warning(self, "Warning", "The current image is not loaded")
                return
            files_to_process = [(file_path, images_viewer.image_cache[file_path])]

        # Show progress dialog
        progress_dialog = QtWidgets.QProgressDialog("Performing dilation...", "cancel", 0, len(files_to_process),
                                                    self.parent)
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setWindowTitle("Dilation operation")
        progress_dialog.show()

        # Process image
        processed_count = 0
        for i, (file_path, img) in enumerate(files_to_process):
            # Update progress
            progress_dialog.setValue(i)
            progress_dialog.setLabelText(f"Processing: {os.path.basename(file_path)}")

            # Process events to update UI
            QtWidgets.QApplication.processEvents()

            # Check if the user canceled the operation
            if progress_dialog.wasCanceled():
                break

            if file_path in images_viewer.yolo_results:
                results_label = deepcopy(images_viewer.yolo_results[file_path])
                results_label = self.parent.plotter.filter_results_label(results_label, selected_classes)
                # Check for mask data
                if "masks" in results_label and results_label["masks"]:
                    # Get mask data
                    masks_data = results_label["masks"]

                    # Create dilation mask
                    hole_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)

                    # Process each selected category
                    for mask_info in masks_data:
                        if len(mask_info) > 0:
                            points = mask_info[1:]
                            if len(points) >= 6 and len(points) % 2 == 0:  # At least 3 points

                                # Create polygon point array
                                pts = np.array([[points[i], points[i + 1]] for i in range(0, len(points), 2)],
                                               np.int32)

                                # Draw polygon on mask
                                cv2.fillPoly(hole_mask, [pts], 1)

                    # Apply dilation (set selected area to black)
                    if np.any(hole_mask):
                        img[hole_mask > 0] = [0, 0, 0]  # Set selected area to black
                        images_viewer.image_cache[file_path] = img
                        processed_count += 1

        # Processing complete
        progress_dialog.setValue(len(files_to_process))

        self.parent.statusbar.showMessage(f"Dilation completed for {processed_count} images", 3000)
        # Update the currently displayed image
        current_item = self.parent.files_dock.list_widget.currentItem()
        if current_item:
            file_path = current_item.data(QtCore.Qt.UserRole)
            images_viewer.load_file(file_path)

    def apply_highlight_operation(self):
        """
        Highlight selected class areas (Adapt to `results_label` format)
        """
        selected_classes = self.parent.yolo_dock.get_selected_classes() if self.parent.annos_dock.show_filtered else None

        if isinstance(selected_classes, (list, tuple)) and len(selected_classes) < 1:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select the category to process first.")
            return

        # Get the current `ImagesViewer` instance
        images_viewer = self.parent.tab_widget.currentWidget()
        if not hasattr(images_viewer, 'image_cache') or not hasattr(images_viewer, 'yolo_results'):
            QtWidgets.QMessageBox.warning(self, "Warning", "The current view does not support this operation")
            return

        # 检查 image_cache 是否为空，如果为空则根据处理范围临时加载
        if not images_viewer.image_cache:
            if self.all_process_checkbox.isChecked():
                # 处理所有图像：加载文件管理器中的所有图像
                total_files = self.parent.files_dock.list_widget.count()
                if total_files == 0:
                    QtWidgets.QMessageBox.warning(self, "Warning",
                                                  "No files available to load. Please add images first.")
                    return
                if len(images_viewer.image_cache) == 0:
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "Load Images",
                        f"No cached images found. Load {total_files} images temporarily?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                    )

                    if reply == QtWidgets.QMessageBox.Yes:
                        progress_dialog = QtWidgets.QProgressDialog("Loading images...", "Cancel", 0, total_files,
                                                                    self.parent)
                        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
                        progress_dialog.setWindowTitle("Loading Images")
                        progress_dialog.show()

                        for i in range(total_files):
                            progress_dialog.setValue(i)
                            progress_dialog.setLabelText(f"Loading: {i + 1}/{total_files}")

                            QtWidgets.QApplication.processEvents()

                            if progress_dialog.wasCanceled():
                                progress_dialog.close()
                                return

                            item = self.parent.files_dock.list_widget.item(i)
                            file_path = item.data(QtCore.Qt.UserRole)

                            if file_path not in images_viewer.image_cache:
                                try:
                                    img = cv2.imread(file_path)
                                    if img is not None:
                                        images_viewer.image_cache[file_path] = img
                                except Exception as e:
                                    print(f"Failed to load {file_path}: {str(e)}")
                                    continue

                        progress_dialog.setValue(total_files)
                        progress_dialog.close()

                        if not images_viewer.image_cache:
                            QtWidgets.QMessageBox.warning(self, "Warning", "Failed to load any images from file list.")
                            return
                    else:
                        return
            else:
                # 处理单个图像：只加载当前选中的图像
                current_item = self.parent.files_dock.list_widget.currentItem()
                if not current_item:
                    QtWidgets.QMessageBox.warning(self, "Warning", "No image selected")
                    return

                file_path = current_item.data(QtCore.Qt.UserRole)
                if file_path not in images_viewer.image_cache:
                    try:
                        img = cv2.imread(file_path)
                        if img is not None:
                            images_viewer.image_cache[file_path] = img
                        else:
                            QtWidgets.QMessageBox.warning(self, "Warning", f"Failed to load image: {file_path}")
                            return
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(self, "Warning", f"Error loading image: {str(e)}")
                        return

        # Confirm the files to process.
        if self.all_process_checkbox.isChecked():
            # Process all images.
            files_to_process = list(images_viewer.image_cache.items())
        else:
            # Process only the current image.
            current_item = self.parent.files_dock.list_widget.currentItem()
            if not current_item:
                QtWidgets.QMessageBox.warning(self, "Warning", "No image selected")
                return
            file_path = current_item.data(QtCore.Qt.UserRole)
            if file_path not in images_viewer.image_cache:
                QtWidgets.QMessageBox.warning(self, "Warning", "The current image is not loaded")
                return
            files_to_process = [(file_path, images_viewer.image_cache[file_path])]

        # Show progress dialog
        progress_dialog = QtWidgets.QProgressDialog("Performing highlight operation...", "Cancel", 0,
                                                    len(files_to_process),
                                                    self.parent)
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setWindowTitle("Highlight operation")
        progress_dialog.show()

        # Process image
        processed_count = 0

        for i, (file_path, img) in enumerate(files_to_process):
            # Update progress
            progress_dialog.setValue(i)
            progress_dialog.setLabelText(f"Processing: {os.path.basename(file_path)}")

            # Process events to update UI
            QtWidgets.QApplication.processEvents()

            # Check if the user canceled the operation
            if progress_dialog.wasCanceled():
                break

            if file_path in images_viewer.yolo_results:
                results_label = deepcopy(images_viewer.yolo_results[file_path])
                results_label = self.parent.plotter.filter_results_label(results_label, selected_classes)

                # Check for mask data
                if "masks" in results_label and results_label["masks"]:
                    # Get mask data
                    masks_data = results_label["masks"]

                    # Create highlight mask
                    highlight_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)

                    # Process each selected category
                    # names = results_label.get("names", {})
                    for mask_info in masks_data:
                        if len(mask_info) > 0:
                            points = mask_info[1:]
                            if len(points) >= 6 and len(points) % 2 == 0:  # At least 3 points
                                # Create polygon point array
                                pts = np.array([[points[i], points[i + 1]] for i in range(0, len(points), 2)],
                                               np.int32)

                                # Draw polygon on mask
                                cv2.fillPoly(highlight_mask, [pts], 1)

                    # Apply highlight operation (increase brightness and contrast)
                    if np.any(highlight_mask):
                        # Create highlight effect
                        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                        hsv[:, :, 1] = np.where(highlight_mask > 0,
                                                np.minimum(hsv[:, :, 1].astype(np.uint16) + 50, 255).astype(
                                                    np.uint8),
                                                hsv[:, :, 1])
                        hsv[:, :, 2] = np.where(highlight_mask > 0,
                                                np.minimum(hsv[:, :, 2].astype(np.uint16) + 50, 255).astype(
                                                    np.uint8),
                                                hsv[:, :, 2])
                        highlighted_img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

                        # Restore non-highlighted areas to the original image
                        mask_3d = np.stack([highlight_mask, highlight_mask, highlight_mask], axis=2)
                        img = np.where(mask_3d > 0, highlighted_img, img)

                        images_viewer.image_cache[file_path] = img
                        processed_count += 1

        # Processing complete
        progress_dialog.setValue(len(files_to_process))

        self.parent.statusbar.showMessage(f"Dilation completed for {processed_count} images", 3000)

        # Update displayed image
        current_item = self.parent.files_dock.list_widget.currentItem()
        if current_item:
            file_path = current_item.data(QtCore.Qt.UserRole)
            images_viewer.load_file(file_path)

    def apply_holeleave_operation(self):
        """
        Keep selected class, set rest to black (for results_label)
        """
        selected_classes = self.parent.yolo_dock.get_selected_classes() if self.parent.annos_dock.show_filtered else None

        if isinstance(selected_classes, (list, tuple)) and len(selected_classes) < 1:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a class to process")
            return

        # Get current ImagesViewer instance
        images_viewer = self.parent.tab_widget.currentWidget()
        if not hasattr(images_viewer, 'image_cache') or not hasattr(images_viewer, 'yolo_results'):
            QtWidgets.QMessageBox.warning(self, "Warning", " Operation not supported in current view")
            return

        # 检查 image_cache 是否为空，如果为空则根据处理范围临时加载
        if not images_viewer.image_cache:
            if self.all_process_checkbox.isChecked():
                # 处理所有图像：加载文件管理器中的所有图像
                total_files = self.parent.files_dock.list_widget.count()
                if total_files == 0:
                    QtWidgets.QMessageBox.warning(self, "Warning",
                                                  "No files available to load. Please add images first.")
                    return
                if len(images_viewer.image_cache) == 0:
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "Load Images",
                        f"No cached images found. Load {total_files} images temporarily?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                    )

                    if reply == QtWidgets.QMessageBox.Yes:
                        progress_dialog = QtWidgets.QProgressDialog("Loading images...", "Cancel", 0, total_files,
                                                                    self.parent)
                        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
                        progress_dialog.setWindowTitle("Loading Images")
                        progress_dialog.show()

                        for i in range(total_files):
                            progress_dialog.setValue(i)
                            progress_dialog.setLabelText(f"Loading: {i + 1}/{total_files}")

                            QtWidgets.QApplication.processEvents()

                            if progress_dialog.wasCanceled():
                                progress_dialog.close()
                                return

                            item = self.parent.files_dock.list_widget.item(i)
                            file_path = item.data(QtCore.Qt.UserRole)

                            if file_path not in images_viewer.image_cache:
                                try:
                                    img = cv2.imread(file_path)
                                    if img is not None:
                                        images_viewer.image_cache[file_path] = img
                                except Exception as e:
                                    print(f"Failed to load {file_path}: {str(e)}")
                                    continue

                        progress_dialog.setValue(total_files)
                        progress_dialog.close()

                        if not images_viewer.image_cache:
                            QtWidgets.QMessageBox.warning(self, "Warning", "Failed to load any images from file list.")
                            return
                    else:
                        return
            else:
                # 处理单个图像：只加载当前选中的图像
                current_item = self.parent.files_dock.list_widget.currentItem()
                if not current_item:
                    QtWidgets.QMessageBox.warning(self, "Warning", "No image selected")
                    return

                file_path = current_item.data(QtCore.Qt.UserRole)
                if file_path not in images_viewer.image_cache:
                    try:
                        img = cv2.imread(file_path)
                        if img is not None:
                            images_viewer.image_cache[file_path] = img
                        else:
                            QtWidgets.QMessageBox.warning(self, "Warning", f"Failed to load image: {file_path}")
                            return
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(self, "Warning", f"Error loading image: {str(e)}")
                        return

        # Confirm files to process
        if self.all_process_checkbox.isChecked():
            # Process all images
            files_to_process = list(images_viewer.image_cache.items())
        else:
            # Process current image only
            current_item = self.parent.files_dock.list_widget.currentItem()
            if not current_item:
                QtWidgets.QMessageBox.warning(self, "Warning", "No image selected")
                return
            file_path = current_item.data(QtCore.Qt.UserRole)
            if file_path not in images_viewer.image_cache:
                QtWidgets.QMessageBox.warning(self, "Warning", "Image not loaded")
                return
            files_to_process = [(file_path, images_viewer.image_cache[file_path])]

        # Show progress dialog
        progress_dialog = QtWidgets.QProgressDialog("Performing mask operation...", "Cancel", 0, len(files_to_process),
                                                    self.parent)
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setWindowTitle("Keep Region Operation")
        progress_dialog.show()

        # Process image
        processed_count = 0
        for i, (file_path, img) in enumerate(files_to_process):
            # Update progress
            progress_dialog.setValue(i)
            progress_dialog.setLabelText(f"Processing: {os.path.basename(file_path)}")

            # Process UI events
            QtWidgets.QApplication.processEvents()

            # Check for cancel
            if progress_dialog.wasCanceled():
                break

            if file_path in images_viewer.yolo_results:
                results_label = deepcopy(images_viewer.yolo_results[file_path])
                results_label = self.parent.plotter.filter_results_label(results_label, selected_classes)

                # Check for mask data
                if "masks" in results_label and results_label["masks"]:
                    # Get mask data
                    masks_data = results_label["masks"]

                    # Create mask for keep operation
                    keep_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)

                    for mask_info in masks_data:
                        if len(mask_info) > 0:
                            points = mask_info[1:]
                            if len(points) >= 6 and len(points) % 2 == 0:  # At least 3 points
                                # Create polygon points
                                pts = np.array([[points[i], points[i + 1]] for i in range(0, len(points), 2)],
                                               np.int32)

                                # Draw polygon on mask
                                cv2.fillPoly(keep_mask, [pts], 1)

                    # Apply keep operation (set non-selected to black)
                    if np.any(keep_mask):
                        # Invert mask (non-selected to 0)
                        inverted_mask = 1 - keep_mask
                        # Set non-selected to black
                        img[inverted_mask > 0] = [0, 0, 0]
                        images_viewer.image_cache[file_path] = img
                        processed_count += 1

        # Done
        progress_dialog.setValue(len(files_to_process))

        self.parent.statusbar.showMessage(f"Dilation completed for {processed_count} images", 3000)

        # Update displayed image
        current_item = self.parent.files_dock.list_widget.currentItem()
        if current_item:
            file_path = current_item.data(QtCore.Qt.UserRole)
            images_viewer.load_file(file_path)

    def apply_holeshow_operation(self):
        """
        Show mask of selected class, set background to black (for results_label)
        """
        selected_classes = self.parent.yolo_dock.get_selected_classes() if self.parent.annos_dock.show_filtered else None

        if isinstance(selected_classes, (list, tuple)) and len(selected_classes) < 1:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a class to process")
            return

        # Get current ImagesViewer instance
        images_viewer = self.parent.tab_widget.currentWidget()
        if not hasattr(images_viewer, 'image_cache') or not hasattr(images_viewer, 'yolo_results'):
            QtWidgets.QMessageBox.warning(self, "Warning", "Operation not supported in current view")
            return

        # 检查 image_cache 是否为空，如果为空则根据处理范围临时加载
        if not images_viewer.image_cache:
            if self.all_process_checkbox.isChecked():
                # 处理所有图像：加载文件管理器中的所有图像
                total_files = self.parent.files_dock.list_widget.count()
                if total_files == 0:
                    QtWidgets.QMessageBox.warning(self, "Warning",
                                                  "No files available to load. Please add images first.")
                    return
                if len(images_viewer.image_cache) == 0:
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "Load Images",
                        f"No cached images found. Load {total_files} images temporarily?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                    )

                    if reply == QtWidgets.QMessageBox.Yes:
                        progress_dialog = QtWidgets.QProgressDialog("Loading images...", "Cancel", 0, total_files,
                                                                    self.parent)
                        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
                        progress_dialog.setWindowTitle("Loading Images")
                        progress_dialog.show()

                        for i in range(total_files):
                            progress_dialog.setValue(i)
                            progress_dialog.setLabelText(f"Loading: {i + 1}/{total_files}")

                            QtWidgets.QApplication.processEvents()

                            if progress_dialog.wasCanceled():
                                progress_dialog.close()
                                return

                            item = self.parent.files_dock.list_widget.item(i)
                            file_path = item.data(QtCore.Qt.UserRole)

                            if file_path not in images_viewer.image_cache:
                                try:
                                    img = cv2.imread(file_path)
                                    if img is not None:
                                        images_viewer.image_cache[file_path] = img
                                except Exception as e:
                                    print(f"Failed to load {file_path}: {str(e)}")
                                    continue

                        progress_dialog.setValue(total_files)
                        progress_dialog.close()

                        if not images_viewer.image_cache:
                            QtWidgets.QMessageBox.warning(self, "Warning", "Failed to load any images from file list.")
                            return
                    else:
                        return
            else:
                # 处理单个图像：只加载当前选中的图像
                current_item = self.parent.files_dock.list_widget.currentItem()
                if not current_item:
                    QtWidgets.QMessageBox.warning(self, "Warning", "No image selected")
                    return

                file_path = current_item.data(QtCore.Qt.UserRole)
                if file_path not in images_viewer.image_cache:
                    try:
                        img = cv2.imread(file_path)
                        if img is not None:
                            images_viewer.image_cache[file_path] = img
                        else:
                            QtWidgets.QMessageBox.warning(self, "Warning", f"Failed to load image: {file_path}")
                            return
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(self, "Warning", f"Error loading image: {str(e)}")
                        return

        # Confirm files to process
        if self.all_process_checkbox.isChecked():
            # Process all images
            files_to_process = list(images_viewer.image_cache.items())
        else:
            # Process current image only
            current_item = self.parent.files_dock.list_widget.currentItem()
            if not current_item:
                QtWidgets.QMessageBox.warning(self, "Warning", "No image selected")
                return
            file_path = current_item.data(QtCore.Qt.UserRole)
            if file_path not in images_viewer.image_cache:
                QtWidgets.QMessageBox.warning(self, "Warning", "Image not loaded")
                return
            files_to_process = [(file_path, images_viewer.image_cache[file_path])]

        # Show progress dialog
        progress_dialog = QtWidgets.QProgressDialog("Showing mask...", "Cancel", 0, len(files_to_process),
                                                    self.parent)
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setWindowTitle("Show Mask")
        progress_dialog.show()

        # Process image
        processed_count = 0
        for i, (file_path, img) in enumerate(files_to_process):
            # Update progress
            progress_dialog.setValue(i)
            progress_dialog.setLabelText(f"Processing: {os.path.basename(file_path)}")

            # Update UI
            QtWidgets.QApplication.processEvents()

            #  Check for cancel
            if progress_dialog.wasCanceled():
                break

            if file_path in images_viewer.yolo_results:
                results_label = deepcopy(images_viewer.yolo_results[file_path])
                results_label = self.parent.plotter.filter_results_label(results_label, selected_classes)

                # Check for mask data
                if "masks" in results_label and results_label["masks"]:
                    # Get mask data
                    masks_data = results_label["masks"]

                    # Create mask for keep operation
                    show_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)

                    for mask_info in masks_data:
                        if len(mask_info) > 0:
                            points = mask_info[1:]
                            if len(points) >= 6 and len(points) % 2 == 0:  # At least 3 points
                                # Create polygon points
                                pts = np.array([[points[i], points[i + 1]] for i in range(0, len(points), 2)],
                                               np.int32)

                                # Draw polygon on mask
                                cv2.fillPoly(show_mask, [pts], 1)

                    # Apply keep operation (set non-selected to white)
                    if np.any(show_mask):
                        # Generate image containing only mask
                        # Set mask to white, background black
                        mask_img = np.zeros_like(img)
                        mask_img[show_mask > 0] = [128, 128, 128]  # White mask
                        images_viewer.image_cache[file_path] = mask_img
                        processed_count += 1

        # Done
        progress_dialog.setValue(len(files_to_process))

        self.parent.statusbar.showMessage(f"Dilation completed for {processed_count} images", 3000)

        # Update the currently displayed image
        current_item = self.parent.files_dock.list_widget.currentItem()
        if current_item:
            file_path = current_item.data(QtCore.Qt.UserRole)
            images_viewer.load_file(file_path)

    def apply_mark_operation(self):
        """
        Mark selected class on image (for results_label)
        """
        selected_classes = self.parent.yolo_dock.get_selected_classes() if self.parent.annos_dock.show_filtered else None

        if isinstance(selected_classes, (list, tuple)) and len(selected_classes) < 1:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a class to process")
            return

        # Get current ImagesViewer instance
        images_viewer = self.parent.tab_widget.currentWidget()
        if not hasattr(images_viewer, 'image_cache') or not hasattr(images_viewer, 'yolo_results'):
            QtWidgets.QMessageBox.warning(self, "Warning", "Operation not supported in current view")
            return

        # 检查 image_cache 是否为空，如果为空则根据处理范围临时加载
        if not images_viewer.image_cache:
            if self.all_process_checkbox.isChecked():
                # 处理所有图像：加载文件管理器中的所有图像
                total_files = self.parent.files_dock.list_widget.count()
                if total_files == 0:
                    QtWidgets.QMessageBox.warning(self, "Warning",
                                                  "No files available to load. Please add images first.")
                    return
                if len(images_viewer.image_cache) == 0:
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "Load Images",
                        f"No cached images found. Load {total_files} images temporarily?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                    )

                    if reply == QtWidgets.QMessageBox.Yes:
                        progress_dialog = QtWidgets.QProgressDialog("Loading images...", "Cancel", 0, total_files,
                                                                    self.parent)
                        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
                        progress_dialog.setWindowTitle("Loading Images")
                        progress_dialog.show()

                        for i in range(total_files):
                            progress_dialog.setValue(i)
                            progress_dialog.setLabelText(f"Loading: {i + 1}/{total_files}")

                            QtWidgets.QApplication.processEvents()

                            if progress_dialog.wasCanceled():
                                progress_dialog.close()
                                return

                            item = self.parent.files_dock.list_widget.item(i)
                            file_path = item.data(QtCore.Qt.UserRole)

                            if file_path not in images_viewer.image_cache:
                                try:
                                    img = cv2.imread(file_path)
                                    if img is not None:
                                        images_viewer.image_cache[file_path] = img
                                except Exception as e:
                                    print(f"Failed to load {file_path}: {str(e)}")
                                    continue

                        progress_dialog.setValue(total_files)
                        progress_dialog.close()

                        if not images_viewer.image_cache:
                            QtWidgets.QMessageBox.warning(self, "Warning", "Failed to load any images from file list.")
                            return
                    else:
                        return
            else:
                # 处理单个图像：只加载当前选中的图像
                current_item = self.parent.files_dock.list_widget.currentItem()
                if not current_item:
                    QtWidgets.QMessageBox.warning(self, "Warning", "No image selected")
                    return

                file_path = current_item.data(QtCore.Qt.UserRole)
                if file_path not in images_viewer.image_cache:
                    try:
                        img = cv2.imread(file_path)
                        if img is not None:
                            images_viewer.image_cache[file_path] = img
                        else:
                            QtWidgets.QMessageBox.warning(self, "Warning", f"Failed to load image: {file_path}")
                            return
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(self, "Warning", f"Error loading image: {str(e)}")
                        return

        # Confirm files to process
        if self.all_process_checkbox.isChecked():
            # Process all images
            files_to_process = list(images_viewer.image_cache.items())
        else:
            # Process current image only
            current_item = self.parent.files_dock.list_widget.currentItem()
            if not current_item:
                QtWidgets.QMessageBox.warning(self, "Warning", "No image selected")
                return
            file_path = current_item.data(QtCore.Qt.UserRole)
            if file_path not in images_viewer.image_cache:
                QtWidgets.QMessageBox.warning(self, "Warning", "Image not loaded")
                return
            files_to_process = [(file_path, images_viewer.image_cache[file_path])]

        # Show progress dialog
        progress_dialog = QtWidgets.QProgressDialog("Marking...", "Cancel", 0, len(files_to_process),
                                                    self.parent)
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setWindowTitle("Mark")
        progress_dialog.show()

        # Process image
        processed_count = 0
        for i, (file_path, img) in enumerate(files_to_process):
            # Update progress
            progress_dialog.setValue(i)
            progress_dialog.setLabelText(f"Processing: {os.path.basename(file_path)}")

            # Update UI
            QtWidgets.QApplication.processEvents()

            # Check for cancel
            if progress_dialog.wasCanceled():
                break

            if file_path in images_viewer.yolo_results:
                results_label = deepcopy(images_viewer.yolo_results[file_path])
                results_label = self.parent.plotter.filter_results_label(results_label, selected_classes)

                # Process mask marks
                if "masks" in results_label and results_label["masks"]:
                    masks_data = results_label["masks"]
                    names = results_label.get("names", {})

                    # Process each selected class
                    for mask_info in masks_data:
                        if len(mask_info) > 0:
                            class_id = int(mask_info[0])
                            class_name = names.get(class_id, f"class_{class_id}")

                            points = mask_info[1:]
                            if len(points) >= 6 and len(points) % 2 == 0:  # At least 3 points
                                # Create polygon points
                                pts = np.array([[points[i], points[i + 1]] for i in range(0, len(points), 2)],
                                               np.int32)

                                # Create mask image
                                mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
                                cv2.fillPoly(mask, [pts], 1)
                                mask = (mask * 255).astype(np.uint8)

                                # Draw mask outline
                                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                                cv2.drawContours(img, contours, -1, (0, 255, 0), 2)

                                # Add label near outline
                                if contours:
                                    # Get largest contour center
                                    largest_contour = max(contours, key=cv2.contourArea)
                                    M = cv2.moments(largest_contour)
                                    if M["m00"] != 0:
                                        cx = int(M["m10"] / M["m00"])
                                        cy = int(M["m01"] / M["m00"])
                                        cv2.putText(img, class_name, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX,
                                                    0.5, (0, 255, 0), 1, cv2.LINE_AA)

                # Process bounding box marks
                elif "boxes" in results_label and results_label["boxes"]:
                    boxes_data = results_label["boxes"]
                    names = results_label.get("names", {})

                    # Process each selected class
                    for box_info in boxes_data:
                        if len(box_info) >= 6:  # [x1, y1, x2, y2, conf, class_id]
                            x1, y1, x2, y2 = map(int, box_info[:4])
                            class_id = int(box_info[5])
                            class_name = names.get(class_id, f"class_{class_id}")

                            # Draw bbox if class is selected
                            if class_name in selected_classes:
                                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.putText(img, class_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                            0.5, (0, 255, 0), 1, cv2.LINE_AA)

                images_viewer.image_cache[file_path] = img
                processed_count += 1

        # Done
        progress_dialog.setValue(len(files_to_process))

        self.parent.statusbar.showMessage(f"Dilation completed for {processed_count} images", 3000)

        # Update displayed image
        current_item = self.parent.files_dock.list_widget.currentItem()
        if current_item:
            file_path = current_item.data(QtCore.Qt.UserRole)
            images_viewer.load_file(file_path)

    def apply_threshold_operation(self):
        """
        Apply threshold segmentation operation
        """
        # Get threshold
        threshold_value = self.threshold_slider.value()

        # Get current ImagesViewer instance
        images_viewer = self.parent.tab_widget.currentWidget()
        if not hasattr(images_viewer, 'image_cache'):
            QtWidgets.QMessageBox.warning(self, "Warning", "Current view does not support this operation")
            return

        # 检查 image_cache 是否为空，如果为空则根据处理范围临时加载
        if hasattr(images_viewer, 'image_cache'):
            if self.all_process_checkbox.isChecked():
                # 处理所有图像：加载文件管理器中的所有图像
                total_files = self.parent.files_dock.list_widget.count()
                if total_files == 0:
                    QtWidgets.QMessageBox.warning(self, "Warning",
                                                  "No files available to load. Please add images first.")
                    return
                if len(images_viewer.image_cache) == 0:
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "Load Images",
                        f"No cached images found. Load {total_files} images temporarily?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                    )

                    if reply == QtWidgets.QMessageBox.Yes:
                        progress_dialog = QtWidgets.QProgressDialog("Loading images...", "Cancel", 0, total_files,
                                                                    self.parent)
                        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
                        progress_dialog.setWindowTitle("Loading Images")
                        progress_dialog.show()

                        for i in range(total_files):
                            progress_dialog.setValue(i)
                            progress_dialog.setLabelText(f"Loading: {i + 1}/{total_files}")

                            QtWidgets.QApplication.processEvents()

                            if progress_dialog.wasCanceled():
                                progress_dialog.close()
                                return

                            item = self.parent.files_dock.list_widget.item(i)
                            file_path = item.data(QtCore.Qt.UserRole)

                            if file_path not in images_viewer.image_cache:
                                try:
                                    img = cv2.imread(file_path)
                                    if img is not None:
                                        images_viewer.image_cache[file_path] = img
                                except Exception as e:
                                    print(f"Failed to load {file_path}: {str(e)}")
                                    continue

                        progress_dialog.setValue(total_files)
                        progress_dialog.close()

                        if not images_viewer.image_cache:
                            QtWidgets.QMessageBox.warning(self, "Warning", "Failed to load any images from file list.")
                            return
                    else:
                        return
            else:
                # 处理单个图像：只加载当前选中的图像
                current_item = self.parent.files_dock.list_widget.currentItem()
                if not current_item:
                    QtWidgets.QMessageBox.warning(self, "Warning", "No image selected")
                    return

                file_path = current_item.data(QtCore.Qt.UserRole)
                if file_path not in images_viewer.image_cache:
                    try:
                        img = cv2.imread(file_path)
                        if img is not None:
                            images_viewer.image_cache[file_path] = img
                        else:
                            QtWidgets.QMessageBox.warning(self, "Warning", f"Failed to load image: {file_path}")
                            return
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(self, "Warning", f"Error loading image: {str(e)}")
                        return

        # Determine files to process
        if self.all_process_checkbox.isChecked():
            # Process all images
            files_to_process = list(images_viewer.image_cache.items())
        else:
            # Process only current image
            current_item = self.parent.files_dock.list_widget.currentItem()
            if not current_item:
                QtWidgets.QMessageBox.warning(self, "Warning", "No image selected")
                return
            file_path = current_item.data(QtCore.Qt.UserRole)
            if file_path not in images_viewer.image_cache:
                QtWidgets.QMessageBox.warning(self, "Warning", "Current image not loaded")
                return
            files_to_process = [(file_path, images_viewer.image_cache[file_path])]

        # Show progress dialog
        progress_dialog = QtWidgets.QProgressDialog("Performing threshold segmentation...", "Cancel", 0,
                                                    len(files_to_process),
                                                    self.parent)
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setWindowTitle("Threshold Segmentation")
        progress_dialog.show()

        # Process threshold segmentation on images
        processed_count = 0
        for i, (file_path, img) in enumerate(files_to_process):
            # Update progress
            progress_dialog.setValue(i)
            progress_dialog.setLabelText(f"Processing: {os.path.basename(file_path)}")

            # Process events to update UI
            QtWidgets.QApplication.processEvents()

            # Check if user canceled operation
            if progress_dialog.wasCanceled():
                break

            try:
                # Convert to grayscale image (if needed)
                if len(img.shape) == 3:
                    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                else:
                    gray_img = img
                if self.binary_checkbox.isChecked():
                    # Apply threshold segmentation
                    _, binary_img = cv2.threshold(gray_img, threshold_value, 255, cv2.THRESH_BINARY)
                else:
                    binary_img = gray_img.copy()
                    binary_img[binary_img < threshold_value] = 0
                # Convert binary image to 3-channel to maintain consistency
                if len(img.shape) == 3:
                    result_img = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2BGR)
                else:
                    result_img = binary_img

                # Update image in cache
                images_viewer.image_cache[file_path] = result_img
                processed_count += 1

            except Exception as e:
                self.parent.statusbar.showMessage(f"Error processing image {os.path.basename(file_path)}: {str(e)}",
                                                  5000)
                continue

        # Complete processing
        progress_dialog.setValue(len(files_to_process))
        progress_dialog.close()

        if processed_count > 0:
            self.parent.statusbar.showMessage(f"Completed threshold segmentation for {processed_count} images", 3000)
        else:
            self.parent.statusbar.showMessage("No images were processed", 3000)

        # Update currently displayed image if it was processed
        current_item = self.parent.files_dock.list_widget.currentItem()
        if current_item:
            file_path = current_item.data(QtCore.Qt.UserRole)
            if file_path in images_viewer.image_cache:
                images_viewer.load_file(file_path)

    def calculate_2d_info(self):
        """
        Calculate pore statistics in 2D images
        """
        current_widget = self.parent.tab_widget.currentWidget()
        file_path, image = current_widget.img
        image = current_widget.image_cache[file_path] if file_path in current_widget.image_cache else image

        # Ensure image is grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Get scale factors
        dx = getattr(current_widget, 'dx', 1.0)
        dy = getattr(current_widget, 'dy', 1.0)

        if current_widget.mask_calcu is not None and isinstance(current_widget.mask_calcu, tuple) and isinstance(current_widget.mask_calcu[0], list):
            label_path = self.get_label_path(file_path, current_widget.mask_calcu[0])
            if label_path is not None and os.path.exists(label_path):
                mask = cv2.imread(label_path, cv2.IMREAD_GRAYSCALE)
                mask = mask if current_widget.mask_calcu[1] else 255 - mask
            else:
                self.parent.statusbar.showMessage(f"Failed to load label image: {label_path}", 3000)
                mask = np.ones_like(gray, dtype=np.uint8) * 255
        elif  current_widget.mask_calcu is not None and isinstance(current_widget.mask_calcu, tuple):
            mask = current_widget.mask_calcu[0]
            mask = mask if current_widget.mask_calcu[1] else 255 - mask
        else:
            mask = np.ones_like(gray, dtype=np.uint8) * 255

        mask = mask.squeeze()
        mask = (mask > 0).astype(np.uint8) * 255
        if mask.shape[:2] != gray.shape[:2]:
            mask = cv2.resize(mask, (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_NEAREST)

        if len(mask.shape) == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

        masked_image = cv2.bitwise_and(gray, mask)

        # Find pores (areas with value 0) within masked area
        pore_mask = np.zeros_like(gray, dtype=np.uint8)
        pore_mask[(masked_image == 0) & (mask == 255)] = 255

        # Calculate total pore area (pixels) - only within mask region
        pore_area_pixels = np.count_nonzero(pore_mask == 255)

        # Calculate total area of mask region
        mask_area = np.count_nonzero(mask == 255)

        # Calculate pore ratio (pore area as proportion of mask area)
        pore_ratio = pore_area_pixels / mask_area if mask_area > 0 else 0

        # Calculate total pore volume (assuming unit thickness)
        # Apply scale factors
        scaled_pore_area = pore_area_pixels * dx * dy
        scaled_mask_area = mask_area * dx * dy
        scaled_pore_volume = scaled_pore_area  # In 2D case, volume equals area

        return_info = \
            f"pore_ratio: {pore_ratio:.6f}" + "\n" + \
            f"pore_area: {pore_area_pixels}" + "\n" + \
            f"total_area: {mask_area}" + "\n" + \
            f"scaled_pore_area: {scaled_pore_area:.6f}" + "\n" + \
            f"scaled_total_area: {scaled_mask_area:.6f}" + "\n" + \
            f"scaled_pore_volume: {scaled_pore_volume:.6f}" + "\n" + \
            f"scale_factors: dx: {dx:.3f}, dy: {dy:.3f}"

        # Show information dialog
        msg_box = QtWidgets.QMessageBox(self.parent)
        msg_box.setWindowTitle("Surface Measurement Information")
        msg_box.setText(str(return_info))
        msg_box.exec_()

    @staticmethod
    def get_label_path(file_path, label_dir):
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        if len(label_dir) > 0:
            matched_files = []
            for label_file in label_dir:
                label_base = os.path.splitext(os.path.basename(label_file))[0]
                if label_base == base_name:
                    matched_files.append(label_file)
            if matched_files:
                for label_file in matched_files:
                    _, ext = os.path.splitext(label_file)
                    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", }:
                        return label_file
        return None

    def calculate_3d_info(self):
        """
        Calculate pore statistics in 3D images
        """
        # Get current ImagesViewer instance
        images_viewer = self.parent.tab_widget.currentWidget()

        if not hasattr(images_viewer, 'image_cache'):
            QtWidgets.QMessageBox.warning(self, "Warning", "Current view does not support this operation")
            return

        # 检查 image_cache 是否为空，如果为空则自动加载所有图像
        if not images_viewer.image_cache:
            total_files = self.parent.files_dock.list_widget.count()
            if total_files == 0:
                QtWidgets.QMessageBox.warning(self, "Warning", "No files available to load. Please add images first.")
                return

            reply = QtWidgets.QMessageBox.question(
                self,
                "Load Images",
                f"No cached images found. Load {total_files} images automatically?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                # 显示加载进度
                progress_dialog = QtWidgets.QProgressDialog("Loading images...", "Cancel", 0, total_files, self.parent)
                progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
                progress_dialog.setWindowTitle("Loading Images")
                progress_dialog.show()

                # 从文件管理器加载所有图像到缓存
                loaded_count = 0
                for i in range(total_files):
                    progress_dialog.setValue(i)
                    progress_dialog.setLabelText(f"Loading: {i + 1}/{total_files}")

                    QtWidgets.QApplication.processEvents()

                    if progress_dialog.wasCanceled():
                        progress_dialog.close()
                        return

                    item = self.parent.files_dock.list_widget.item(i)
                    file_path = item.data(QtCore.Qt.UserRole)

                    # 加载图像到缓存
                    if file_path not in images_viewer.image_cache:
                        try:
                            img = cv2.imread(file_path)
                            if img is not None:
                                images_viewer.image_cache[file_path] = img
                                loaded_count += 1
                        except Exception as e:
                            print(f"Failed to load {file_path}: {str(e)}")
                            continue

                progress_dialog.setValue(total_files)
                progress_dialog.close()

                if loaded_count == 0:
                    QtWidgets.QMessageBox.warning(self, "Warning", "Failed to load any images from file list.")
                    return
                else:
                    self.parent.statusbar.showMessage(f"Loaded {loaded_count} images automatically", 3000)
            else:
                return  # 用户取消操作

        # Get all images in the correct order
        images = []
        file_paths = []

        # Get images in order from file manager
        total_files = self.parent.files_dock.list_widget.count()

        # Show progress dialog
        progress_dialog = QtWidgets.QProgressDialog("Preparing 3D calculation...", "Cancel", 0, total_files,
                                                    self.parent)
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setWindowTitle("3D Calculation Preparation")
        progress_dialog.show()

        for i in range(total_files):
            # Update progress
            progress_dialog.setValue(i)

            item = self.parent.files_dock.list_widget.item(i)
            file_path = item.data(QtCore.Qt.UserRole)
            if file_path in images_viewer.image_cache:
                img = images_viewer.image_cache[file_path]
                # Ensure image is grayscale
                if len(img.shape) == 3:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                else:
                    gray = img
                images.append(gray)
                file_paths.append(file_path)

            # Process events to update UI
            QtWidgets.QApplication.processEvents()

            # Check if user canceled operation
            if progress_dialog.wasCanceled():
                progress_dialog.close()
                self.parent.statusbar.showMessage("3D calculation canceled", 3000)
                return

        # Complete preparation phase
        progress_dialog.setValue(total_files)
        progress_dialog.close()

        if not images:
            QtWidgets.QMessageBox.warning(self, "Warning", "No valid images found for 3D calculation")
            return

        # Stack all images into 3D volume
        volume = np.stack(images, axis=0)

        # Get scale factors
        dx = getattr(images_viewer, 'dx', 1.0)
        dy = getattr(images_viewer, 'dy', 1.0)
        dz = getattr(images_viewer, 'dz', 1.0)

        # Get or create mask (similar to 2D version)
        mask_3d = None
        if hasattr(images_viewer, 'mask_calcu') and images_viewer.mask_calcu is not None:
            if isinstance(images_viewer.mask_calcu, tuple) and isinstance(images_viewer.mask_calcu[0], list):
                # Handle case where mask_calcu is (label_dir, mask_flag)
                label_dir = images_viewer.mask_calcu[0]
                mask_flag = images_viewer.mask_calcu[1]

                # 为每个图像文件匹配对应的掩码文件
                mask_list = []
                for file_path in file_paths:
                    label_path = self.get_label_path(file_path, label_dir)
                    if label_path:
                        mask_2d = cv2.imread(label_path, cv2.IMREAD_GRAYSCALE)
                        # 确保是二维数组
                        if mask_2d is not None and len(mask_2d.shape) == 3:
                            # 如果是三维，只取一个通道
                            if mask_2d.shape[2] == 1:
                                mask_2d = mask_2d[:, :, 0]
                            else:
                                # 转换为灰度图
                                mask_2d = cv2.cvtColor(mask_2d, cv2.COLOR_BGR2GRAY)
                        # Apply mask flag
                        mask_2d = mask_2d if mask_flag else 255 - mask_2d
                        # 确保掩码尺寸与对应图像匹配
                        if mask_2d.shape[:2] != images[0].shape[:2]:
                            mask_2d = cv2.resize(mask_2d, (images[0].shape[1], images[0].shape[0]),
                                                 interpolation=cv2.INTER_NEAREST)
                        mask_list.append(mask_2d)
                    else:
                        # 如果找不到对应掩码，创建全白掩码
                        mask_2d = np.ones_like(images[0], dtype=np.uint8) * 255
                        mask_list.append(mask_2d)

                # 将掩码列表堆叠成3D掩码
                mask_3d = np.stack(mask_list, axis=0)

            elif isinstance(images_viewer.mask_calcu, tuple):
                # Handle case where mask_calcu is (mask, mask_flag)
                mask_2d = images_viewer.mask_calcu[0]
                mask_flag = images_viewer.mask_calcu[1]
                mask_2d = mask_2d if mask_flag else 255 - mask_2d
                # Ensure mask is the correct size and binary
                if mask_2d.shape[:2] != volume.shape[1:]:
                    mask_2d = cv2.resize(mask_2d, (volume.shape[2], volume.shape[1]),
                                         interpolation=cv2.INTER_NEAREST)
                # Replicate mask across all slices
                mask_3d = np.stack([mask_2d] * len(images), axis=0)
        else:
            # If no mask provided, create a default mask covering the entire volume
            mask_3d = np.ones_like(volume, dtype=np.uint8) * 255

        # Ensure mask is binary
        mask_3d = (mask_3d > 0).astype(np.uint8) * 255

        # Apply mask to volume
        masked_volume = np.where(mask_3d == 255, volume, 255)  # Set non-masked areas to max value

        # Binarize the volume for pore detection (assuming pores are represented by lower values)
        # In many cases, pores would be 0 values in the image
        binary_volume = (masked_volume == 0).astype(np.uint8)

        # Apply mask to binary volume
        masked_binary_volume = binary_volume * (mask_3d // 255)

        # Calculate total pore volume (voxels) - only within mask region
        pore_volume_voxels = np.count_nonzero(masked_binary_volume)

        # Calculate total volume of mask region
        mask_volume_voxels = np.count_nonzero(mask_3d == 255)

        # Calculate pore ratio (pore volume as proportion of mask volume)
        pore_ratio = pore_volume_voxels / mask_volume_voxels if mask_volume_voxels > 0 else 0

        # Calculate surface area using morphological operations
        from scipy import ndimage

        # Find surface voxels (pore voxels that have non-pore neighbors)
        structuring_element = np.ones((3, 3, 3))
        eroded_pores = ndimage.binary_erosion(masked_binary_volume, structure=structuring_element)
        surface_voxels = masked_binary_volume - eroded_pores

        # Calculate surface area (number of surface voxels)
        surface_area_voxels = np.count_nonzero(surface_voxels)

        # Calculate scaled values
        scaled_pore_volume = pore_volume_voxels * dx * dy * dz
        scaled_mask_volume = mask_volume_voxels * dx * dy * dz
        scaled_surface_area = surface_area_voxels * dx * dy  # Surface area per slice

        # Calculate additional metrics
        # Number of connected pore components
        labeled_pores, num_components = ndimage.label(masked_binary_volume)
        # Average pore size
        avg_pore_size = scaled_pore_volume / num_components if num_components > 0 else 0

        return_info = \
            f"pore_ratio: {pore_ratio:.6f}" + "\n" + \
            f"pore_volume: {pore_volume_voxels} voxels" + "\n" + \
            f"pore_surface_area: {surface_area_voxels} voxels^2" + "\n" + \
            f"total_volume: {mask_volume_voxels} voxels" + "\n" + \
            f"scaled_pore_volume: {scaled_pore_volume:.6f} μm³" + "\n" + \
            f"scaled_total_volume: {scaled_mask_volume:.6f} μm³" + "\n" + \
            f"scaled_surface_area: {scaled_surface_area:.6f} μm²" + "\n" + \
            f"num_pore_components: {num_components}" + "\n" + \
            f"avg_pore_size: {avg_pore_size:.6f} μm³" + "\n" + \
            f"scale_factors: dx: {dx:.3f} μm, dy: {dy:.3f} μm, dz: {dz:.3f} μm"

        # Show information dialog
        msg_box = QtWidgets.QMessageBox(self.parent)
        msg_box.setWindowTitle("3D Measurement Information")
        msg_box.setText(return_info)
        msg_box.exec_()

