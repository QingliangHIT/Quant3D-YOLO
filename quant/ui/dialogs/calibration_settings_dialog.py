"""标定参数设置对话框（图案类型、行列数）。"""

from PyQt5 import QtWidgets


class CalibrationSettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibration Settings")

        layout = QtWidgets.QFormLayout(self)

        # 内角数量输入
        self.inner_corners_width = QtWidgets.QSpinBox()
        self.inner_corners_width.setRange(1, 20)
        self.inner_corners_width.setValue(7)
        self.inner_corners_height = QtWidgets.QSpinBox()
        self.inner_corners_height.setRange(1, 20)
        self.inner_corners_height.setValue(7)
        layout.addRow("Inner Corners (Width)", self.inner_corners_width)
        layout.addRow("Inner Corners (Height)", self.inner_corners_height)

        # 检测类型选择
        self.pattern_type_combo = QtWidgets.QComboBox()
        self.pattern_type_combo.addItems([
            'circles',  # 圆形网格
            'chessboard',  # 棋盘格
            'asymmetric_circles'  # 非对称圆形网格
        ])
        layout.addRow("Detection Type", self.pattern_type_combo)

        # 确认/取消按钮
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_settings(self):
        """返回当前面板上的标定参数。"""
        return {
            'inner_corners': (self.inner_corners_width.value(), self.inner_corners_height.value()),
            'pattern_type': self.pattern_type_combo.currentText(),
        }
