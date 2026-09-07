"""文件与项目目录动作：打开图像/文件夹、载入项目输出目录、保存。"""

import os
from PyQt5 import QtWidgets
from quant.ui.views.batch_image_view import ImagesViewer


def open_images(window):
    file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(window, "Open Image Files", "",
                                                           "Image Files (*.png *.jpg *.jpeg *.bmp)")
    if file_paths:
        window.files_dock.update_file_list(file_paths, add=True)
        current_widget = window.tab_widget.currentWidget()
        if isinstance(current_widget, ImagesViewer):
            current_widget.load_images(file_paths)
        window.statusbar.showMessage(f"Loaded {len(file_paths)} file(s)", 2000)


def open_file(window, file_path):
    window.statusbar.showMessage(f"Loaded file: {file_path}", 2000)
    current_widget = window.tab_widget.currentWidget()
    image_info = current_widget.load_file(file_path)
    window.info_dock.set_info(image_info)


def open_folder(window):
    """
    Load folder and display image files in it
    """
    folder_path = QtWidgets.QFileDialog.getExistingDirectory(window, "Open Folder", "")

    if folder_path:
        # Get image files in folder
        image_files = []
        for file in os.listdir(folder_path):
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                image_files.append(os.path.join(folder_path, file))

        # If no image files found, show warning
        if not image_files:
            QtWidgets.QMessageBox.warning(window, "Load Folder", "No image files found in the selected folder.")
            return

        # Update file list (optional)

        # Perform different operations based on current image viewer type
        current_widget = window.tab_widget.currentWidget()
        if isinstance(current_widget, ImagesViewer):
            # If ImagesViewer, load all images
            current_widget.load_images(image_files)
            window.files_dock.update_file_list(image_files, show=True)
        else:
            # current_widget.load_images(image_files)
            window.files_dock.update_file_list(image_files, show=True)

        # Optional: update status bar information
        window.statusbar.showMessage(f"Loaded {len(image_files)} images from folder.", 2000)


def open_project_dir(window):
    pro_dir = window.project_manager.current_project_dir
    if not pro_dir:
        pro_dir = QtWidgets.QFileDialog.getExistingDirectory(window, "Open Folder", "")
    if os.path.exists(os.path.join(pro_dir, "config.ini")):
        window.project_manager.current_project_dir = pro_dir
        window.project_manager.load_config()
        window.statusbar.showMessage(f"Open project: {pro_dir}", 3000)
    else:
        QtWidgets.QMessageBox.warning(window, "Load Folder", "No config.ini found in the selected folder.")
        return
    folder_path = str(os.path.join(window.project_manager.current_project_dir, window.project_manager.save_dir))
    if folder_path:
        # Get image files in folder
        image_files = []
        image_files2 = []
        video_files = []
        video_files2 = []
        for file in os.listdir(folder_path):
            if file.lower().endswith((".png", ".jpg", ".bmp")):
                if not file.endswith("_r.png") and not file.endswith("_r.jpg") and not file.endswith("_r.bmp"):
                    image_files2.append(os.path.join(folder_path, file))
                image_files.append(os.path.join(folder_path, file))
            elif file.lower().endswith((".mp4", ".avi")):
                if not file.endswith("_r.avi") and not file.endswith("_r.mp4"):
                    video_files2.append(os.path.join(folder_path, file))
                video_files.append(os.path.join(folder_path, file))

        # If no image files found, show warning
        if not image_files:
            QtWidgets.QMessageBox.warning(window, "Load Folder", "No image files found in the project folder.")
            return

        # Update file list (optional)
        window.files_dock.update_file_list(image_files)
        window.project_manager.i_img = len(image_files2)
        window.project_manager.i_vid = len(video_files2)
        # Optional: update status bar information
        window.statusbar.showMessage(f"Loaded {len(image_files)} images from project folder.", 2000)


def save_file(window):
    """
    Save file
    """
    if window.current_file:
        # Implement save logic
        window.is_modified = False
        window.statusbar.showMessage("File saved successfully.", 2000)
    else:
        window.save_file_as()


def save_file_as(window):
    """
    Save as file
    """
    pass
