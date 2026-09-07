"""相机标定：角点检测、单目/双目标定与参数持久化。"""

import glob
import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from tqdm import tqdm


class CameraCalibrator:
    def __init__(self, pattern_size=(7, 7), square_size=40, image_dir=None, detect_shape='circles', detect_num=1000,
                 shuffle=False, filter_files=False, gen_detector=False):
        self.filter_files = filter_files
        self.detect_shape = detect_shape
        self.pattern_size = pattern_size
        self.square_size = square_size
        self.detect_num = detect_num
        self.shuffle = shuffle
        self.obj_points = []
        self.img_points = []
        self.image_paths = None
        self.image_paths_test = None
        self.camera_matrix_left = None
        self.camera_matrix_right = None
        self.dist_coeffs_left = None
        self.dist_coeffs_right = None
        self.imageSize = None
        self.detector = None
        self.ret = None
        self.camera_matrix = None
        self.dist_coeffs = None

        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        self.image_dir = image_dir
        if gen_detector:
            self._generate_detector()

    def _load_images(self, camera_side):
        left_images = []
        for extension in ["jpg", "png", "jpeg"]:
            left_images += glob.glob(os.path.join(self.image_dir, f"*{camera_side}*.{extension}"))

        # 随机选择一部分图像对进行处理
        self.detect_num = min(self.detect_num, len(left_images))
        if self.shuffle:
            random_indices = random.sample(range(len(left_images)), self.detect_num)  # 生成随机索引
        else:
            random_indices = list(range(self.detect_num))
        self.image_paths = [left_images[i] for i in random_indices]
        if len(self.image_paths):
            self.imageSize = cv2.imread(self.image_paths[0]).shape[:2][::-1]
        else:
            raise ValueError("未找到任何图像")

    def _detect_chessboard(self, image, shape_grad):
        """检测棋盘格"""
        ret, corners = cv2.findChessboardCorners(image, shape_grad, None)
        if ret:
            # 角点精检测
            corners = cv2.cornerSubPix(image, corners, (11, 11), (-1, -1), self.criteria)
            # 绘制并显示角点
            # cv2.drawChessboardCorners(image, shape_grad, corners, ret)
        return ret, corners

    def _generate_detector(self):
        params = cv2.SimpleBlobDetector_Params()
        params.filterByArea = True
        params.minArea = 500
        params.maxArea = 100000
        params.filterByCircularity = True
        params.minCircularity = 0.2
        params.filterByConvexity = True
        params.minConvexity = 0.2
        params.filterByInertia = True
        params.minInertiaRatio = 0.2
        self.detector = cv2.SimpleBlobDetector_create(params)

    def _detect_CirclesGrid(self, image, shape_grad):
        """检测圆点格"""
        # ret, corners = cv2.findCirclesGrid(image, shape_grad, cv2.CALIB_CB_ASYMMETRIC_GRID)
        if self.detector is not None:
            ret, corners = cv2.findCirclesGrid(image, shape_grad, cv2.CALIB_CB_SYMMETRIC_GRID, blobDetector=self.detector)
        else:
            ret, corners = cv2.findCirclesGrid(image, shape_grad, cv2.CALIB_CB_SYMMETRIC_GRID)
        # if ret:
            # corners = cv2.cornerSubPix(image, corners, (3, 3), (-1, -1), self.criteria)
            # 绘制并显示角点
            # cv2.drawChessboardCorners(image, shape_grad, corners, ret)
        return ret, corners

    def _add_single_points(self, camera_side):
        """为单目校准收集角点数据"""
        start_time = time.time()
        # 清空原有数据
        self.obj_points.clear()
        self.img_points.clear()

        # 并行处理图像
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            results = list(tqdm(
                executor.map(self.process_single_image, self.image_paths),
                total=len(self.image_paths),
                desc=f"Processing {camera_side} images"
            ))

        # 收集有效角点
        cnt_success = 0
        for success, corners in results:
            if success:
                objp = np.zeros((self.pattern_size[0] * self.pattern_size[1], 3), np.float32)
                objp[:, :2] = np.mgrid[0:self.pattern_size[0], 0:self.pattern_size[1]].T.reshape(-1, 2)
                objp *= self.square_size
                self.obj_points.append(objp)
                self.img_points.append(corners)
                cnt_success += 1
            else:
                if self.filter_files:
                    self._move_failed_image(self.image_paths)

        end_time = time.time()
        print(f"Processed {cnt_success}/{len(self.image_paths)} images in {end_time - start_time:.2f}s")

    def process_single_image(self, image_path):
        """处理单张图像的角点检测"""
        img = cv2.imread(image_path)
        if img is None:
            return (False, None)

        # 转灰度并检测角点
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if self.detect_shape == "circles":
            ret, corners = self._detect_CirclesGrid(gray, self.pattern_size)
        else:
            ret, corners = self._detect_chessboard(gray, self.pattern_size)

        if ret:
            # 角点精修（可选）
            # corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), self.criteria)
            return (True, corners)
        else:
            return (False, None)

    def _move_failed_image(self, image_path):
        """将检测失败的图像移动到指定目录"""
        corners_none_dir = os.path.join(self.image_dir, "corners_none_single")
        os.makedirs(corners_none_dir, exist_ok=True)
        os.rename(image_path, os.path.join(corners_none_dir, os.path.basename(image_path)))

    def save_single_calibration(self, file_path=None):
        # 保存类别映射到YAML文件
        if os.path.exists(f"single_calibration_data.npz"):
            i = 0
            while os.path.exists(f"single_calibration_data_{i}.npz"):
                i += 1
            file_path = file_path if file_path else f"single_calibration_data_{i}.npz"
        else:
            file_path = file_path if file_path else f"single_calibration_data.npz"
        np.savez(file_path, epe=self.ret, M=self.camera_matrix, d=self.dist_coeffs)

    def save_single_json(self, file_path=None):
        # 保存类别映射到YAML文件
        if os.path.exists(f"single_calibration_data.json"):
            i = 0
            while os.path.exists(f"single_calibration_data_{i}.json"):
                i += 1
            file_path = file_path if file_path else f"single_calibration_data_{i}.json"
        else:
            file_path = file_path if file_path else f"single_calibration_data.json"
        args = {
            'epe': self.ret,
            'M': self.camera_matrix,
            'd': self.dist_coeffs,
        }

        # 将 NumPy 数组转换为列表
        def numpy_to_list(d):
            if isinstance(d, dict):
                return {k: numpy_to_list(v) for k, v in d.items()}
            elif isinstance(d, (list, tuple)):
                return [numpy_to_list(i) for i in d]
            elif isinstance(d, np.ndarray):
                return d.tolist()
            else:
                return d

        serializable_data = numpy_to_list(args)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=4)

    def load_single_calibration(self, file_path, camera_side=None):
        data = np.load(file_path)
        if camera_side == 'left':
            self.camera_matrix_left = data['M']
            self.dist_coeffs_left = data['d']
            self.ret = data['epe']
        elif camera_side == 'right':
            self.camera_matrix_right = data['M']
            self.dist_coeffs_right = data['d']
            self.ret = data['epe']
        else:
            self._load_images('left')
            self.camera_matrix = data['M']
            self.dist_coeffs = data['d']
            self.ret = data['epe']

    def load_single_json(self, file_path, camera_side=None):
        # 从 JSON 文件中加载数据
        with open(file_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
            # 将列表转换回 NumPy 数组

        def list_to_numpy(d):
            if isinstance(d, dict):
                return {k: list_to_numpy(v) for k, v in d.items()}
            elif isinstance(d, list):
                # 尝试将列表转换为 NumPy 数组
                try:
                    return np.array(d)
                except ValueError:  # 如果不是数字列表，则保持为列表
                    return [list_to_numpy(i) for i in d]
            else:
                return d

                # 转换并返回包含 NumPy 数组的字典

        data = list_to_numpy(loaded_data)
        side = (camera_side or "").lower()
        if side.startswith('left'):
            self.camera_matrix_left = data['M']
            self.dist_coeffs_left = data['d']
            self.ret = data['epe']
        elif side.startswith('right'):
            self.camera_matrix_right = data['M']
            self.dist_coeffs_right = data['d']
            self.ret = data['epe']
        else:
            self._load_images('left')
            self.camera_matrix = data['M']
            self.dist_coeffs = data['d']
            self.ret = data['epe']

    def rectify_and_save_images_single_camera(self, img_path=None, show=False):
        start_time = time.time()
        if img_path is None:
            img_path = self.image_paths
        else:
            img_path = glob.glob(img_path)
        for path in tqdm(img_path, desc="Rectifying images..."):

            img = cv2.imread(path)
            if img is None:
                print("未找到图像")
                return
            img_rectified = self.rectify_images_single_camera(img)

            if show:
                cv2.imshow('Rectified Image', img_rectified)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            else:
                dir_ = os.path.dirname(path)
                name = os.path.basename(path)
                os.makedirs(os.path.join(dir_, 'rectify'), exist_ok=True)
                path_n = os.path.join(dir_, 'rectify', name)
                cv2.imwrite(str(path_n), img_rectified)
        if not show:
            end_time = time.time()
            print(
                f"图像已校正并保存到 {os.path.join(os.path.dirname(img_path[0]), 'rectify')} in {end_time - start_time:.2f} seconds")

    def rectify_images_single_camera(self, img):
        # 单目标定校正流程
        new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(self.camera_matrix, self.dist_coeffs, self.imageSize,
                                                               1,  # alpha参数控制保留区域（1为保留全部像素）
                                                               self.imageSize)
        # 生成校正映射表
        map1, map2 = cv2.initUndistortRectifyMap(
            self.camera_matrix,
            self.dist_coeffs,
            None,  # 无需旋转矩阵，使用默认值
            new_camera_matrix,
            self.imageSize,
            cv2.CV_32FC1
        )
        img_rectified = cv2.remap(img, map1, map2, cv2.INTER_LINEAR)
        return img_rectified

    def calibrate_single_camera(self, camera_side):
        start_time = time.time()  # 计时开始
        self._load_images(camera_side)
        self._add_single_points(camera_side)

        if len(self.obj_points) == 0 or len(self.img_points) == 0:
            print(f"{camera_side} no enough points for calibration")
            return False
        flags = 0
        # flags |= cv2.CALIB_FIX_FOCAL_LENGTH
        # flags |= cv2.CALIB_FIX_INTRINSIC
        # flags |= cv2.CALIB_THIN_PRISM_MODEL
        # flags |= cv2.CALIB_ZERO_TANGENT_DIST
        flags |= cv2.CALIB_RATIONAL_MODEL
        camera_matrix, dist_coeffs = None, None
        if self.camera_matrix_left is not None and self.dist_coeffs_left is not None:
            camera_matrix = self.camera_matrix_left
            dist_coeffs = self.dist_coeffs_left
            # flags |= cv2.CALIB_FIX_INTRINSIC
            flags |= cv2.CALIB_USE_INTRINSIC_GUESS
            # flags |= cv2.CALIB_FIX_FOCAL_LENGTH
            # flags |= cv2.CALIB_FIX_INTRINSIC
            # flags |= cv2.CALIB_THIN_PRISM_MODEL
            flags |= cv2.CALIB_RATIONAL_MODEL
        elif self.camera_matrix_right is not None and self.dist_coeffs_right is not None:
            camera_matrix = self.camera_matrix_right
            dist_coeffs = self.dist_coeffs
            flags |= cv2.CALIB_USE_INTRINSIC_GUESS
            # flags |= cv2.CALIB_FIX_INTRINSIC
            # flags |= cv2.CALIB_THIN_PRISM_MODEL
            flags |= cv2.CALIB_RATIONAL_MODEL
        self.ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            self.obj_points, self.img_points, self.imageSize, camera_matrix, dist_coeffs, flags=flags)

        if self.ret:
            end_time = time.time()  # 计时结束
            print(f"Calibrated successfully in {end_time - start_time:.2f} seconds")
            print(f" {camera_side} Camera Calibration Reprojection Error: {self.ret:.4f} pixels")
            self.camera_matrix = camera_matrix
            self.dist_coeffs = dist_coeffs
            args = {"epe": self.ret, "M": camera_matrix, "d": dist_coeffs}
            return args
        else:
            print(f"{camera_side} camera calibration failed")
            return False
