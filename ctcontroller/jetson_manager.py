import json
import logging
from textwrap import dedent

from .application_manager import ApplicationManager
from .util import Status, ApplicationException

LOGGER = logging.getLogger("CT Controller")


class JetsonManager(ApplicationManager):
    def __init__(self, runner, log_dir: str, cfg, allow_attaching: bool):
        super().__init__(runner, log_dir, cfg, allow_attaching)
        self.update_config(cfg)
        self.status = Status.PENDING

    def update_config(self, cfg):
        changed = super().update_config(cfg)

        advanced = cfg.get("advanced_app_vars") or {}
        jetson_cfg = advanced.get("jetson", {})

        def pick(name, default=None):
            if name in jetson_cfg:
                return jetson_cfg[name]
            return cfg.get(name, default)

        new_run_dir = pick('run_dir', f'{self.runner.home_dir}/jetson_run')
        if not hasattr(self, 'run_dir') or self.run_dir != new_run_dir:
            self.run_dir = new_run_dir
            changed = True

        new_image_name = pick('image_name', 'habg21/jetson-weed-infer')
        if not hasattr(self, 'image_name') or self.image_name != new_image_name:
            self.image_name = new_image_name
            changed = True

        new_container_name = pick('container_name', 'weed_infer_test')
        if not hasattr(self, 'container_name') or self.container_name != new_container_name:
            self.container_name = new_container_name
            changed = True

        new_model_id = pick('model_id')
        if not hasattr(self, 'model_id') or self.model_id != new_model_id:
            self.model_id = new_model_id
            changed = True

        new_model_container_path = pick('model_container_path', '/workspace/model.pt')
        if not hasattr(self, 'model_container_path') or self.model_container_path != new_model_container_path:
            self.model_container_path = new_model_container_path
            changed = True

        new_threshold = pick('threshold', '0.8')
        if not hasattr(self, 'threshold') or self.threshold != new_threshold:
            self.threshold = new_threshold
            changed = True

        new_target_cls = pick('target_cls', '38')
        if not hasattr(self, 'target_cls') or self.target_cls != new_target_cls:
            self.target_cls = new_target_cls
            changed = True

        new_gpio_pin = pick('gpio_pin', '33')
        if not hasattr(self, 'gpio_pin') or self.gpio_pin != new_gpio_pin:
            self.gpio_pin = new_gpio_pin
            changed = True

        new_sensor_id = pick('sensor_id', '0')
        if not hasattr(self, 'sensor_id') or self.sensor_id != new_sensor_id:
            self.sensor_id = new_sensor_id
            changed = True

        new_camera_width = pick('camera_width', '1080')
        if not hasattr(self, 'camera_width') or self.camera_width != new_camera_width:
            self.camera_width = new_camera_width
            changed = True

        new_camera_height = pick('camera_height', '720')
        if not hasattr(self, 'camera_height') or self.camera_height != new_camera_height:
            self.camera_height = new_camera_height
            changed = True

        new_camera_fps = pick('camera_fps', '60')
        if not hasattr(self, 'camera_fps') or self.camera_fps != new_camera_fps:
            self.camera_fps = new_camera_fps
            changed = True

        new_display = pick('display', ':0')
        if not hasattr(self, 'display') or self.display != new_display:
            self.display = new_display
            changed = True

        new_gpio_init_cmd = pick('gpio_init_cmd')
        if not hasattr(self, 'gpio_init_cmd') or self.gpio_init_cmd != new_gpio_init_cmd:
            self.gpio_init_cmd = new_gpio_init_cmd
            changed = True

        return changed

    def cleanup_environment(self):
        if self.allow_attaching and self.get_application_health() != Status.PENDING:
            if self.get_application_health() == Status.RUNNING:
                LOGGER.info('Jetson application already running.')
                self.status = Status.RUNNING
                return
            if self.get_application_health() == Status.FAILED:
                LOGGER.info('Jetson application failed earlier. Stopping old container.')
                self.stop_app(ignore_failure=True)

        self.runner.run(f'rm -rf {self.run_dir}')
        self.runner.run(f'mkdir -p {self.run_dir}')
        self.status = Status.SETTINGUP

    def configure_app(self):
        if not self.model_id:
            raise ApplicationException('model_id is required')

        LOGGER.info("Pulling the required application image: %s", self.image_name)
        self.runner.run(f'docker pull {self.image_name}')

        model_url = self.resolve_model_url_from_patra(self.model_id)
        remote_model_path = f'{self.run_dir}/models/model.pt'
        self.download_model_to_target(model_url, remote_model_path)
        self.model_host_path = remote_model_path

        self.runner.run(
            dedent(f"""
            cat > {self.log_dir}/ct_controller.yml << 'EOF'
            app_type: jetson_infer
            image_name: {self.image_name}
            container_name: {self.container_name}
            model_id: {self.model_id}
            model_container_path: {self.model_container_path}
            threshold: {self.threshold}
            target_cls: {self.target_cls}
            gpio_pin: {self.gpio_pin}
            sensor_id: {self.sensor_id}
            camera_width: {self.camera_width}
            camera_height: {self.camera_height}
            camera_fps: {self.camera_fps}
            run_dir: {self.run_dir}
            EOF
            """).strip()
        )

        self.status = Status.READY

    def setup_environment(self):
        self.status = Status.SETTINGUP
        self.runner.run(f'docker pull {self.image_name}')
        self.status = Status.READY

    def run_app(self):
        outlog = f'{self.log_dir}/ct_out.log'
        errlog = f'{self.log_dir}/ct_err.log'

        self.runner.run("xhost +local:root")
        # self.runner.run("sudo busybox devmem 0x2434040 w 0x4")
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
        -e MODEL_PATH={self.model_container_path} \
        -e THRESHOLD={self.threshold} \
        -e TARGET_CLS={self.target_cls} \
        -e GPIO_PIN={self.gpio_pin} \
        -e SENSOR_ID={self.sensor_id} \
        -e CAMERA_WIDTH={self.camera_width} \
        -e CAMERA_HEIGHT={self.camera_height} \
        -e CAMERA_FPS={self.camera_fps} \
        -v /tmp/argus_socket:/tmp/argus_socket \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -v /dev:/dev \
        -v /sys:/sys \
        -v /proc:/proc \
        -v {self.model_host_path}:{self.model_container_path}:ro \
        {self.image_name}
        """).strip()

        LOGGER.info("Running docker app command: %s", cmd)
        self.status = Status.RUNNING
        self.runner.tracked_run(cmd, outlog, errlog)
        self.status = Status.COMPLETE

    def stop_app(self, ignore_failure=False):
        cmd = (
            f"docker stop {self.container_name} >/dev/null 2>&1 || true && "
            f"docker rm {self.container_name} >/dev/null 2>&1 || true"
        )
        try:
            self.runner.run(cmd)
        except Exception as e:
            if not ignore_failure:
                raise ApplicationException(f'Failed stopping Jetson container: {e}')
        self.status = Status.SHUTDOWN

    def copy_results(self):
        return

    def run_job(self):
        self.cleanup_environment()
        self.configure_app()
        self.setup_environment()
        self.run_app()

    def shutdown_job(self):
        self.stop_app(ignore_failure=True)

    def get_expected_images(self):
        return [self.image_name] if self.image_name else []

    def get_running_images(self):
        running = self.runner.run('docker ps --filter "status=running" --format "{{.Image}}"').splitlines()
        exited = self.runner.run('docker ps --filter "status=exited" --format "{{.Image}}"').splitlines()
        return running, exited

    def get_container_healths(self, images=None):
        if images is None:
            images = self.get_expected_images()

        running, exited = self.get_running_images()
        healths = {}
        for image in images:
            if image in running:
                healths[image] = Status.RUNNING.name
            elif image in exited:
                healths[image] = Status.FAILED.name
            else:
                healths[image] = Status.PENDING.name
        return healths

    def get_application_health(self):
        healths = self.get_container_healths()
        if not healths:
            return Status.PENDING

        vals = set(healths.values())
        if vals == {Status.RUNNING.name}:
            return Status.RUNNING
        if Status.FAILED.name in vals:
            return Status.FAILED
        if vals == {Status.PENDING.name}:
            return Status.PENDING
        return Status.PENDING

    def get_status(self):
        if self.status in [
            Status.RUNNING, Status.COMPLETE, Status.SETTINGUP,
            Status.READY, Status.SHUTDOWN
        ]:
            return self.status
        return self.get_application_health()

    def resolve_model_url_from_patra(self, model_id: str) -> str:
        patra_url = f"https://patraserver.pods.icicleai.tapis.io/download_mc?id={model_id}"
        out = self.runner.run(f'curl -s "{patra_url}"')

        try:
            data = json.loads(out)
        except Exception as exc:
            raise ApplicationException(
                f"Failed to parse Patra response as JSON: {exc}; response={out}"
            )

        if "ai_model" not in data or "location" not in data["ai_model"]:
            raise ApplicationException(
                f"Patra response missing ai_model.location: {data}"
            )

        return data["ai_model"]["location"]

    def download_model_to_target(self, model_url: str, dest_path: str):
        self.runner.run(f'mkdir -p "$(dirname "{dest_path}")"')
        self.runner.run(f'wget -O "{dest_path}" "{model_url}"')

        if not self.runner.file_exists(dest_path):
            raise ApplicationException(f"Model download failed: {dest_path}")