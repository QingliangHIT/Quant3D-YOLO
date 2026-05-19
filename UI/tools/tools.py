# image_viewer.py
import os

import cv2
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt
from .tool_plot_yolo import COLORS


def get_image_format_name(image_format):
    format_map = {
        QtGui.QImage.Format_Invalid: "Invalid",
        QtGui.QImage.Format_Mono: "Mono (1-bit)",
        QtGui.QImage.Format_MonoLSB: "Mono LSB",
        QtGui.QImage.Format_Indexed8: "Indexed8 (256 colors)",
        QtGui.QImage.Format_RGB32: "RGB32",
        QtGui.QImage.Format_ARGB32: "ARGB32",
        QtGui.QImage.Format_ARGB32_Premultiplied: "ARGB32 Premultiplied",
        QtGui.QImage.Format_RGB16: "RGB16",
        QtGui.QImage.Format_RGB444: "RGB444",
        QtGui.QImage.Format_RGB555: "RGB555",
        QtGui.QImage.Format_RGB666: "RGB666",
        QtGui.QImage.Format_RGB888: "RGB888",
        QtGui.QImage.Format_BGR30: "BGR30",
        QtGui.QImage.Format_A2BGR30_Premultiplied: "A2BGR30 Premultiplied",
        QtGui.QImage.Format_RGB30: "RGB30",
        QtGui.QImage.Format_A2RGB30_Premultiplied: "A2RGB30 Premultiplied",
        QtGui.QImage.Format_Alpha8: "Alpha8 (8-bit alpha)",
        QtGui.QImage.Format_Grayscale8: "Grayscale8 (8-bit)"
    }
    return format_map.get(image_format, f"Unknown Format ({image_format})")


