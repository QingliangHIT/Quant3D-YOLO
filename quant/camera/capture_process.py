"""独立采集进程：从摄像头持续读帧并写入管道/队列。"""

import time
import cv2
from queue import Full


def capture_frames(camera_index, width, height, frame_queue, barrier=None, conn=None):
    """Capture frames from camera and put into queue"""

    def process_cap(camera_index, width, height):
        if conn:
            conn.send({"type": "status", "message": "🎥 Camera loading...", "value": 0})

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            cap.release()
            if conn:
                conn.send({"type": "error", "message": "Camera cannot be opened", "value": 3000})
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        fps = int(cap.get(cv2.CAP_PROP_FPS))  # 某些驱动返回 0，由调用方决定默认值
        if conn:
            conn.send({"type": "ready", "message": f"🎥 Camera ready: {width}x{height} @ {fps} FPS", "value": 3000,
                       "width": width, "height": height, "fps": fps})
        return cap

    # Status variables
    running = True
    capture = True
    cap = process_cap(camera_index, width, height)
    while running:
        if conn and conn.poll():
            try:
                msg = conn.recv()
                cmd = msg.get("cmd") if isinstance(msg, dict) else None
                if cmd == 'run':
                    capture = True
                    conn.send({"type": "status", "message": "Capturing...", "value": 3000})
                elif cmd == 'stop':
                    running = False
                    capture = False
                elif cmd == 'stay':
                    capture = False
                elif cmd == 'set':
                    # 换相机前先释放旧句柄，且打开失败时保持 cap 为 None 而不是复用旧设备
                    if cap is not None:
                        cap.release()
                    cap = process_cap(msg["camera_index"], msg["width"], msg["height"])
                elif cmd == 'focus' and cap is not None:
                    if msg['val'] == 0:
                        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                    elif msg['val'] == -1:
                        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                    else:
                        cap.set(cv2.CAP_PROP_FOCUS, msg['val'])

            except EOFError:
                running = False  # Pipe has been closed
            except (OSError, KeyError) as exc:
                # 管道断裂或消息不完整时退出，避免子进程带著无效句柄空转
                print(f"Capture process pipe error: {exc}")
                running = False

        if capture:
            if cap is None:
                # 相机未能打开：不读帧、只等待新指令，避免 AttributeError 拖崩子进程
                time.sleep(0.2)
                continue
            if barrier:
                barrier.wait()
            ret_grab = cap.grab()
            if ret_grab:
                ret_retrieve, frame = cap.retrieve()
                if ret_retrieve:
                    time_stamp = time.time()
                    try:
                        frame_queue.put((time_stamp, frame), block=False)  # Wait max 0.1 sec
                    except Full:
                        pass  # Drop current frame
        else:
            if conn:
                try:
                    conn.send({"type": "status", "message": "Video paused", "value": 0})
                except OSError:
                    running = False
            time.sleep(0.1)

    if cap is not None:
        cap.release()
