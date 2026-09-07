"""连拍参数设置对话框。"""

from PyQt5 import QtWidgets


class BurstSettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Burst Settings")
        self.layout = QtWidgets.QVBoxLayout(self)

        # Interval setting
        interval_layout = QtWidgets.QHBoxLayout()
        self.interval_label = QtWidgets.QLabel("⏱️ Interval(s):")
        self.spin_burst_interval = QtWidgets.QSpinBox()
        self.spin_burst_interval.setRange(1, 60)
        self.spin_burst_interval.setValue(1)
        interval_layout.addWidget(self.interval_label)
        interval_layout.addWidget(self.spin_burst_interval)

        # Count setting
        count_layout = QtWidgets.QHBoxLayout()
        self.count_label = QtWidgets.QLabel("📷 Count:")
        self.spin_burst_count = QtWidgets.QSpinBox()
        self.spin_burst_count.setRange(0, 1000)
        self.spin_burst_count.setValue(0)
        count_layout.addWidget(self.count_label)
        count_layout.addWidget(self.spin_burst_count)

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.layout.addLayout(interval_layout)
        self.layout.addLayout(count_layout)
        self.layout.addWidget(button_box)

    def get_settings(self):
        return self.spin_burst_interval.value(), self.spin_burst_count.value()
