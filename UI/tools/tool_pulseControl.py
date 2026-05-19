from datetime import datetime

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, QSettings, QTimer
from PyQt5.QtChart import QLineSeries, QChart, QChartView, QValueAxis
import serial
from PyQt5.QtWidgets import QButtonGroup
from serial.tools import list_ports
import json
import os
import shutil
import time


class PulseControlDialog(QtWidgets.QDialog):
    CONFIG_FILE = "pulse_config.json"
    HISTORY_FILE = "command_history.json"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pulse Controller")
        self.setWindowIcon(QtGui.QIcon("icon/pulse.svg"))
        self.resize(800, 600)

        # Init variables
        # self.step_scale = {'KEEP': 100, 'PULSE': 100, }  # step parameter
        self.variable_value = {'KEEP': 3000, 'PULSE': 400, 'STEP': 100, 'ENA': False}
        self.current_variable = 'PULSE'
        self.ser_list = {}  # Serial connection objects
        self.available_ports = []  # Available ports list
        self.history_items = []
        self.chart_series = {}
        self.theme = "Light"

        # Load config
        self.load_config()
        self.load_history()

        # Init UI
        self.init_ui()
        self.connect_signals()
        self.update_port_list()  # Auto detect ports

        # Start timer for chart updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_chart)
        self.timer.start(1000)  # Update every second

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # Create menu bar
        self.create_menus(main_layout)

        # Main content area
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)

        # Top control area
        control_widget = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout(control_widget)

        # Left control panel
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)

        # current variable selection
        # current variable selection
        # var_group = QtWidgets.QGroupBox("variable control")
        # var_layout = QtWidgets.QHBoxLayout(var_group)

        # left_layout.addWidget(var_group)

        # Serial port settings
        port_group = QtWidgets.QGroupBox("Serial Connection")
        port_layout = QtWidgets.QVBoxLayout(port_group)

        port_row = QtWidgets.QHBoxLayout()
        self.port_combo = QtWidgets.QComboBox()
        self.refresh_port_btn = QtWidgets.QPushButton("Refresh")
        port_row.addWidget(QtWidgets.QLabel("Port:"))
        port_row.addWidget(self.port_combo)
        port_row.addWidget(self.refresh_port_btn)
        port_layout.addLayout(port_row)

        baudrate_row = QtWidgets.QHBoxLayout()
        baudrate_row.addWidget(QtWidgets.QLabel("Baudrate:"))
        self.baudrate_combo = QtWidgets.QComboBox()
        self.baudrate_combo.addItems(["2400", "9600", "115200"])
        self.baudrate_combo.setCurrentText("2400")
        baudrate_row.addWidget(self.baudrate_combo)
        port_layout.addLayout(baudrate_row)

        multi_select_row = QtWidgets.QHBoxLayout()
        self.multi_select_checkbox = QtWidgets.QCheckBox("Multi-select mode")
        multi_select_row.addWidget(self.multi_select_checkbox)
        port_layout.addLayout(multi_select_row)

        port_ctrl_row = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        port_ctrl_row.addWidget(self.start_btn)
        port_ctrl_row.addWidget(self.stop_btn)
        port_layout.addLayout(port_ctrl_row)

        left_layout.addWidget(port_group)

        # Step control
        step_group = QtWidgets.QGroupBox("Step control")
        step_layout = QtWidgets.QVBoxLayout(step_group)
        var_layout = QtWidgets.QHBoxLayout()

        self.var_button_group = QButtonGroup(self)
        self.var_buttons = {}
        self.var_labels = {}

        for var in ["KEEP", "PULSE", "STEP", "ENA"]:
            btn = QtWidgets.QPushButton(var.capitalize())
            btn.setCheckable(True)
            btn.setFixedSize(80, 30)
            label = QtWidgets.QLabel(f"{self.variable_value[var]}")

            self.var_button_group.addButton(btn)
            self.var_buttons[var] = btn
            self.var_labels[var] = label

            var_layout.addWidget(btn)
            var_layout.addWidget(label)

        self.var_button_group.setExclusive(True)
        self.var_button_group.buttonClicked.connect(self.on_var_button_clicked)

        # Default select first variable
        self.var_buttons["PULSE"].setChecked(True)
        var_layout.addStretch()
        var_layout = QtWidgets.QHBoxLayout()

        self.var_button_group = QButtonGroup(self)
        self.var_buttons = {}
        self.var_labels = {}

        for var in ["KEEP", "PULSE", "STEP", "ENA"]:
            btn = QtWidgets.QPushButton(var.capitalize())
            btn.setCheckable(True)
            btn.setFixedSize(80, 30)
            label = QtWidgets.QLabel(f"{self.variable_value[var]}")
            label.setFixedSize(80, 30)

            self.var_button_group.addButton(btn)
            self.var_buttons[var] = btn
            self.var_labels[var] = label

            var_layout.addWidget(btn)
            var_layout.addWidget(label)

        self.var_button_group.setExclusive(True)
        self.var_button_group.buttonClicked.connect(self.on_var_button_clicked)

        # Default select first variable
        self.var_buttons["KEEP"].setChecked(True)
        var_layout.addStretch()
        step_layout.addLayout(var_layout)

        self.step_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.step_slider.setMinimum(0)
        self.step_slider.setMaximum(20000)
        self.step_slider.setValue(self.variable_value[self.current_variable])
        self.step_label = QtWidgets.QLabel(f"Step: {self.step_slider.value()}")

        step_ctrl_row = QtWidgets.QHBoxLayout()
        step_ctrl_row.addWidget(QtWidgets.QLabel("Step adjust:"))
        step_ctrl_row.addWidget(self.step_slider)
        step_ctrl_row.addWidget(self.step_label)
        step_layout.addLayout(step_ctrl_row)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_left = QtWidgets.QPushButton("← Expand")
        self.btn_right = QtWidgets.QPushButton("→ Shrink")
        self.btn_up = QtWidgets.QPushButton("↑ Increase step")
        self.btn_down = QtWidgets.QPushButton("↓ Decrease step")
        btn_layout.addWidget(self.btn_left)
        btn_layout.addWidget(self.btn_right)
        btn_layout.addWidget(self.btn_up)
        btn_layout.addWidget(self.btn_down)
        step_layout.addLayout(btn_layout)

        left_layout.addWidget(step_group)

        # Right history panel
        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)

        history_group = QtWidgets.QGroupBox("Command History")
        history_layout = QtWidgets.QVBoxLayout(history_group)

        self.history_combo = QtWidgets.QComboBox()
        self.history_combo.setEditable(True)
        self.history_combo.setMaxCount(20)
        self.history_combo.addItems(self.history_items)
        history_layout.addWidget(self.history_combo)

        cmd_row = QtWidgets.QHBoxLayout()
        self.send_btn = QtWidgets.QPushButton("Send")
        self.clear_btn = QtWidgets.QPushButton("Clear")
        cmd_row.addWidget(self.send_btn)
        cmd_row.addWidget(self.clear_btn)
        history_layout.addLayout(cmd_row)

        right_layout.addWidget(history_group)

        # Chart display
        chart_group = QtWidgets.QGroupBox("Variable Monitor")
        chart_layout = QtWidgets.QVBoxLayout(chart_group)

        self.setup_chart()
        chart_layout.addWidget(self.chart_view)

        right_layout.addWidget(chart_group)

        # Status info
        status_group = QtWidgets.QGroupBox("Status info")
        status_layout = QtWidgets.QHBoxLayout(status_group)

        self.status_indicator = QtWidgets.QLabel("●")
        self.status_indicator.setStyleSheet("color: red;")
        self.status_indicator.setFont(QtGui.QFont("Arial", 12))
        status_layout.addWidget(QtWidgets.QLabel("Connection:"))
        status_layout.addWidget(self.status_indicator)
        status_layout.addStretch()

        right_layout.addWidget(status_group)

        # Control panel
        control_layout.addWidget(left_panel, stretch=2)
        control_layout.addWidget(right_panel, stretch=1)
        content_layout.addWidget(control_widget, stretch=1)

        # Log output
        log_group = QtWidgets.QGroupBox("Log output")
        log_layout = QtWidgets.QVBoxLayout(log_group)

        self.log_output = QtWidgets.QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)

        content_layout.addWidget(log_group, stretch=1)

        main_layout.addWidget(content_widget)

    def on_var_button_clicked(self, button):
        for var, btn in self.var_buttons.items():
            if btn is button:
                # index = list(self.var_buttons.keys()).index(var)
                self.current_variable = var
                self.update_current_variable(var)

                # Update all labels
                for v, b in self.var_buttons.items():
                    self.var_labels[v].setText(str(self.variable_value[v]))
                break

    def create_menus(self, layout):
        menu_bar = QtWidgets.QMenuBar(self)

        # File menu
        file_menu = menu_bar.addMenu("File")
        save_config_action = file_menu.addAction("Save Config")
        load_config_action = file_menu.addAction("Load Config")
        backup_config_action = file_menu.addAction("Backup Config")
        file_menu.addSeparator()
        export_log_action = file_menu.addAction("Export Log")
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")

        # Tools menu
        tool_menu = menu_bar.addMenu("Tools")
        clear_log_action = tool_menu.addAction("Clear Log")
        reset_step_action = tool_menu.addAction("Reset Step")
        tool_menu.addSeparator()
        send_test_action = tool_menu.addAction("Send Test Command")

        # Settings menu
        setting_menu = menu_bar.addMenu("Settings")
        theme_group = QtWidgets.QActionGroup(self)
        light_theme_action = setting_menu.addAction("Light Theme")
        light_theme_action.setCheckable(True)
        dark_theme_action = setting_menu.addAction("Dark Theme")
        dark_theme_action.setCheckable(True)
        theme_group.addAction(light_theme_action)
        theme_group.addAction(dark_theme_action)
        if self.theme == "Light":
            light_theme_action.setChecked(True)
        else:
            dark_theme_action.setChecked(True)
        setting_menu.addActions([light_theme_action, dark_theme_action])

        # Help menu
        help_menu = menu_bar.addMenu("Help")
        about_action = help_menu.addAction("About")

        layout.insertWidget(0, menu_bar)

    def connect_signals(self):
        # self.var_combo.currentIndexChanged.connect(self.update_current_variable)
        # self.step_slider.valueChanged.connect(lambda v: self.step_label.setText(f"{v}"))
        self.step_slider.valueChanged.connect(self.on_step_slider_changed)
        self.btn_left.clicked.connect(lambda: self.send_pulse(0))
        self.btn_right.clicked.connect(lambda: self.send_pulse(1))
        self.btn_up.clicked.connect(self.increase_step_rate)
        self.btn_down.clicked.connect(self.decrease_step_rate)
        self.send_btn.clicked.connect(self.send_custom_command)
        self.clear_btn.clicked.connect(self.clear_log)
        self.start_btn.clicked.connect(self.start_connection)
        self.stop_btn.clicked.connect(self.stop_connection)
        self.refresh_port_btn.clicked.connect(self.update_port_list)

        # Shortcuts
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Enter"), self, lambda: self.send_custom_command())
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+W"), self, lambda: self.send_pulse(1))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, lambda: self.send_pulse(0))

    def on_step_slider_changed(self, value):
        current_var = self.current_variable

        # Update QLabel display
        self.step_label.setText(f"{value}")

        # Optional: Update QLabel next to button
        self.variable_value[current_var] = value
        self.var_labels[current_var].setText(f"{self.variable_value[current_var]}")

    def setup_chart(self):
        """Init chart"""
        self.chart = QChart()
        # self.chart.setTitle("variation trend of variable values")

        axis_x = QValueAxis()
        axis_x.setTitleText("Time (s)")
        axis_x.setTickCount(6)
        axis_x.setRange(0, 60)

        axis_y = QValueAxis()
        axis_y.setTitleText("数值")
        axis_y.setRange(0, 1000)

        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignLeft)

        for var in ["KEEP", "PULSE"]:
            series = QLineSeries()
            series.setName(var)
            series.append(0, self.variable_value[var])
            self.chart.addSeries(series)
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
            self.chart_series[var] = series

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QtGui.QPainter.Antialiasing)

    def update_chart(self):
        """Update chart data"""
        for var, series in self.chart_series.items():
            points = series.pointsVector()
            if len(points) > 60:  # Keep last 60 points
                points = points[1:]

            # Add new point
            new_point = QtCore.QPointF(len(points), self.variable_value[var])
            points.append(new_point)

            series.replace(points)

    def log(self, message):
        """Add log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")

    def update_current_variable(self, val):
        """Update current variable"""
        if val in {"KEEP", "PULSE", "STEP"}:
            self.var_labels[val].setText(f"{self.variable_value[val]}")
            self.step_slider.setValue(self.variable_value[val])
            if val in {"KEEP"}:
                self.log(f"{val} updated: {self.variable_value[val]}")
                if self.multi_select_checkbox.isChecked():
                    # Multi-select mode: send to all connected devices
                    for port, ser in self.ser_list.items():
                        if ser and ser.is_open:
                            command = f"set -k {self.variable_value[val]}\r\n"
                            ser.write(command.encode('gbk'))
                else:
                    # Single-select mode: send to current device
                    selected_port = self.port_combo.currentText()
                    if selected_port in self.ser_list:
                        ser = self.ser_list[selected_port]
                        if ser and ser.is_open:
                            command = f"set -k {self.variable_value[val]}\r\n"
                            ser.write(command.encode('gbk'))
        elif val in {'ENA'}:
            self.variable_value[val] = not self.variable_value[val]
            self.var_labels[val].setText(f"{self.variable_value[val]}")
            self.log(f"{val} updated: {self.variable_value[val]}")
            if self.multi_select_checkbox.isChecked():
                # Multi-select mode: send to all connected devices
                for port, ser in self.ser_list.items():
                    if ser and ser.is_open:
                        command = f"set -e {int(self.variable_value[val])}\r\n"
                        ser.write(command.encode('gbk'))
            else:
                # Single-select mode: send to current device
                selected_port = self.port_combo.currentText()
                if selected_port in self.ser_list:
                    ser = self.ser_list[selected_port]
                    if ser and ser.is_open:
                        command = f"set -e {int(self.variable_value[val])}\r\n"
                        ser.write(command.encode('gbk'))

    def send_pulse(self, direction):
        """Send pulse command"""
        pulse_value = self.variable_value['PULSE']
        self.log(f"Send pulse: direction={direction}, value={pulse_value}")

        if self.multi_select_checkbox.isChecked():
            # Multi-select mode: send to all connected devices
            for port, ser in self.ser_list.items():
                if ser and ser.is_open:
                    command = f"pulse {direction} {pulse_value}\r\n"
                    ser.write(command.encode('gbk'))
        else:
            # Single-select mode: send to current device
            selected_port = self.port_combo.currentText()
            if selected_port in self.ser_list:
                ser = self.ser_list[selected_port]
                if ser and ser.is_open:
                    command = f"pulse {direction} {pulse_value}\r\n"
                    ser.write(command.encode('gbk'))

    def increase_step_rate(self):
        """Increase step"""
        idx = self.current_variable
        if idx in {'KEEP', 'PULSE'}:
            # self.variable_value[idx] += 10 ** self.variable_value['STEP']
            self.variable_value[idx] += self.variable_value['STEP']
            self.step_slider.setValue(self.variable_value[idx])
            self.log(f"({idx}) increased to: {self.variable_value[idx]}")

    def decrease_step_rate(self):
        """Decrease step"""
        idx = self.current_variable
        if idx in {'KEEP', 'PULSE'}:
            self.variable_value[idx] -= self.variable_value['STEP']
            self.step_slider.setValue(self.variable_value[idx])
            self.log(f"({idx}) decreased to: {self.variable_value[idx]}")

    def send_custom_command(self):
        """Send custom command"""
        cmd = self.history_combo.currentText().strip()
        if not cmd:
            return

        self.log(f"Sending command: {cmd}")

        if self.multi_select_checkbox.isChecked():
            # Multi-select mode: send to all connected devices
            for port, ser in self.ser_list.items():
                if ser and ser.is_open:
                    ser.write(cmd.encode('gbk') + b"\r\n")
        else:
            # Single-select mode: send to current device
            selected_port = self.port_combo.currentText()
            if selected_port in self.ser_list:
                ser = self.ser_list[selected_port]
                if ser and ser.is_open:
                    ser.write(cmd.encode('gbk') + b"\r\n")
                    response = receive_data_with_timeout(ser)
                    if response:
                        self.log(f"Received: {response}")
                        # return response
        # Update history
        if cmd not in self.history_items:
            self.history_items.append(cmd)
            self.history_combo.addItem(cmd)
            if len(self.history_items) > 20:
                self.history_items.pop(0)
                self.history_combo.removeItem(0)
            self.save_history()

    def start_connection(self):
        """Start serial connection"""
        selected_port = self.port_combo.currentText()
        if not selected_port:
            self.log("Please select a port first.")
            return

        try:
            # Get baudrate
            baudrate = int(self.baudrate_combo.currentText())

            # Create serial connection
            ser = serial.Serial(
                port=selected_port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_ODD,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )

            send_command(ser, "run 11832\r\n")
            time.sleep(0.5)  # Wait for command processing
            if receive_response(ser, "$ready 11832$"):
                # Store connection
                self.ser_list[selected_port] = ser
            else:
                ser.close()
                self.log(f"Failed to connect: {selected_port}")
                return

            self.log(f"Connected to port: {selected_port}")
            self.status_indicator.setStyleSheet("color: green;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            if ser and ser.is_open:
                ser.write('get k'.encode('gbk') + b"\r\n")
                response = receive_data_with_timeout(ser)
                if response:
                    keep_value = int(response.split(': ')[1])
                    self.log(f"Current keep value: {keep_value}")
                    self.variable_value['KEEP'] = keep_value
                    self.var_labels['KEEP'].setText(f"{keep_value}")
                ser.write('get e'.encode('gbk') + b"\r\n")
                response = receive_data_with_timeout(ser)
                if response:
                    ENA_status = response.split(': ')[1].startswith('true')
                    self.log(f"Current ENA status: {ENA_status}")
                    self.variable_value['ENA'] = ENA_status
                    self.var_labels['ENA'].setText(f"{ENA_status}")
                # self.update_current_variable('KEEP')

        except Exception as e:
            self.log(f"Connection failed: {str(e)}")
            self.status_indicator.setStyleSheet("color: red;")

    def stop_connection(self):
        """Stop connection"""
        selected_port = self.port_combo.currentText()
        if selected_port in self.ser_list:
            ser = self.ser_list[selected_port]
            if ser and ser.is_open:
                ser.close()
            del self.ser_list[selected_port]

        self.log("Port disconnected.")
        self.status_indicator.setStyleSheet("color: red;")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def update_port_list(self):
        """Update available ports list"""
        self.port_combo.clear()
        self.available_ports = [port.device for port in list_ports.comports()]

        if self.available_ports:
            self.port_combo.addItems(self.available_ports)
            #  Restore previous selection if available
            if hasattr(self, 'last_selected_port') and self.last_selected_port in self.available_ports:
                index = self.port_combo.findText(self.last_selected_port)
                if index >= 0:
                    self.port_combo.setCurrentIndex(index)
        else:
            self.port_combo.addItem("No ports available")

    def load_config(self):
        """Load saved config"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    # self.step_scale = config.get("step_scale", {'KEEP': 100, 'PULSE': 100, 'STEP': 1})
                    # self.variable_value = config.get("variable_value", {'KEEP': 1000, 'PULSE': 400, 'STEP': 100, 'ENA': False})
                    self.last_selected_port = config.get("last_selected_port", "")
                    self.theme = config.get("theme", "Light")
            except Exception as e:
                self.log(f"Load config failed: {e}")

    def save_config(self):
        """Save current config"""
        config = {
            # "step_scale": self.step_scale,
            # "variable_value": self.variable_value,
            "last_selected_port": self.port_combo.currentText(),
            "theme": self.theme
        }
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            self.log(f"Save config failed: {e}")

    def load_history(self):
        """Load command history"""
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE, 'r') as f:
                    self.history_items = json.load(f)
            except Exception as e:
                self.log(f"Load history failed: {e}")

    def save_history(self):
        """Save command history"""
        try:
            with open(self.HISTORY_FILE, 'w') as f:
                json.dump(self.history_items, f)
        except Exception as e:
            self.log(f"Save history failed: {e}")

    def clear_log(self):
        """Clear log"""
        self.log_output.clear()
        self.log("Log cleared")

    def change_theme(self, theme):
        """Change theme"""
        self.theme = theme
        if theme == "Light":
            self.setStyleSheet("QWidget { background-color: white; color: black; }")
        elif theme == "Dark":
            self.setStyleSheet("QWidget { background-color: #2b2b2b; color: #e0e0e0; }")
        self.save_config()

    def closeEvent(self, event):
        """Save config on close"""
        self.save_config()
        self.save_history()

        # Close all serial connections
        for port, ser in self.ser_list.items():
            if ser and ser.is_open:
                ser.close()

        super().closeEvent(event)


def send_command(com, command):
    com.write(command.encode('gbk'))


def receive_response(com, expected_response):
    while com.in_waiting > 0:
        data = com.read(com.in_waiting).decode('gbk')
        if expected_response in data:
            return True
    return False


def receive_data(com):
    if com.in_waiting > 0:
        data = com.read(com.in_waiting).decode('gbk')
        return data
    return None


def receive_data_with_timeout(com, timeout=5, check_interval=0.1):
    start_time = time.time()
    last_bytes_in_waiting = 0
    data = ""
    while time.time() - start_time < timeout:
        if com.in_waiting > 0:
            new_data = com.read(com.in_waiting).decode('gbk')
            data += new_data
            last_bytes_in_waiting = com.in_waiting
        else:
            time.sleep(0.1)

        # Check if bytes change in check_interval
        time.sleep(check_interval)
        if com.in_waiting == last_bytes_in_waiting:
            return data

    return data


# Run as main program
if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = PulseControlDialog()
    window.show()
    sys.exit(app.exec_())
