"""相机设备枚举（Windows 下通过 wmi 探测可用摄像头）。"""

import wmi


def get_cameras_from_windows():
    """Get camera devices from Windows"""
    c = wmi.WMI()
    cameras = []

    for device in c.Win32_PnPEntity():
        if device.Name and ("camera" in device.Name.lower() or "webcam" in device.Name.lower()):
            cameras.append(device.Name)

    return cameras


def detect_available_cameras():
    """
    Detect available cameras in system
    :return: List of available camera indices
    """
    available = []
    available_cameras = get_cameras_from_windows()
    for i, name in enumerate(available_cameras):
        available.append(i)
    return available
