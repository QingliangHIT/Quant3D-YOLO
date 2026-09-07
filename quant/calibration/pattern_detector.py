"""标定板图案检测：棋盘格 / 圆点网格角点提取。"""

import cv2


class CalibrationDetector:
    def __init__(self, inner_corners=(7, 7), pattern_type='circles'):
        """
        初始化标定检测器
        :param inner_corners: 棋盘格内部角点数量 (width, height)
        :param pattern_type: 检测类型 ('chessboard', 'circles', 'asymmetric_circles')
        """
        self.inner_corners = inner_corners
        self.pattern_type = pattern_type
        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    def detect(self, image):
        """
        根据 pattern_type 自动选择检测方法
        :param image: 输入图像
        :return: 是否检测成功，以及绘制了角点的图像
        """
        if self.pattern_type == 'chessboard':
            return self.detect_chessboard(image)
        elif self.pattern_type == 'circles':
            return self.detect_circles_grid(image, flags=cv2.CALIB_CB_SYMMETRIC_GRID)
        elif self.pattern_type == 'asymmetric_circles':
            return self.detect_circles_grid(image, flags=cv2.CALIB_CB_ASYMMETRIC_GRID)
        else:
            raise ValueError(f"Unsupported pattern type: {self.pattern_type}")

    def detect_chessboard(self, image):
        """检测棋盘格"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, self.inner_corners, None)
        if ret:
            # 角点精检测
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), self.criteria)
            cv2.drawChessboardCorners(image, self.inner_corners, corners, ret)
        return ret, image

    def detect_circles_grid(self, image, flags=0):
        """检测圆形网格（对称或非对称）"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findCirclesGrid(gray, self.inner_corners, flags=flags)
        if ret:
            cv2.drawChessboardCorners(image, self.inner_corners, corners, ret)
        return ret, image
