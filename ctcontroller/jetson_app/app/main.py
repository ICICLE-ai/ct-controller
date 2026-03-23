import os
import time

import cv2
import Jetson.GPIO as GPIO
import torch
from ultralytics import YOLO


MODEL_PATH = os.environ.get("MODEL_PATH", "./Yolo-cnw.pt")
THRESHOLD = float(os.environ.get("THRESHOLD", "0.8"))
TARGET_CLS = int(os.environ.get("TARGET_CLS", "38"))
GPIO_PIN = int(os.environ.get("GPIO_PIN", "33"))
SENSOR_ID = int(os.environ.get("SENSOR_ID", "0"))
CAMERA_WIDTH = int(os.environ.get("CAMERA_WIDTH", "1080"))
CAMERA_HEIGHT = int(os.environ.get("CAMERA_HEIGHT", "720"))
CAMERA_FPS = int(os.environ.get("CAMERA_FPS", "60"))


def led_on() -> None:
    GPIO.output(GPIO_PIN, GPIO.HIGH)


def led_off() -> None:
    GPIO.output(GPIO_PIN, GPIO.LOW)


def build_gstreamer_pipeline() -> str:
    return (
        f"nvarguscamerasrc sensor-id={SENSOR_ID} ! "
        f"video/x-raw(memory:NVMM), width=(int){CAMERA_WIDTH}, "
        f"height=(int){CAMERA_HEIGHT}, format=(string)NV12, "
        f"framerate=(fraction){CAMERA_FPS}/1 ! "
        "nvvidconv ! "
        "video/x-raw, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! "
        "appsink drop=true max-buffers=1 sync=false"
    )


def main() -> None:
    print("Starting Jetson weed inference", flush=True)
    print(f"MODEL_PATH={MODEL_PATH}", flush=True)
    print(f"THRESHOLD={THRESHOLD}", flush=True)
    print(f"TARGET_CLS={TARGET_CLS}", flush=True)
    print(f"GPIO_PIN={GPIO_PIN}", flush=True)
    print(f"SENSOR_ID={SENSOR_ID}", flush=True)
    print(f"CAMERA_WIDTH={CAMERA_WIDTH}", flush=True)
    print(f"CAMERA_HEIGHT={CAMERA_HEIGHT}", flush=True)
    print(f"CAMERA_FPS={CAMERA_FPS}", flush=True)
    print(f"TORCH_CUDA_AVAILABLE={torch.cuda.is_available()}", flush=True)

    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(GPIO_PIN, GPIO.OUT, initial=GPIO.HIGH)

    model = YOLO(MODEL_PATH)

    gst_pipeline = build_gstreamer_pipeline()
    print(f"GSTREAMER_PIPELINE={gst_pipeline}", flush=True)

    cam = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

    if not cam.isOpened():
        print("ERROR: Could not open camera", flush=True)
        raise SystemExit(1)

    frame_id = 0
    prev = time.time()

    try:
        while True:
            ret, frame = cam.read()
            if not ret:
                print("ERROR: Failed to read frame", flush=True)
                break

            frame_id += 1
            t0 = time.time()

            results = model(frame, verbose=False)
            boxes = results[0].boxes

            weed_count = 0
            if boxes is not None and boxes.cls is not None and boxes.conf is not None:
                weed_count = int(
                    torch.sum((boxes.cls == TARGET_CLS) & (boxes.conf > THRESHOLD)).item()
                )

            if weed_count > 0:
                led_on()
                weed_status = "DETECTED"
            else:
                led_off()
                weed_status = "NOT_DETECTED"

            t1 = time.time()
            inf_ms = (t1 - t0) * 1000.0
            fps = 1.0 / (t1 - prev) if (t1 - prev) > 0 else 0.0
            prev = t1

            print(
                f"frame={frame_id} weed={weed_status} count={weed_count} "
                f"inference_ms={inf_ms:.2f} fps={fps:.2f}",
                flush=True
            )

    except KeyboardInterrupt:
        print("Stopping...", flush=True)

    finally:
        cam.release()
        GPIO.cleanup()
        print("Cleaned up camera and GPIO", flush=True)


if __name__ == "__main__":
    main()