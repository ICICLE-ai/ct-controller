"""
Custom application manager for running a standalone Jetson inference app.
"""

import logging
from .application_manager import ApplicationManager
from .util import Status, ApplicationException

LOGGER = logging.getLogger("CT Controller")


class CustomJetsonAppManager(ApplicationManager):
    def __init__(self, runner, log_dir: str, cfg, allow_attaching: bool):
        super().__init__(runner, log_dir, cfg, allow_attaching)
        self.update_custom_config(cfg)

    def update_custom_config(self, cfg):
        self.run_dir = cfg.get("run_dir", f"{self.runner.home_dir}/custom_jetson_run")
        self.local_app_dir = cfg.get("local_app_dir", "")
        self.container_name = cfg.get("container_name", "custom-jetson-app")
        self.image_name = cfg.get("image_name", "custom-jetson-app:dev")
        self.jetson_model_path = cfg.get("jetson_model_path", "./models/Yolo-cnw.pt")
        self.jetson_threshold = cfg.get("jetson_threshold", 0.8)
        self.jetson_target_cls = cfg.get("jetson_target_cls", 38)
        self.jetson_gpio_pin = cfg.get("jetson_gpio_pin", 33)
        self.jetson_sleep_sec = cfg.get("jetson_sleep_sec", 0.05)

    def stage_app(self):
        if not self.local_app_dir:
            raise ApplicationException("local_app_dir is not set")

        LOGGER.info("Staging app from %s to %s", self.local_app_dir, self.run_dir)

        try:
            self.runner.mkdir(self.run_dir)
        except Exception:
            pass

        # LocalRunner path
        if getattr(self.runner, "ip_address", None) == "localhost":
            self.runner.get(self.local_app_dir, self.run_dir)
            staged_root = f"{self.run_dir}/{self.local_app_dir.rstrip('/').split('/')[-1]}"
        else:
            # RemoteRunner path: local -> remote upload
            staged_root = self.runner.copy_dir(self.local_app_dir, self.run_dir)

        LOGGER.info("Staged app root = %s", staged_root)
        self.staged_root = staged_root
        self.runner.run(f"find {staged_root} -maxdepth 3 -type f | sort > {self.run_dir}/staged_files.txt")

    def execute_app(self):
        app_main = f"{self.staged_root}/app/main.py"
        if not self.runner.file_exists(app_main):
            raise ApplicationException(f"App entrypoint not found: {app_main}")

        LOGGER.info("Executing staged app: %s", app_main)

        outlog = f"{self.log_dir}/custom_app_out.log"
        errlog = f"{self.log_dir}/custom_app_err.log"

        self.runner.tracked_run(
            f"cd {self.staged_root} && "
            f"MODEL_PATH='{self.jetson_model_path}' "
            f"THRESHOLD='{self.jetson_threshold}' "
            f"TARGET_CLS='{self.jetson_target_cls}' "
            f"GPIO_PIN='{self.jetson_gpio_pin}' "
            f"SLEEP_SEC='{self.jetson_sleep_sec}' "
            f"python3 app/main.py",
            outlog,
            errlog
        )

    def run_job(self):
        LOGGER.info("CustomJetsonAppManager.run_job() called")
        LOGGER.info("run_dir=%s", self.run_dir)
        LOGGER.info("local_app_dir=%s", self.local_app_dir)
        LOGGER.info("container_name=%s", self.container_name)
        LOGGER.info("image_name=%s", self.image_name)
        LOGGER.info("jetson_model_path=%s", self.jetson_model_path)
        LOGGER.info("jetson_threshold=%s", self.jetson_threshold)
        LOGGER.info("jetson_target_cls=%s", self.jetson_target_cls)
        LOGGER.info("jetson_gpio_pin=%s", self.jetson_gpio_pin)
        LOGGER.info("jetson_sleep_sec=%s", self.jetson_sleep_sec)

        self.status = Status.RUNNING
        self.stage_app()
        self.execute_app()
        self.status = Status.COMPLETE

    def shutdown_job(self):
        LOGGER.info("CustomJetsonAppManager.shutdown_job() called")
        self.status = Status.SHUTDOWN