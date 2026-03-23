"""
Custom application manager for running a standalone Jetson inference app
through the same lifecycle shape that ct-controller's API expects.
"""

import json
import logging
from textwrap import dedent

from .application_manager import ApplicationManager
from .util import Status, ApplicationException

LOGGER = logging.getLogger("CT Controller")


class CustomJetsonAppManager(ApplicationManager):
    def __init__(self, runner, log_dir: str, cfg, allow_attaching: bool):
        super().__init__(runner, log_dir, cfg, allow_attaching)
        self.update_custom_config(cfg)
        self.staged_root = None

    def update_custom_config(self, cfg):
        self.run_dir = cfg.get("run_dir", f"{self.runner.home_dir}/custom_jetson_run")
        self.local_app_dir = cfg.get("local_app_dir", "")
        self.container_name = cfg.get("container_name", "custom-jetson-app")
        self.image_name = cfg.get("image_name", "custom-jetson-app:dev")

        self.model_id = cfg.get("model_id", None)
        self.jetson_model_path = cfg.get("jetson_model_path", "")

        self.jetson_threshold = cfg.get("jetson_threshold", 0.8)
        self.jetson_target_cls = cfg.get("jetson_target_cls", 38)
        self.jetson_gpio_pin = cfg.get("jetson_gpio_pin", 33)
        self.jetson_sensor_id = cfg.get("jetson_sensor_id", 0)
        self.jetson_camera_width = cfg.get("jetson_camera_width", 1080)
        self.jetson_camera_height = cfg.get("jetson_camera_height", 720)
        self.jetson_camera_fps = cfg.get("jetson_camera_fps", 60)
        self.jetson_sleep_sec = cfg.get("jetson_sleep_sec", 0.05)

    #
    # Lifecycle methods expected by ctcontroller/api.py
    #

    def cleanup_environment(self):
        LOGGER.info("CustomJetsonAppManager.cleanup_environment() called")
        self.status = Status.PENDING
        try:
            if self.runner.file_exists(self.run_dir):
                LOGGER.info("Removing previous run_dir: %s", self.run_dir)
                self.runner.run(f"rm -rf {self.run_dir}")
        except Exception as exc:
            LOGGER.warning("cleanup_environment failed but ignored: %s", str(exc))

    def configure_app(self):
        LOGGER.info("CustomJetsonAppManager.configure_app() called")
        self.status = Status.PENDING

        self.stage_app()

        app_main = f"{self.staged_root}/app/main.py"
        if not self.runner.file_exists(app_main):
            raise ApplicationException(f"App entrypoint not found: {app_main}")

        # Model resolution priority:
        # 1. CT_CONTROLLER_MODEL_ID via Patra
        # 2. explicit CT_CONTROLLER_JETSON_MODEL_PATH
        if self.model_id:
            LOGGER.info("Using model_id from Patra: %s", self.model_id)
            model_url = self.resolve_model_url_from_patra(self.model_id)
            remote_model_path = f"{self.run_dir}/models/model.pt"
            self.download_model_to_target(model_url, remote_model_path)
            self.jetson_model_path = remote_model_path

        elif self.jetson_model_path:
            LOGGER.info("Using provided jetson_model_path: %s", self.jetson_model_path)
            if not self.runner.file_exists(self.jetson_model_path):
                raise ApplicationException(
                    f"Model path not found on target: {self.jetson_model_path}"
                )
        else:
            raise ApplicationException(
                "No model specified. Set CT_CONTROLLER_MODEL_ID or CT_CONTROLLER_JETSON_MODEL_PATH"
            )

        LOGGER.info("Final model path on target: %s", self.jetson_model_path)
        LOGGER.info("App configured successfully. staged_root=%s", self.staged_root)
        self.status = Status.READY

    def setup_environment(self):
        LOGGER.info("CustomJetsonAppManager.setup_environment() called")
        return

    def run_app(self):
        LOGGER.info("CustomJetsonAppManager.run_app() called")

        model_mount_src = self.jetson_model_path
        model_mount_dst = "/workspace/model.pt"

        outlog = f"{self.log_dir}/custom_app_out.log"
        errlog = f"{self.log_dir}/custom_app_err.log"

        cmd = dedent(f"""
        docker rm -f {self.container_name} >/dev/null 2>&1 || true && \
        docker run --rm -it \
        --name {self.container_name} \
        --runtime nvidia \
        --gpus all \
        --network host \
        --ipc host \
        --privileged \
        --device /dev/video0:/dev/video0 \
        -e NVIDIA_DRIVER_CAPABILITIES=all \
        -e MODEL_PATH={model_mount_dst} \
        -e THRESHOLD={self.jetson_threshold} \
        -e TARGET_CLS={self.jetson_target_cls} \
        -e GPIO_PIN={self.jetson_gpio_pin} \
        -e SENSOR_ID={self.jetson_sensor_id} \
        -e CAMERA_WIDTH={self.jetson_camera_width} \
        -e CAMERA_HEIGHT={self.jetson_camera_height} \
        -e CAMERA_FPS={self.jetson_camera_fps} \
        -v /tmp/argus_socket:/tmp/argus_socket \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -v /dev:/dev \
        -v /sys:/sys \
        -v /proc:/proc \
        -v {model_mount_src}:{model_mount_dst}:ro \
        {self.image_name}
        """).strip()

        LOGGER.info("Running docker app command: %s", cmd)
        self.status = Status.RUNNING
        self.runner.tracked_run(cmd, outlog, errlog)
        self.status = Status.COMPLETE

    def stop_app(self):
        LOGGER.info("CustomJetsonAppManager.stop_app() called")
        cmd = (
            f"docker stop {self.container_name} >/dev/null 2>&1 || true && "
            f"docker rm {self.container_name} >/dev/null 2>&1 || true"
        )
        self.runner.run(cmd)
        self.status = Status.SHUTDOWN

    def copy_results(self):
        LOGGER.info("CustomJetsonAppManager.copy_results() called")
        return

    def get_container_healths(self):
        LOGGER.info("CustomJetsonAppManager.get_container_healths() called")
        return {}

    #
    # Internal helpers
    #

    def stage_app(self):
        if not self.local_app_dir:
            raise ApplicationException("local_app_dir is not set")

        LOGGER.info("Staging app from %s to %s", self.local_app_dir, self.run_dir)

        try:
            self.runner.mkdir(self.run_dir)
        except Exception:
            pass

        if getattr(self.runner, "ip_address", None) == "localhost":
            self.runner.get(self.local_app_dir, self.run_dir)
            staged_root = f"{self.run_dir}/{self.local_app_dir.rstrip('/').split('/')[-1]}"
        else:
            staged_root = self.runner.copy_dir(self.local_app_dir, self.run_dir)

        LOGGER.info("Staged app root = %s", staged_root)
        self.staged_root = staged_root

        self.runner.run(
            f"find {staged_root} -maxdepth 3 -type f | sort > {self.run_dir}/staged_files.txt"
        )

    def resolve_model_url_from_patra(self, model_id: str) -> str:
        LOGGER.info("Resolving model URL from Patra for model_id=%s", model_id)

        patra_url = f"https://patraserver.pods.icicleai.tapis.io/download_mc?id={model_id}"
        cmd = f'curl -s "{patra_url}"'
        out = self.runner.run(cmd)

        try:
            data = json.loads(out)
        except Exception as exc:
            raise ApplicationException(
                f"Failed to parse Patra response as JSON: {str(exc)}; response={out}"
            )

        if "ai_model" not in data or "location" not in data["ai_model"]:
            raise ApplicationException(
                f"Patra response missing ai_model.location: {data}"
            )

        model_url = data["ai_model"]["location"]
        LOGGER.info("Resolved model URL: %s", model_url)
        return model_url

    def download_model_to_target(self, model_url: str, dest_path: str):
        LOGGER.info("Downloading model from %s to %s", model_url, dest_path)

        self.runner.run(f'mkdir -p "$(dirname "{dest_path}")"')
        self.runner.run(f'wget -O "{dest_path}" "{model_url}"')

        if not self.runner.file_exists(dest_path):
            raise ApplicationException(f"Model download failed: {dest_path}")

        LOGGER.info("Model downloaded successfully to %s", dest_path)

    #
    # Backward-compatible methods
    #

    def run_job(self):
        LOGGER.info("CustomJetsonAppManager.run_job() called")
        self.cleanup_environment()
        self.configure_app()
        self.setup_environment()
        self.run_app()

    def shutdown_job(self):
        LOGGER.info("CustomJetsonAppManager.shutdown_job() called")
        self.stop_app()