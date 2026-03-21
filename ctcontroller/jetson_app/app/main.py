import os
import time
import signal
import cv2
from ultralytics import YOLO
import Jetson.GPIO as GPIO

THRESHOLD = float(os.getenv("THRESHOLD", "0.8"))
TARGET_CLS = int(os.getenv("TARGET_CLS", "38"))
GPIO_PIN = int(os.getenv("GPIO_PIN", "33"))
SLEEP_SEC = float(os.getenv("SLEEP_SEC", "0.05"))

RUNNING = True

def handle_signal(signum, frame):
    global RUNNING
    print(f"Received signal {signum}, stopping...")
    RUNNING = False

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

def build_gst_pipeline():
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), width=(int)1080, height=(int)720, "
        "format=(string)NV12, framerate=(fraction)60/1 ! "
        "nvvidconv ! "
        "video/x-raw, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! "
        "appsink"
    )

def main():
    model_path = os.getenv("MODEL_PATH", "./models/Yolo-cnw.pt")
    output_dir = os.getenv("OUTPUT_DIR", "./outputs")

    print("Starting custom Jetson inference app")
    print(f"MODEL_PATH={model_path}")
    print(f"OUTPUT_DIR={output_dir}")
    print(f"THRESHOLD={THRESHOLD}")
    print(f"TARGET_CLS={TARGET_CLS}")
    print(f"GPIO_PIN={GPIO_PIN}")
    print(f"SLEEP_SEC={SLEEP_SEC}")

    os.makedirs(output_dir, exist_ok=True)

    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(GPIO_PIN, GPIO.OUT, initial=GPIO.LOW)
    print("GPIO initialized")

    cam = None
    try:
        model = YOLO(model_path)
        print("Model loaded successfully")

        gst_pipeline = build_gst_pipeline()
        print("Opening CSI camera...")
        cam = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

        if not cam.isOpened():
            print("ERROR: Could not open CSI camera")
            return

        print("Camera opened successfully")

        frame_idx = 0

        while RUNNING:
            ret, frame = cam.read()
            if not ret:
                print("WARNING: Failed to read frame")
                time.sleep(SLEEP_SEC)
                continue

            frame_idx += 1
            results = model(frame, verbose=False)
            result = results[0]
            boxes = result.boxes

            target_count = 0
            if boxes is not None and boxes.cls is not None and boxes.conf is not None:
                for cls_id, conf in zip(boxes.cls.tolist(), boxes.conf.tolist()):
                    if int(cls_id) == TARGET_CLS and float(conf) > THRESHOLD:
                        target_count += 1

            weed_detected = target_count > 0

            if not weed_detected:
                GPIO.output(GPIO_PIN, GPIO.HIGH)
                gpio_state = "HIGH"
            else:
                GPIO.output(GPIO_PIN, GPIO.LOW)
                gpio_state = "LOW"

            print(
                f"frame={frame_idx} weed_detected={weed_detected} "
                f"target_count={target_count} gpio={gpio_state}"
            )

            time.sleep(SLEEP_SEC)

    finally:
        if cam is not None:
            cam.release()
        GPIO.output(GPIO_PIN, GPIO.LOW)
        GPIO.cleanup()
        print("GPIO cleaned up")
        print("Application exiting")

if __name__ == "__main__":
    main()