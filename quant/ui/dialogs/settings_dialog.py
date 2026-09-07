"""全局设置对话框：任务类型、显示开关、缓存策略等。"""

from PyQt5 import QtWidgets, QtCore, QtGui
from quant.core.paths import icon_path


class SettingsDialog(QtWidgets.QDialog):
    theme_changed = QtCore.pyqtSignal(str)
    language_changed = QtCore.pyqtSignal(str)
    left_camera_changed = QtCore.pyqtSignal(int)     # Camera index signal
    mask_opacity_changed = QtCore.pyqtSignal(float)  # mask opacity change signal

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowIcon(QtGui.QIcon(icon_path("Settings.ico")))
        self._last_values = {
            'theme': 'Light',
            'language': 'Chinese',
            'left_camera': 0,
            'mask_opacity': 0.5,
        }
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Theme Settings
        theme_group = QtWidgets.QGroupBox("Theme Settings")
        theme_layout = QtWidgets.QVBoxLayout()
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # Language Settings
        language_group = QtWidgets.QGroupBox("Language Settings")
        language_layout = QtWidgets.QVBoxLayout()
        self.language_combo = QtWidgets.QComboBox()
        self.language_combo.addItems(["Chinese", "English"])
        language_layout.addWidget(self.language_combo)
        language_group.setLayout(language_layout)
        layout.addWidget(language_group)

        # Camera Settings
        camera_group = QtWidgets.QGroupBox("Camera Settings")
        camera_layout = QtWidgets.QGridLayout()

        # Camera
        self.left_camera_combo = QtWidgets.QComboBox()
        camera_layout.addWidget(QtWidgets.QLabel("Camera:"), 0, 0)
        camera_layout.addWidget(self.left_camera_combo, 0, 1)

        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)

        # Mask Opacity Settings (New)
        mask_group = QtWidgets.QGroupBox("Mask Settings")
        mask_layout = QtWidgets.QVBoxLayout()

        self.mask_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.mask_slider.setMinimum(0)
        self.mask_slider.setMaximum(100)
        self.mask_slider.setValue(50)  # Default 0.5 opacity
        self.mask_label = QtWidgets.QLabel(f"Opacity: {self.mask_slider.value()}%")

        self.mask_slider.valueChanged.connect(lambda v: self.mask_label.setText(f"Opacity: {v}%"))

        mask_layout.addWidget(self.mask_label)
        mask_layout.addWidget(self.mask_slider)
        mask_group.setLayout(mask_layout)
        layout.addWidget(mask_group)

        # Apply Button
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(self.apply_settings)
        layout.addWidget(apply_button)

    def set_available_cameras(self, available_indices):
        """ Set available camera list """
        self.left_camera_combo.clear()
        if available_indices is None:
            return
        for idx in available_indices:
            self.left_camera_combo.addItem(f"Camera {idx}", userData=idx)

        # Select first by default
        if len(available_indices) > 0:
            self.left_camera_combo.setCurrentIndex(0)

    def apply_settings(self):
        selected_theme = self.theme_combo.currentText()
        selected_language = self.language_combo.currentText()
        selected_left_camera = self.left_camera_combo.currentData()
        mask_opacity = self.mask_slider.value() / 100.0  # Convert to float [0.0 - 1.0]

        QtWidgets.QMessageBox.information(
            self,
            "Settings Applied",
            f"Theme: {selected_theme}\nLanguage: {selected_language}\nCamera: {selected_left_camera}\nMask Opacity: {mask_opacity:.2f}"
        )

        # Only emit signals when values change
        if selected_theme != self._last_values['theme']:
            self.theme_changed.emit(selected_theme)
            self._last_values['theme'] = selected_theme

        if selected_language != self._last_values['language']:
            self.language_changed.emit(selected_language)
            self._last_values['language'] = selected_language

        if selected_left_camera != self._last_values['left_camera']:
            self.left_camera_changed.emit(selected_left_camera)
            self._last_values['left_camera'] = selected_left_camera

        if mask_opacity != self._last_values['mask_opacity']:
            self.mask_opacity_changed.emit(mask_opacity)
            self._last_values['mask_opacity'] = mask_opacity
