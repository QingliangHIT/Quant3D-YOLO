"""应用引导：创建 QApplication 与主窗口。"""
from __future__ import annotations

import sys
import traceback

from PyQt5 import QtCore, QtGui, QtWidgets

from quant import __app_name__
from quant.core.config import UI_CONFIG
from quant.core.paths import icon_path


def _log_exception(exc_type, exc_value, exc_tb) -> None:
    """打印未捕获异常的完整堆栈。"""
    stream = sys.stderr or sys.__stderr__
    if stream is None:  # 打包成无控制台的 exe 时可能没有 stderr
        return
    stream.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    stream.flush()


def _install_excepthook() -> None:
    """PyQt5 5.5+ 默认在槽内未捕获异常时 qFatal 终止进程；改为记录后继续运行。

    GUI 应用里单个槽的意外错误不应带走整个软件，但堆栈必须留在控制台/日志里。
    """
    sys.excepthook = _log_exception


def run(argv=None) -> int:
    """启动 GUI，返回退出码。"""
    from quant.ui.shell.main_window import MainWindow

    _install_excepthook()
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    app = QtWidgets.QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName(__app_name__)
    app.setOrganizationName(__app_name__)
    app.setWindowIcon(QtGui.QIcon(icon_path("SOFT.ico")))

    try:
        window = MainWindow()
    except Exception:  # noqa: BLE001 - 装配失败时给出可见提示，而不是无声退出
        traceback.print_exc()
        QtWidgets.QMessageBox.critical(
            None, "Startup Failed", "Failed to build the main window, see console output for details."
        )
        return 1

    window.resize(*UI_CONFIG.window_size)
    window.setMinimumSize(*UI_CONFIG.min_window_size)
    window.show()
    return app.exec_()
