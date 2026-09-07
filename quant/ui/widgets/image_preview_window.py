"""独立的图像预览窗口。"""

from PyQt5 import QtWidgets, QtCore


class ImageViewerWindow(QtWidgets.QMainWindow):
    def __init__(self, pixmap=None):
        super().__init__()
        self.setWindowTitle("Image preview")
        self.resize(600, 400)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        self.view = QtWidgets.QLabel()
        self.view.setPixmap(pixmap)
        self.view.setAlignment(QtCore.Qt.AlignCenter)
        self.view.setScaledContents(True)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(self.view)
        scroll_area.setWidgetResizable(True)

        layout.addWidget(scroll_area)
        self.setCentralWidget(central)
