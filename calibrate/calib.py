import glob
import json
import threading

import cv2
import matplotlib.pyplot as plt
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor
import time
from tqdm import tqdm
import random  # 添加导入random模块
# from common.tools import drawLine, show_image, shift_pairwise
# from screeninfo import get_monitors

def drawLine(img, num=16, thickness=4):
    h, w = img.shape[:2]
    for i in range(0, h, h // num):
        cv2.line(img, (0, i), (w, i), (0, 255, 0), thickness, 8)
    return img


def show_image(name, img, x=0, y=0, scale=None, time=None):
    # cv2.WINDOW_NORMAL：用户可以调整窗口的大小（默认标志，如果未指定其他标志）。
    # cv2.WINDOW_AUTOSIZE：窗口大小自动调整以适应显示的图像，用户不能手动调整窗口大小。
    # cv2.WINDOW_FREERATIO：当调整窗口大小时，图像的内容可以自由缩放（默认）。
    # cv2.WINDOW_KEEPRATIO：当调整窗口大小时，图像的内容保持其纵横比。
    cv2.namedWindow(name, cv2.WINDOW_FREERATIO)
    cv2.moveWindow(name, x, y)
    # pyautogui.hotkey('shift')

    w, h = img.shape[:2]
    if scale:
        cv2.resizeWindow(name, int(h * scale), int(w * scale))  # 自己设定窗口图片的大小
    cv2.imshow(name, img)
    if time:
        cv2.waitKey(time)
        cv2.destroyAllWindows()


def get_color_rainbow(i, max_i):
    # 计算颜色比例（0到1）
    ratio = i / max_i
    # 使用彩虹色映射
    cmap = plt.get_cmap('hsv')
    return cmap(ratio)


def get_style_by_index(i):
    styles = ['-', '--', ':', '-.']
    return styles[i % len(styles)]  # 循环使用颜色列表


def plot_parameters(*args, name=None, style=None, merge=False):
    """
    绘制校准参数收敛曲线图

    参数:
    *args (tuple): 可变参数，每组参数应包含 (errors, f1_values, f2_values, t1_values)
    merge (bool): 是否合并绘制在同一子画布上，默认为 False
    """
    import matplotlib.pyplot as plt
    # 如果 merge 为 True，则在一组画布上绘制所有曲线
    if merge:
        fig, ax = plt.subplots(figsize=(12, 6))

        # 遍历每组数据，绘制在同一画布上
        for i, item in enumerate(args):
            ax.plot(item, label=name[i] if name else '', color=get_color_rainbow(i, len(args)), linestyle=get_style_by_index(i))

        # 设置图表属性
        ax.set_xlabel('Iteration')
        ax.set_ylabel('Value')
        # ax.set_title('Calibration Parameters Convergence (Merged)')
        ax.legend()
        ax.grid(True)

    # 如果 merge 为 False，则为每组数据创建独立的子画布
    else:
        # 计算需要的子画布数量
        num_plots = len(args)
        # 创建子画布网格，假设最多 4 组数据，可以调整 cols 和 rows 的值
        cols = 2
        rows = (num_plots + cols - 1) // cols  # 向上取整

        fig, axes = plt.subplots(rows, cols, figsize=(12, 6 * rows))
        axes = axes.flatten()  # 将 axes 转换为一维数组，方便遍历

        # 遍历每组数据，绘制在独立的子画布上
        for i, item in enumerate(args):
            ax = axes[i]
            ax.plot(item, label=name[i] if name else '', color='black', linestyle='-')

            # 设置子画布属性
            ax.set_xlabel('Iteration')
            ax.set_ylabel('Value')
            # ax.set_title(f'Calibration Parameters Convergence (Group {i + 1})')
            ax.legend()
            ax.grid(True)

        # 关闭多余的子画布
        for j in range(num_plots, len(axes)):
            axes[j].axis('off')

    plt.tight_layout()  # 调整子画布布局


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
        self.img_points_left = []
        self.img_points_right = []
        self.img_points = []
        self.image_paths = None
        self.image_paths_test = None
        self.camera_matrix_left = None
        self.camera_matrix_right = None
        self.dist_coeffs_left = None
        self.dist_coeffs_right = None
        self.imageSize = None
        self.detector = None
        self.R = None
        self.T = None
        self.E = None
        self.F = None
        self.R1 = None
        self.R2 = None
        self.P1 = None
        self.P2 = None
        self.Q = None
        self.ret = None
        self.camera_matrix = None
        self.dist_coeffs = None

        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        self.image_dir = image_dir
        import tkinter as tk
        root = tk.Tk()
        self.screen_size = (root.winfo_screenwidth()-100, root.winfo_screenheight()-100)
        if gen_detector:
            self._generate_detector()
        # for m in get_monitors():
        #     self.screen_size = (m.width, m.height)
        # print(f"屏幕尺寸：{self.screen_size}")

        # self.screen_size = (1920, 1080)

    def _load_image_pairs(self,  left_name='left', right_name='right', detect_num=1000):
        left_images = []
        right_images = []
        for extension in ["jpg", "png", "jpeg"]:
            left_images += glob.glob(os.path.join(self.image_dir, f"*{left_name}*.{extension}"))
            right_images += glob.glob(os.path.join(self.image_dir, f"*{right_name}*.{extension}"))

        if len(left_images) != len(right_images):
            raise ValueError("左图和右图的数量不匹配")

        # 随机选择一部分图像对进行处理
        num_images_to_process = min(detect_num, len(left_images))
        if self.shuffle:
            random_indices = random.sample(range(len(left_images)), num_images_to_process)  # 生成随机索引
        else:
            random_indices = list(range(num_images_to_process))
        image_paths = [(left_images[i], right_images[i]) for i in random_indices]
        if len(image_paths):
            self.imageSize = cv2.imread(image_paths[0][0]).shape[:2][::-1]
        else:
            raise ValueError("未找到任何图像")
        # self.image_paths_test = [(left_images[i], right_images[i]) for i in range(len(left_images)) not in random_indices]
        image_paths_test = [(left_images[i], right_images[i]) for i in range(len(left_images)) if
                                 i not in set(random_indices)]
        return image_paths, image_paths_test, self.imageSize


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

    def _add_points(self):
        start_time = time.time()  # 计时开始
        with ThreadPoolExecutor() as executor:
            results = list(tqdm(executor.map(self._process_image_pair, self.image_paths), total=len(self.image_paths),
                                desc="Processing image pairs"))

        cnt_success = sum(1 for success, _, _ in results if success)
        end_time = time.time()  # 计时结束
        print(
            f"Processed {cnt_success} out of {len(self.image_paths)} image pairs in {end_time - start_time:.2f} seconds")

    def _process_image_pair(self, image_pair):  # threading
        left_img_path, right_img_path = image_pair
        img_left = cv2.imread(left_img_path)
        img_right = cv2.imread(right_img_path)
        success = self._add_calibration_points(img_left, img_right)
        if not success and self.filter_files:
            corners_none_dir = os.path.join(self.image_dir, "corners_none")
            os.makedirs(corners_none_dir, exist_ok=True)
            os.rename(left_img_path, os.path.join(corners_none_dir, os.path.basename(left_img_path)))
            os.rename(right_img_path, os.path.join(corners_none_dir, os.path.basename(right_img_path)))
        return success, left_img_path, right_img_path

    def filter_image_pairs(self):
        start_time = time.time()
        self.image_paths, _, self.imageSize = self._load_image_pairs(self.detect_num)
        stay = self.filter_files
        self.filter_files = True
        with ThreadPoolExecutor() as executor:
            results = list(tqdm(executor.map(self._process_image_pair, self.image_paths), total=len(self.image_paths),
                                desc="Processing image pairs"))

        cnt_success = sum(1 for success, _, _ in results if success)
        end_time = time.time()
        self.filter_files = stay
        print(f"已过滤文件{len(self.image_paths)-cnt_success}/{len(self.image_paths)} \\ in {end_time - start_time:.2f} seconds")
        # for l, r in img_paths:
        #     img_left = cv2.imread(l)
        #     img_right = cv2.imread(r)
        #     corners_left, corners_right = self._find_corners(img_left, img_right)
        #     # cv2.drawChessboardCorners(img_left, self.pattern_size, corners_left, True)
        #     # cv2.drawChessboardCorners(img_right, self.pattern_size, corners_right, True)
        #     if corners_left is not None and corners_right is not None:
        #         continue
        #
        # end_time = time.time()
        # print(f"图像已展示完毕\\ in {end_time - start_time:.2f} seconds")

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

    def _find_corners(self, img_left, img_right):
        gray_left = cv2.cvtColor(img_left, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(img_right, cv2.COLOR_BGR2GRAY)
        if self.detect_shape == "circles":
            ret_left, corners_left = self._detect_CirclesGrid(gray_left, self.pattern_size)
            ret_right, corners_right = self._detect_CirclesGrid(gray_right, self.pattern_size)
        else:
            ret_left, corners_left = self._detect_chessboard(gray_left, self.pattern_size)
            ret_right, corners_right = self._detect_chessboard(gray_right, self.pattern_size)
        if not ret_left or not ret_right:
            # 如果检测不到角点，将图像移动到 corners_none 目录
            # corners_none_dir = os.path.join(os.getcwd(), "corners_none")
            # os.makedirs(corners_none_dir, exist_ok=True)
            # cv2.imwrite(os.path.join(corners_none_dir, "left_failed.png"), img_left)
            # cv2.imwrite(os.path.join(corners_none_dir, "right_failed.png"), img_right)
            return None, None
        return corners_left, corners_right

    def _add_calibration_points(self, img_left, img_right):
        corners_left, corners_right = self._find_corners(img_left, img_right)
        if corners_left is not None and corners_right is not None:
            objp = np.zeros((self.pattern_size[0] * self.pattern_size[1], 3), np.float32)
            objp[:, :2] = np.mgrid[0:self.pattern_size[0], 0:self.pattern_size[1]].T.reshape(-1, 2)
            objp *= self.square_size
            self.obj_points.append(objp)
            self.img_points_left.append(corners_left)
            self.img_points_right.append(corners_right)
            return True
        return False

    def calibrate_and_evaluate(self, args_tuple):
        """
        执行一次立体标定并评估误差。

        参数:
            args_tuple (tuple): 包含标定所需的参数

        返回:
            dict: 标定结果和误差评估值
        """
        object_points, image_points1, image_points2, camera_matrix1, dist_coeffs1, \
            camera_matrix2, dist_coeffs2, image_size, R, T, E, F, criteria, flags, image_paths_test = args_tuple

        # 执行立体标定
        result = cv2.stereoCalibrate(
            object_points, image_points1, image_points2,
            camera_matrix1, dist_coeffs1, camera_matrix2, dist_coeffs2,
            image_size, criteria=criteria, flags=flags
        )

        error, cm1, dc1, cm2, dc2, R, T, E, F = result

        # 保存当前标定参数用于误差评估
        camera = [cm1, dc1, cm2, dc2, R, T, E, F]

        # 评估误差（num=5 表示每次评估5张图像）
        align_error, max_error, mean_error = self.evaluate_error(num=40, train=True, show=False, image_paths=image_paths_test, camera=camera)

        return {
            'error': error,
            'cm1': cm1,
            'dc1': dc1,
            'cm2': cm2,
            'dc2': dc2,
            'R': R,
            'T': T,
            'E': E,
            'F': F,
            'align_error': align_error,
            'max_error': max_error,
            'mean_error': mean_error
        }

    def value_stereo_calibrate(self, result_parent='result_stereo', step=4):
        # self._load_image_pairs()
        # self._add_points()
        parent = result_parent
        os.makedirs(parent, exist_ok=True)
        f = os.path.join(parent, 'value.csv')
        # s = "" if os.path.exists(f) else (("%10s," * 12 % ('epe', 't1', 'f11', 'f12','cx1', 'cy1', 'f21', 'f22',
        #                                                             'cx2', 'cy2', 't2', 't3')).rstrip(",") + "\n")  # header
        s = (("%10s," * 15 % ('epe', 't1', 'f11', 'f12','cx1', 'cy1', 'f21', 'f22', 'cx2', 'cy2', 't2', 't3',
                              'align_error', 'max_error', 'mean_error')).rstrip(",") + "\n")  # header
        with open(f, 'w') as file:
            file.write(s)
        start_time = time.time()  # 计时开始
        args = []
        flags = 0
        camera_matrix_left = None
        dist_coeffs_left = None
        camera_matrix_right = None
        dist_coeffs_right = None
        if self.camera_matrix_left is not None and self.dist_coeffs_left is not None \
                and self.camera_matrix_right is not None and self.dist_coeffs_right is not None:
            camera_matrix_left = self.camera_matrix_left.copy()
            dist_coeffs_left = self.dist_coeffs_left.copy()
            camera_matrix_right = self.camera_matrix_right.copy()
            dist_coeffs_right = self.dist_coeffs_right.copy()
            # flags |= cv2.CALIB_USE_INTRINSIC_GUESS
            # flags |= cv2.CALIB_FIX_FOCAL_LENGTH
            flags |= cv2.CALIB_FIX_INTRINSIC
            # flags |= cv2.CALIB_THIN_PRISM_MODEL
            flags |= cv2.CALIB_RATIONAL_MODEL
        # criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 8000, 1e-8)
        for i in range(step, self.detect_num + 1, step):
            self.image_paths, self.image_paths_test, self.imageSize = self._load_image_pairs('_r','_l', i)
            self._add_points()
            if len(self.obj_points) == 0 or len(self.img_points_left) == 0 or len(self.img_points_right) == 0:
                print("没有足够的标定点进行立体校准")
                return False
            args.append([
                self.obj_points[:i],  # objectPoints
                self.img_points_left[:i],  # imagePoints1
                self.img_points_right[:i],  # imagePoints2
                camera_matrix_left,  # cameraMatrix1
                dist_coeffs_left,  # distCoeffs1
                camera_matrix_right,  # cameraMatrix2
                dist_coeffs_right,  # distCoeffs2
                self.imageSize,  # imageSize (必须是 (width, height))
                None,  # R
                None,  # T
                None,  # E
                None,  # F
                None,  # criteria
                flags,  # distCoeffs2
                # 可选参数（如criteria, flags等）
                self.image_paths_test
            ])

        with ThreadPoolExecutor() as executor:
            results = list(tqdm(
                executor.map(self.calibrate_and_evaluate, args),
                total=len(args),
                desc="Processing image pairs"
            ))
        # 存储参数变化
        f11_values = []
        f12_values = []
        f21_values = []
        f22_values = []
        t1_values = []
        t2_values = []
        t3_values = []
        cx1_values = []
        cx2_values = []
        cy1_values = []
        cy2_values = []
        errors = []
        align_errors = []  # 存储对齐误差
        max_errors = []  # 存储最大误差
        mean_errors = []  # 存储平均误差
        # 选择误差最小的结果
        best_error = float('inf')
        for result in results:
            error = result['error']
            cm1 = result['cm1']
            dc1 = result['dc1']
            cm2 = result['cm2']
            dc2 = result['dc2']
            R = result['R']
            T = result['T']
            E = result['E']
            F = result['F']
            align_error = result['align_error']
            max_error = result['max_error']
            mean_error = result['mean_error']

            errors.append(error)
            t1 = T[0]
            f11 = cm1[0, 0]
            f12 = cm1[1, 1]
            cx1 = cm1[0, 2]
            cy1 = cm1[1, 2]
            f21 = cm2[0, 0]
            f22 = cm2[1, 1]
            cx2 = cm2[0, 2]
            cy2 = cm2[1, 2]
            t2 = T[1]
            t3 = T[2]
            f11_values.append(f11)
            f12_values.append(f12)
            f21_values.append(f21)
            f22_values.append(f22)
            t1_values.append(t1)
            t2_values.append(t2)
            t3_values.append(t3)
            cx1_values.append(cx1)
            cx2_values.append(cx2)
            cy1_values.append(cy1)
            cy2_values.append(cy2)
            align_errors.append(align_error)
            max_errors.append(max_error)
            mean_errors.append(mean_error)

            with open(f, 'a') as file:
                file.write(("%10.5g," * 15 % (error, t1, f11, f12, cx1, cy1, f21, f22, cx2, cy2, t2, t3, align_error, max_error, mean_error)).rstrip(",") + "\n")
            if align_error < best_error:
                best_error = align_error
                self.ret = error
                self.camera_matrix_left = cm1
                self.dist_coeffs_left = dc1
                self.camera_matrix_right = cm2
                self.dist_coeffs_right = dc2
                self.R = R
                self.T = T
                self.E = E
                self.F = F
                self.R1, self.R2, self.P1, self.P2, self.Q, _, _ = cv2.stereoRectify(
                    self.camera_matrix_left, self.dist_coeffs_left,
                    self.camera_matrix_right, self.dist_coeffs_right,
                    self.imageSize, self.R, self.T
                )
                self.save_json(os.path.join(parent, 'parameters.json'))
        end_time = time.time()
        print(f"Calibrated successfully in {end_time - start_time:.2f} seconds")
        print(f"Best align Error: {best_error:.4f} pixels")
        name = ['Reprojection Error', 'Focal Length (f11)', 'Focal Length (f12)', 'Focal Length (f21)', 'Focal Length (f22)',
                'Principal Point (cx1)', 'Principal Point (cy1)',
                'Principal Point (cx2)', 'Principal Point (cy2)',
                'Baseline (t1)', 'Translation (t2)', 'Translation (t3)']

        # 合并显示所有参数变化趋势
        plot_parameters(errors, f11_values, f12_values, f21_values, f22_values, cx1_values, cy1_values,
                        cx2_values, cy2_values, t1_values, t2_values, t3_values,
                        name=name, merge=True)
        plt.savefig(os.path.join(parent, "parameters_all_merged.png"))
        plt.close()

        plot_parameters(errors, f11_values, f12_values, f21_values, f22_values, cx1_values, cy1_values,
                        cx2_values, cy2_values, t1_values, t2_values, t3_values,
                        name=name, merge=False)
        plt.savefig(os.path.join(parent, "parameters_all_split.png"))
        plt.close()

        # 分开展示每个参数
        plot_parameters(errors, name=['Reprojection Error'], merge=False)
        plt.savefig(os.path.join(parent, "parameters_error.png"))
        plt.close()

        plot_parameters(f11_values, f12_values, f21_values, f22_values, name=['Focal Length (f11)', 'Focal Length (f12)', 'Focal Length (f21)', 'Focal Length (f22)'], merge=True)
        plt.savefig(os.path.join(parent, "parameters_focal_lengths.png"))
        plt.close()

        plot_parameters(cx1_values, cy1_values, cx2_values, cy2_values,
                        name=['Principal Point (cx1)', 'Principal Point (cy1)',
                              'Principal Point (cx2)', 'Principal Point (cy2)'],
                        merge=True)
        plt.savefig(os.path.join(parent, "parameters_principal_points.png"))
        plt.close()

        plot_parameters(t1_values,
                        name=['Baseline (t1)'],
                        merge=False)
        plt.savefig(os.path.join(parent, "parameters_Baseline.png"))
        plt.close()

        plot_parameters(t2_values, t3_values,
                        name=['Translation (t2)', 'Translation (t3)'],
                        merge=True)
        plt.savefig(os.path.join(parent, "parameters_translation.png"))
        plt.close()

        plot_parameters(align_errors, max_errors, mean_errors,
                        name=['align errors', 'Max distance errer', 'mean distance errer'],
                        merge=True)
        plt.savefig(os.path.join(parent, "parameters_val.png"))
        plt.close()

        # if show:
        #     plt.show()
        # else:
        #     plt.close('all')

    def value_single_calibrate(self, camera_side, show=False, result_parent='sc', step=10):
        """
        对单目相机进行逐步增加图像数量的标定，并保存每次的结果到CSV文件。

        参数:
            camera_side (str): 要标定的相机 ("left" 或 "right")。
            show (bool): 是否显示标定后的参数图表。
            result_dir (str): 保存结果的CSV文件路径。
        """
        # 如果文件不存在，则写入表头
        s = ""
        parent = result_parent
        os.makedirs(parent, exist_ok=True)
        result_dir = 'value_single.csv'
        result_dir = os.path.join(parent, result_dir)
        # if not os.path.exists(result_dir):
        header = ("%10s," * 5 % ('epe', 'f1', 'f2', 'cx', 'cy')).rstrip(",") + "\n"
        s = header

        with open(result_dir, 'w') as file:
            file.write(s)

        start_time = time.time()
        best_error = float('inf')
        errors = []
        f1_values = []
        f2_values = []
        cx_values = []
        cy_values = []

        for i in range(step, self.detect_num + 1, step):
            self.detect_num = i
            print(f"\nProcessing {i} image pairs...")

            # 加载指定数量的图像
            self._load_images(camera_side)

            # 收集角点信息
            self._add_single_points(camera_side)

            if len(self.obj_points) == 0 or len(self.img_points) == 0:
                print("没有足够的标定点进行单目标定")
                continue

            # 进行单目标定
            ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
                self.obj_points, self.img_points, self.imageSize, None, None
            )

            if ret:
                print(f"{camera_side} 单目标定成功，重投影误差: {ret:.4f} 像素")

                # 记录误差和相机矩阵参数
                errors.append(ret)
                f1_values.append(camera_matrix[0, 0])  # fx
                f2_values.append(camera_matrix[1, 1])  # fy
                cx_values.append(camera_matrix[0, 2])  # cx
                cy_values.append(camera_matrix[1, 2])  # cy

                # 将数据写入CSV文件
                with open(result_dir, 'a') as file:
                    line = ("%10.5g," * 5 % (ret, camera_matrix[0, 0], camera_matrix[1, 1],
                                             camera_matrix[0, 2], camera_matrix[1, 2])).rstrip(",") + "\n"
                    file.write(line)
                if ret < best_error:
                    best_error = ret
                    self.ret = best_error
                    self.camera_matrix = camera_matrix
                    self.dist_coeffs = dist_coeffs
                    self.save_single_json(os.path.join(parent, 'parameters_single.json'))

        end_time = time.time()
        print(f"完成所有单目标定，耗时 {end_time - start_time:.2f} 秒")

        # 绘制参数变化趋势图
        name = ['Reprojection Error', 'Focal Length (fx)', 'Focal Length (fy)', 'Principal Point (cx)',
                'Principal Point (cy)']
        plot_parameters(errors, f1_values, f2_values, cx_values, cy_values, name=name, merge=False)
        if show:
            plt.show()
        else:
            plt.savefig(os.path.join(parent, "parameters_s.png"))
            plot_parameters(errors, f1_values, f2_values, cx_values, cy_values, name=name, merge=True)
            plt.savefig(os.path.join(parent, "parameters_m.png"))
            plot_parameters(errors, name=['Reprojection Error'], merge=False)
            plt.savefig(os.path.join(parent, "parameters_error.png"))
            plot_parameters(f1_values, f2_values, name=['Focal Length (fx)', 'Focal Length (fy)'], merge=True)
            plt.savefig(os.path.join(parent, "parameters_focus.png"))
            plot_parameters(cx_values, cy_values, name=['Principal Point (cx)', 'Principal Point (cy)'], merge=True)
            plt.savefig(os.path.join(parent, "parameters_cxy.png"))
        # if show:
        #     plt.show()
        # else:
        #     plt.savefig("single_calibration_parameters.png")

    def calibrate(self, left_name='_l', right_name='_r', num=None):
        if num is None:
            num=self.detect_num
        self.image_paths, self.image_paths_test, self.imageSize = self._load_image_pairs(left_name, right_name, num)
        self._add_points()
        start_time = time.time()  # 计时开始
        if len(self.obj_points) == 0 or len(self.img_points_left) == 0 or len(self.img_points_right) == 0:
            print("没有足够的标定点进行立体校准")
            return False
        flags = 0
        # 如果该标志被设置，那么就会固定输入的cameraMatrix和distCoeffs不变，只求解R,T,E,F.
        # flags |= cv2.CALIB_FIX_INTRINSIC
        # 根据用户提供的cameraMatrix和distCoeffs为初始值开始迭代
        # flags |= cv2.CALIB_USE_INTRINSIC_GUESS
        # 迭代过程中不会改变焦距
        # flags |= cv2.CALIB_FIX_FOCAL_LENGTH
        # 切向畸变保持为零
        # flags |= cv2.CALIB_ZERO_TANGENT_DIST
        # flags |= cv2.CALIB_FIX_K1  # 固定k1为0
        # flags |= cv2.CALIB_FIX_K2  # 固定k2为0
        # flags |= cv2.CALIB_FIX_K3  # 固定k3为0
        # 固定主点（图像中心点）为提供的值，不进行优化
        # flags |= cv2.CALIB_FIX_PRINCIPAL_POINT
        # 固定焦距为提供的值，不进行优化
        # flags |= cv2.CALIB_FIX_FOCAL_LENGTH
        # 使用更复杂的理性模型来描述径向畸变（包含额外的畸变参数 k4, k5, k6）
        flags |= cv2.CALIB_RATIONAL_MODEL
        # 启用薄棱镜畸变模型（包含额外的畸变参数 s1, s2, s3, s4）
        # flags |= cv2.CALIB_THIN_PRISM_MODEL
        # 分别固定对应的径向畸变参数（k1 到 k6)
        # flags |= cv2.CALIB_FIX_K1
        # 强制左右相机具有相同的焦距
        # flags |= cv2.CALIB_SAME_FOCAL_LENGTH
        # 固定切向畸变为提供的值，不进行优化
        # flags |= cv2.CALIB_FIX_TANGENT_DIST
        if self.camera_matrix_left is not None and self.dist_coeffs_left is not None \
                and self.camera_matrix_right is not None and self.dist_coeffs_right is not None:
            print( "Using pre-calibrated camera parameters")
            # print( "Left camera matrix: ", self.camera_matrix_left)
            # print( "right camera matrix: ", self.camera_matrix_right)
            # flags |= cv2.CALIB_USE_INTRINSIC_GUESS
            # flags |= cv2.CALIB_FIX_FOCAL_LENGTH
            flags |= cv2.CALIB_FIX_INTRINSIC
            # flags |= cv2.CALIB_THIN_PRISM_MODEL
            flags |= cv2.CALIB_RATIONAL_MODEL
        # criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 8000, 1e-8)
        self.ret, self.camera_matrix_left, self.dist_coeffs_left, self.camera_matrix_right, self.dist_coeffs_right, self.R, self.T, self.E, self.F = cv2.stereoCalibrate(
            self.obj_points, self.img_points_left, self.img_points_right, self.camera_matrix_left,
            self.dist_coeffs_left, self.camera_matrix_right, self.dist_coeffs_right, self.imageSize, flags=flags)
        self.R1, self.R2, self.P1, self.P2, self.Q, _, _ = cv2.stereoRectify(
            self.camera_matrix_left, self.dist_coeffs_left,
            self.camera_matrix_right, self.dist_coeffs_right,
            self.imageSize, self.R, self.T
        )
        if self.ret:
            end_time = time.time()  # 计时结束
            print(f"Calibrated successfully in {end_time - start_time:.2f} seconds")
            print(f"Stereo Calibration Reprojection Error: {self.ret:.4f} pixels")
            args = {
                'epe': self.ret,
                'M1': self.camera_matrix_left,
                'M2': self.camera_matrix_right,
                'd1': self.dist_coeffs_left,
                'd2': self.dist_coeffs_right,
                'R': self.R,
                'T': self.T,
                'E': self.E,
                'F': self.F,
                'R1': self.R1,
                'R2': self.R2,
                'P1': self.P1,
                'P2': self.P2,
                'Q': self.Q
            }
            return args
            # error_list = []
            # for i in range(len(self.obj_points)):
            #     # 使用单目校准得到的相机位姿进行投影
            #     imgpts_left, _ = cv2.projectPoints(
            #         self.obj_points[i],
            #         rvecs_list[i],
            #         tvecs_list[i],
            #         self.camera_matrix_left,
            #         self.dist_coeffs_left
            #     )
            #     error_left = cv2.norm(
            #         self.img_points_left[i],
            #         imgpts_left,
            #         cv2.NORM_L2
            #     ) / len(imgpts_left)
            #     error_list.append(error_left)
            #
            # average_error = sum(error_list) / len(error_list)
            # print(f"Per-image average reprojection error: {average_error:.4f}")
            # self.save_calibration("calibration_data.npz")
            # self.save_json("calibration_data.json")
        else:
            print("Calibration failed")
            return False

    def save_calibration(self, file_path):
        # 保存类别映射到YAML文件
        if os.path.exists(f"stereo_calibration_data.npz"):
            i = 0
            while os.path.exists(f"stereo_calibration_data_{i}.npz"):
                i += 1
            file_path = file_path if file_path else f"stereo_calibration_data_{i}.npz"
        else:
            file_path = file_path if file_path else f"stereo_calibration_data.npz"
        np.savez(file_path,
                 M1=self.camera_matrix_left, d1=self.dist_coeffs_left,
                 M2=self.camera_matrix_right, d2=self.dist_coeffs_right,
                 R=self.R, T=self.T, E=self.E, F=self.F, epe=self.ret,
                 P1=self.P1, P2=self.P2, Q=self.Q, R1=self.R1, R2=self.R2
                 )

    def save_json(self, file_path=None):
        # 保存类别映射到YAML文件
        if os.path.exists(f"stereo_calibration_data.json"):
            i = 0
            while os.path.exists(f"stereo_calibration_data_{i}.json"):
                i += 1
            file_path = file_path if file_path else f"stereo_calibration_data_{i}.json"
        else:
            file_path = file_path if file_path else f"stereo_calibration_data.json"
        args = {
            'epe': self.ret,
            'M1': self.camera_matrix_left,
            'M2': self.camera_matrix_right,
            'd1': self.dist_coeffs_left,
            'd2': self.dist_coeffs_right,
            'R': self.R,
            'T': self.T,
            'E': self.E,
            'F': self.F,
            'R1': self.R1,
            'R2': self.R2,
            'P1': self.P1,
            'P2': self.P2,
            'Q': self.Q
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
        with open(file_path, 'w') as f:
            json.dump(serializable_data, f, indent=4)

    def load_calibration(self, file_path):
        self.image_paths, _, self.imageSize = self._load_image_pairs(self.detect_num)

        data = np.load(file_path)
        self.camera_matrix_left = data['M1']
        self.dist_coeffs_left = data['d1']
        self.camera_matrix_right = data['M2']
        self.dist_coeffs_right = data['d2']
        self.R = data['R']
        self.T = data['T']
        self.E = data['E']
        self.F = data['F']

    def load_from_json(self, file_path):
        self.image_paths, self.image_paths_test, self.imageSize = self._load_image_pairs('_r', '_l', detect_num=self.detect_num)

        # 从 JSON 文件中加载数据
        with open(file_path, 'r') as f:
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
        list01 = list(data.keys())
        print(list01)
        self.camera_matrix_left = data['M1']
        self.dist_coeffs_left = data['d1']
        self.camera_matrix_right = data['M2']
        self.dist_coeffs_right = data['d2']
        self.R = data['R']
        self.T = data['T']
        self.E = data['E']
        self.F = data['F']
        self.ret = data['epe']
        # self.camera_args = args['camera']

    def rectify_image(self, img_left, img_right):
        size = img_left.shape
        self.R1, self.R2, self.P1, self.P2, self.Q, _, _ = cv2.stereoRectify(self.camera_matrix_left, self.dist_coeffs_left,
                                                    self.camera_matrix_right, self.dist_coeffs_right,
                                                    self.imageSize, self.R, self.T)
        map1_left, map2_left = cv2.initUndistortRectifyMap(self.camera_matrix_left, self.dist_coeffs_left, self.R1, self.P1,
                                                           self.imageSize, cv2.CV_32FC1)
        map1_right, map2_right = cv2.initUndistortRectifyMap(self.camera_matrix_right, self.dist_coeffs_right, self.R2, self.P2,
                                                             self.imageSize, cv2.CV_32FC1)
        img_left_rectified = cv2.remap(img_left, map1_left, map2_left, cv2.INTER_LINEAR)
        img_right_rectified = cv2.remap(img_right, map1_right, map2_right, cv2.INTER_LINEAR)
        return img_left_rectified, img_right_rectified

    def rectify_images(self, img_left_path=None, img_right_path=None, show=True):
        start_time = time.time()
        if img_left_path is None or img_right_path is None:
            img_paths = self.image_paths
        else:
            path_left = glob.glob(img_left_path)
            path_right = glob.glob(img_right_path)

            if len(path_left) != len(path_right):
                print("左右图像数量不匹配")
                return
            if not len(path_left) or not len(path_right):
                print("未找到图像")
                return
            img_paths = zip(path_left, path_right)
        for l, r in tqdm(img_paths, desc="Rectifying images..."):
            img_left = cv2.imread(l)
            img_right = cv2.imread(r)
            img_left_rectified, img_right_rectified = self.rectify_image(img_left, img_right)
            if show:
                img_ = np.concatenate((img_left, img_right), axis=1)
                img = np.concatenate((img_left_rectified, img_right_rectified), axis=1)
                img_c = np.concatenate((img_, img), axis=0)
                imgWidth = img_left_rectified.shape[1]  # 每行的第一个点
                scale = self.screen_size[0] / imgWidth
                drawLine(img_c, 32, max(1, int(scale)))
                if show:
                    show_image('before/after', img_c, 0, 50, scale=scale, time=-1)
            else:
                dir1 = os.path.dirname(l)
                dir2 = os.path.dirname(r)
                name1 = os.path.basename(l)
                name2 = os.path.basename(r)
                os.makedirs(os.path.join(dir1, 'rectify'), exist_ok=True)
                l = os.path.join(dir1, 'rectify', name1)
                r = os.path.join(dir2, 'rectify', name2)
                cv2.imwrite(l, img_left_rectified)
                cv2.imwrite(r, img_right_rectified)
        end_time = time.time()
        if not show:
            print(f"图像已校正并保存到 {os.path.dirname(img_paths[0])}\\rectify in {end_time - start_time:.2f} seconds")

    def show_images(self, align_err=True, detect=False, rectify=False):
        start_time = time.time()
        self.image_paths, _, self.imageSize = self._load_image_pairs(self.detect_num)
        img_paths = self.image_paths
        img = None
        for l, r in img_paths:
            img_left = cv2.imread(l)
            img_right = cv2.imread(r)
            if rectify:
                img_left, img_right = self.rectify_image(img_left, img_right)
            if align_err:
                align_error_, max_error_, mean_error_, img = self._calculate_error(img_left, img_right, detail_align=True,  detail_length=True, show_3d=False)
                if align_error_ is None or max_error_ is None or mean_error_ is None:
                    print(f"无法计算误差: {l} {r}")
            elif detect:
                corners_left, corners_right = self._find_corners(img_left, img_right)
                cv2.drawChessboardCorners(img_left, self.pattern_size, corners_left, True)
                cv2.drawChessboardCorners(img_right, self.pattern_size, corners_right, True)

            if img is not None:
                img_ = img
            else:
                img_ = np.concatenate((img_left, img_right), axis=1)
                imgWidth = img_.shape[1]  # 每行的第一个点
                scale = self.screen_size[0] / imgWidth

                drawLine(img_, 32, max(1, int(scale)))
            imgWidth = img_.shape[1]  # 每行的第一个点
            scale = self.screen_size[0] / imgWidth

            show_image('before/after', img_, 0, 50, scale=scale, time=-1)
        end_time = time.time()
        print(f"图像已展示完毕\\ in {end_time - start_time:.2f} seconds")

    def _calculate_error(self, img_left, img_right, detail_align=False, detail_length=False, show_3d=False, P1=None, P2=None):
        # 校正图像
        # img_left_rectified, img_right_rectified = self.rectify_image(img_left, img_right)
        # img_left_rectified, img_right_rectified = img_left, img_right
        # 检测角点
        corners_left, corners_right = self._find_corners(img_left, img_right)
        if corners_left is None or corners_right is None:
            return None, None, None, None

        imgWidth = img_left.shape[1]
        scale = self.screen_size[0] / imgWidth

        r, c = self.pattern_size
        e_y1 = corners_left[0][0][1] - corners_right[0][0][1]
        e_y2 = corners_left[c - 1][0][1] - corners_right[c - 1][0][1]
        e_y3 = corners_left[r * c - r][0][1] - corners_right[r * c - r][0][1]
        e_y4 = corners_left[r * c - 1][0][1] - corners_right[r * c - 1][0][1]
        # align_error = (e_y1 + e_y2 + e_y3 + e_y4) / 4
        align_error = np.sum(np.abs(np.stack([e_y1, e_y2, e_y3, e_y4]))) / 4
        if detail_align:
            print("四个角点的对齐误差：", e_y1, e_y2, e_y3, e_y4, "平均误差：", align_error)

        # 计算真实距离
        if P1 is not None and P2 is not None:
            P1i, P2i = P1, P2
        else:
            P1i, P2i = self.P1, self.P2
        if P1i is not None and P2i is not None:
            points = cv2.triangulatePoints(P1i, P2i, corners_left, corners_right)
            points_normal = points[:] / points[-1]
            point_corner = [point for point in points_normal[:3].transpose()]

            # 计算每一行的首尾长度
            row_lengths = []
            for i in range(r):
                start_point = point_corner[i * c]
                end_point = point_corner[(i + 1) * c - 1]  # 每行的最后一个点
                length = np.linalg.norm(start_point - end_point)  # 计算欧氏距离
                row_lengths.append(length)
                if detail_length:
                    scale_ = max(1, int(scale))
                    cv2.circle(img_left, np.uint16(np.around(corners_left[i * c][0])), scale_ * 4, (0, 0, 255),
                               scale_ * 4)
                    cv2.circle(img_left, np.uint16(np.around(corners_left[(i + 1) * c - 1][0])), scale_ * 4,
                               (0, 0, 255), scale_ * 4)
                    cv2.line(img_left, np.uint16(np.around(corners_left[i * c][0])),
                             np.uint16(np.around(corners_left[(i + 1) * c - 1][0])), (0, 0, 255), scale_)
                    cv2.circle(img_right, np.uint16(np.around(corners_right[i * c][0])), scale_ * 4, (0, 0, 255),
                               scale_ * 4)
                    cv2.circle(img_right, np.uint16(np.around(corners_right[(i + 1) * c - 1][0])), scale_ * 4,
                               (0, 0, 255), scale_ * 4)
                    cv2.line(img_right, np.uint16(np.around(corners_right[i * c][0])),
                             np.uint16(np.around(corners_right[(i + 1) * c - 1][0])), (0, 0, 255), scale_)

            # 计算每一列的首尾长度
            col_lengths = []
            for j in range(c):
                start_point = point_corner[j]  # 每列的第一个点
                end_point = point_corner[(r - 1) * c + j]  # 每列的最后一个点
                length = np.linalg.norm(start_point - end_point)  # 计算欧氏距离
                col_lengths.append(length)
                if detail_length:
                    cv2.circle(img_left, np.uint16(np.around(corners_left[j][0])),
                               scale_ * 2, (0, 255, 0), scale_ * 2)
                    cv2.circle(img_left,
                               np.uint16(np.around(corners_left[(r - 1) * c + j][0])),
                               scale_ * 2, (0, 255, 0), scale_ * 2)
                    cv2.line(img_left, np.uint16(np.around(corners_left[j][0])),
                             np.uint16(np.around(corners_left[(r - 1) * c + j][0])), (0, 255, 0), scale_)

                    cv2.circle(img_right, np.uint16(np.around(corners_right[j][0])),
                               scale_ * 2, (0, 255, 0), scale_ * 2)
                    cv2.circle(img_right,
                               np.uint16(np.around(corners_right[(r - 1) * c + j][0])),
                               scale_ * 2, (0, 255, 0), scale_ * 2)
                    cv2.line(img_right, np.uint16(np.around(corners_right[j][0])),
                             np.uint16(np.around(corners_right[(r - 1) * c + j][0])), (0, 255, 0), scale_)

            # 打印每一行和每一列的首尾长度
            e_row = np.array(row_lengths) - self.square_size * (r - 1)
            e_col = np.array(row_lengths) - self.square_size * (r - 1)
            # 计算真实世界坐标之间的欧氏距离
            max_error = np.max(np.stack([e_row, e_col], axis=0))
            mean_error = np.mean(np.stack([e_row, e_col], axis=0))
            img = np.concatenate((img_left, img_right), axis=1)
            drawLine(img, 16, max(1, int(scale)))

            if show_3d:
                import matplotlib.pyplot as plt
                fig = plt.figure(figsize=(12, 12))
                ax = fig.add_subplot(111, projection='3d')
                plt.cla()
                coodinates = np.array(point_corner)
                ax.scatter(coodinates[:, 0], coodinates[:, 1], coodinates[:, 2], color='red')
                plt.draw()
                plt.show()
                print("每一行的首尾长度误差：", e_row, "最大误差：", np.max(e_row))
                print("每一列的首尾长度误差：", e_col, "最大误差：", np.max(e_col))
            # img = np.concatenate((img_left, img_right), axis=1)
            # img_c = np.concatenate((img_, img), axis=0)
            # if show:
            #     show_image('align', img, 0, 0, scale=scale, time=-1)
            return align_error, max_error, mean_error, img
        else:
            cv2.drawChessboardCorners(img_left, self.pattern_size, corners_left, True)
            cv2.drawChessboardCorners(img_right, self.pattern_size, corners_right, True)
            img = np.concatenate((img_left, img_right), axis=1)
            drawLine(img, 16, max(1, int(scale)))

        return align_error, None, None, img

    def evaluate_error(self, num=0, show=False, train=False, save=False, image_paths=None, camera=None):
        max_error = []
        mean_error = []
        align_error = []
        if image_paths is None or len(image_paths) == 0 :
            image_paths = self.image_paths_test
        if image_paths is None or len(image_paths) == 0 :
            image_paths = self.image_paths
        if image_paths is None or len(image_paths) == 0:
            return

        num = len(image_paths) if num <= 0 else min(num, len(image_paths))
        if show or train or save:
            pbar = image_paths[:num]
        else:
            pbar = tqdm(image_paths[:num], desc="Calculating error...")
        if camera:
            camera_matrix_left = camera[0]
            dist_coeffs_left = camera[1]
            camera_matrix_right = camera[2]
            dist_coeffs_right = camera[3]
            R = camera[4]
            T = camera[5]
        else:
            camera_matrix_left = self.camera_matrix_left
            dist_coeffs_left = self.dist_coeffs_left
            camera_matrix_right = self.camera_matrix_right
            dist_coeffs_right = self.dist_coeffs_right
            R = self.R
            T = self.T
        R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(camera_matrix_left, dist_coeffs_left, camera_matrix_right,
                                                    dist_coeffs_right, self.imageSize, R, T)
        map1_left, map2_left = cv2.initUndistortRectifyMap(camera_matrix_left, dist_coeffs_left, R1, P1, self.imageSize, cv2.CV_32FC1)
        map1_right, map2_right = cv2.initUndistortRectifyMap(camera_matrix_right, dist_coeffs_right, R2, P2, self.imageSize, cv2.CV_32FC1)
        for l, r in pbar:
            img_left = cv2.imread(l)
            img_right = cv2.imread(r)
            # img_left_rectified, img_right_rectified = self.rectify_image(img_left, img_right)
            img_left_rectified = cv2.remap(img_left, map1_left, map2_left, cv2.INTER_LINEAR)
            img_right_rectified = cv2.remap(img_right, map1_right, map2_right, cv2.INTER_LINEAR)
            align_error_, max_error_, mean_error_, img = self._calculate_error(img_left_rectified, img_right_rectified,
                                                                                   detail_align=show,  detail_length=False, show_3d=False, P1=P1, P2=P2)
            if img is not None:
                if show:
                    img_ = np.concatenate((img_left, img_right), axis=1)
                    imgWidth = img_left_rectified.shape[1]  # 每行的第一个点
                    scale = self.screen_size[0] / imgWidth

                    drawLine(img_, 16, max(1, int(scale)))
                    # img = np.concatenate((img_left_rectified, img_right_rectified), axis=1)
                    img_c = np.concatenate((img_, img), axis=0)
                    show_image('before/after', img_c, 0, 50, scale=scale, time=-1)

                if save:
                    dir, name = os.path.dirname(l), os.path.basename(l)
                    os.makedirs(os.path.join(dir, 'rectify_error'), exist_ok=True)
                    cv2.imwrite(f"{os.path.join(dir, 'rectify_error', name)}", img)
                    print(f"保存误差图片: {os.path.join(dir, 'rectify_error', name)}")
            if align_error_ is None or max_error_ is None or mean_error_ is None:
                if not train:
                    print(f"无法计算误差: {l} {r}")
                continue
            if max_error is not None and mean_error is not None:
                max_error.append(max_error_)
                mean_error.append(mean_error_)
            if align_error_ is not None:
                align_error.append(align_error_)
        if not train:
            if len(max_error) > 0:
                print(f"统计样本: {len(max_error)} pairs,", end=' ')
                print(
                    f"最大误差: {np.array(max_error).max()} mm, 平均误差: {np.array(mean_error).mean()} mm,", end=' ')
            if len(align_error) > 0:
                print(
                    f"对齐误差: {np.array(align_error).mean()} pixel")
        return np.array(align_error).mean(), np.array(max_error).max(), np.array(mean_error).mean()
    # **********************************************************

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
        if os.path.exists(f"stereo_calibration_data.json"):
            i = 0
            while os.path.exists(f"stereo_calibration_data_{i}.json"):
                i += 1
            file_path = file_path if file_path else f"stereo_calibration_data_{i}.json"
        else:
            file_path = file_path if file_path else f"stereo_calibration_data.json"
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
        with open(file_path, 'w') as f:
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
        with open(file_path, 'r') as f:
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
        list01 = list(data.keys())
        print(list01)
        if camera_side.startswith('left'):
            self.camera_matrix_left = data['M']
            self.dist_coeffs_left = data['d']
            self.ret = data['epe']
        elif camera_side.startswith('right'):
            self.camera_matrix_right = data['M']
            self.dist_coeffs_right = data['d']
            self.ret = data['epe']
        else:
            self._load_images('left')
            self.camera_matrix = data['M']
            self.dist_coeffs = data['d']
            self.reet = data['epe']

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
            return  args
        else:
            print(f"{camera_side} camera calibration failed")
            return  False


# 示例使用代码
if __name__ == "__main__":
    # 初始化标定类，假设标定板有 7x7 个内角点，每个棋盘格大小为 0.040 米
    pattern_size = (7, 7)
    square_size = 40
    # image_dir = r'E:\xiaoyu\videos2images_f'
    image_dir = r'D:\MyData\Desktop\BinocularReconstrution\stereo-app-250406\new\project1\capture\20250602002853'


    stereo_calib = CameraCalibrator(pattern_size, square_size, image_dir, detect_num=10, shuffle=True, filter_files=False)
    # stereo_calib.show_images(align_err=False, detect=True, rectify=False)
    # stereo_calib.calibrate()
    # print(stereo_calib.camera_matrix_left)
    # stereo_calib.save_json('calibration_data_04.json')

    # stereo_calib.calibrate_single_camera('left')
    # stereo_calib.save_single_json('calibration_data_left3.json')
    # stereo_calib.load_single_json('calibration_data_left.json',  'left')
    # stereo_calib.load_single_json('calibration_data_right.json',  'right')
    # stereo_calib.calibrate()
    # stereo_calib.auto_tune_parameters()
    # stereo_calib.generate_detector()
    # stereo_calib.filter_image_pairs()
    # ret = stereo_calib.value_stereo_calibrate(result_dir='value2.csv')
    # stereo_calib.save_json('calibration_value_iter.json')detail=False, save=False)

    # 单目标定示例
    stereo_calib.calibrate_single_camera('snap')
    stereo_calib.rectify_and_save_images_single_camera(show=True)
    # stereo_calib.save_single_json('left_single_camera_calibration.json')
    # stereo_calib.rectify_and_save_images_single_camera()
    # stereo_calib.calibrate_single_camera('right')
    # stereo_calib.save_single_json('right_single_camera_calibration.npz')
    # stereo_calib.load_single_json('left_single_camera_calibration.json', 'left')
    # stereo_calib.load_single_json('right_single_camera_calibration.json', 'right')

    # 增进式标定
    # ret = stereo_calib.value_calibrate()
    # stereo_calib.save_json('calibration_data_value.json')
