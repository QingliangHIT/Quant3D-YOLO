from PyQt5 import QtWidgets
from UI.viewer.viewerCamera import CameraWindow
from UI.viewer.viewerImage import ImageViewer  # Import new ImageViewer


class CustomTabBar(QtWidgets.QTabBar):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.setTabsClosable(True)  # Enable close button
        self.tabCloseRequested.connect(self.close_tab)

    def close_tab(self, index):
        """Close tab at index, ensure widget destroyed"""
        widget = self.parentWidget().widget(index)  # Get current tab widget
        self.parentWidget().removeTab(index)  # Remove tab
        if isinstance(widget, CameraWindow):
            widget.cleanup()  # Release camera resources
            for dock in [self.parent.dock_dict[i] for i in self.parent.camera_page_source]:
                if hasattr(dock, 'cleanup'):
                    dock.cleanup()
            # widget.deleteLater()  # Mark for deletion
            self.parent.action_toggle_camera_view.setChecked(False)
            self.parent.action_toggle_stereo_view.setChecked(False)
        if isinstance(widget, ImageViewer):  # Check if image page
            widget.cleanup()  # Release camera resources
            for dock in [self.parent.dock_dict[i] for i in self.parent.image_view_page_source]:
                if hasattr(dock, 'cleanup'):
                    dock.cleanup()
            self.parent.action_toggle_image_view.setChecked(False)


class CustomTabWidget(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(CustomTabBar(parent))  # Use custom TabBar