"""
Contains the CameraTrapsManager class which manages the camera traps application on
a remote node
"""

import os
import re
import logging
import json
import shutil
import filecmp
import tempfile
from textwrap import dedent
from pathlib import Path
import validators
from .application_manager import ApplicationManager
from .remote import RemoteRunner
from .local import LocalRunner
from .util import ApplicationException, capture_shell, Status

LOGGER = logging.getLogger("CT Controller")


# Class to manage the camera traps application on a remote node
class CameraTrapsManager(ApplicationManager):
    """
    A class to manage the running of the Camera Traps application on a remote node.
    It generates the appropriate docker-compose.yml file based on configuration
    requirements passed into it, runs the application, stores the output on the local machine,
    shuts down the docker containers on completion, and cleans up the remote run directory.

    Attributes:
        runner (RemoteRuner): runner attached to the target node
        log_dir (str): local directory where all output related to this run should be stored
        run_dir (str): remote directory where the camera traps application will be run
        version (str): the release version of camera traps that will be run
        gpu (bool): whether to run camera traps on the GPU
        model (str): 
        input (str): 
        allow_attaching (bool): whether to allow attaching to an existing run of camera traps
        advanced (dict): a key-pair of advanced runtime options for camera traps

    Methods:
        generate_cfg_file(rmt_path): 
            Generates a config file and copies it to the remote node that will run camera traps
        get_video_device():
        cleaup_environment():
        setup_environment():
        configure_app():
        setup_app():
        remove_app():
        run_app():
        stop_app():
        copy_results():
        run_job():
        shutdown_job():
        Functions for asynchronous jobs:
        get_expected_images():
        get_running_images():
        stop_running_containers():
        get_application_health():
        get_status(): Updates the status of the jb
    """

    def __init__(self, runner: RemoteRunner | LocalRunner, log_dir: str, cfg, allow_attaching: bool):
        """
        Constructions all necessary attributes for a CameraTrapsManager object
            
            Parameters:
                runner (RemoteRunner|LocalRunner): a runner attached to the target node
                log_dir (str): local directory where all output related to this run should be stored
                cfg (dict): a dictionary of configuration parameters and values passed from the
                            Controller object
        """

        super().__init__(runner, log_dir, cfg, allow_attaching)

        self.update_config(cfg)
        self.keywords = ['tapis', 'icicle', 'iud2i']

    def parse_model(self, model):
        if '.pt' in model:
            return 'file'
        else:
            return 'id'

    def check_cache(self, model):
        if hasattr(self, 'model_cache') and self.model_cache:
            cached_model = Path(self.model_cache) / model
            if cached_model.is_file():
                return cached_model

    def generate_cfg_file(self):
        """Generates a config file and copies it to the remote node that will run camera traps"""

        rmt_pth = self.run_dir_parent
        relpath = os.path.relpath(self.run_dir, rmt_pth)
        cfg_str = ''
        cfg_str += f'install_dir: {relpath}\n'
        cfg_str += f'device_id: {self.runner.device_id}\n'
        cfg_str += f'user_id: {self.user_id}\n'
        cfg_str += f'experiment_id: {self.experiment_id}\n'
        cfg_str += f'mode: {self.mode}\n'
        if self.version:
            cfg_str += f'ct_version: {self.version}\n'
        if self.gpu:
            cfg_str += f'use_gpu_in_scoring: {self.gpu}\n'
        if self.model:
            if self.parse_model(self.model) == 'file':
                cached_model = self.check_cache(self.model)
                if cached_model:
                    self.model = cached_model
                cfg_str += f'local_model_path: {self.model}\n'
            else:
                cfg_str += f'model_id: {self.model}\n'
        if self.input:
            if validators.url(self.input):
                if self.input_dataset_type == 'image':
                    cfg_str += 'use_image_url: true\n'
                    cfg_str += f'source_image_url: {self.input}\n'
                elif self.input_dataset_type == 'video':
                    cfg_str += 'source_video_url: {self.input}\n'
            else:
                self.status = Status.FAILED
                raise ApplicationException(f"Input dataset source: {self.input} is not a valid url")
        if self.mode == 'video_simulation':
            cfg_str += f'motion_video_device: {self.get_video_device()}\n'
        if self.advanced:
            for key, val in self.advanced.items():
                cfg_str += f'{key}: {val}\n'
        cfg_str += f'inference_server: false\n'
        if self.node_type == 'Jetson':
            cfg_str += 'image_scoring_plugin_image: tapis/image_scoring_plugin_py_nano_3.8\n'
            cfg_str += 'power_monitor_backend: jtop\n'
        if self.runner.cpu_arch == 'arm':
            cfg_str += 'power_monitor_backend: scaphandre\n'

        def _get_next_path(fpath):
            new_path = f'{fpath}.bak'
            if not os.path.exists(new_path):
                return new_path
            ver = 1
            while True:
                new_path = f'{fpath}.bak.{ver}'
                if not os.path.exists(new_path):
                    return new_path
                ver = ver + 1

        fpath = f'{self.log_dir}/ct_controller.yml'
        changed = True

        if not os.path.exists(fpath):
            with open(fpath, 'w', encoding='utf-8') as fil:
                fil.write(cfg_str)
        else:
            with tempfile.NamedTemporaryFile('w', delete=False, dir=os.path.dirname(fpath), encoding='utf-8') as fil:
                fil.write(cfg_str)
                tmp_path = fil.name
            if filecmp.cmp(tmp_path, fpath, shallow=False):
                os.remove(tmp_path)
                changed = False
            next_path = _get_next_path(fpath)
            shutil.move(fpath, next_path)
            shutil.move(tmp_path, fpath)

        self.runner.copy_file(fpath, f'{rmt_pth}/ct_controller.yml')


    def get_video_device(self):
        """
        Determines if there are any v4l2loopback devices available on the remote host
        """
        def _create_v4l2_device(all_devices):
            cmd = 'sudo modprobe v4l2loopback exclusive_caps=1 card_label=VirtualCam'
            self.runner.run(cmd)
        
        def _get_all_devices():
            dev_regex = re.compile(r'(/dev/video\d+)')
            v4l2devices = []
            cmd = 'v4l2-ctl --list-devices'
            out = self.runner.run(cmd)
            all_devices = dev_regex.findall(out)
            if 'v4l2loopback' in out:
                blocks = out.split('\n\n')
                for block in blocks:
                    if 'v4l2loopback' in block:
                        v4l2devices.extend(dev_regex.findall(block))
            return all_devices, v4l2devices
        
        def _is_v4l2loopback_available(device):
            cmd = f'v4l2-ctl -d {device} --all'
            out = self.runner.run(cmd)
            for line in out.splitlines():
                if line.strip().lower().startswith('driver name') and 'v4l2 loopback' in line.lower():
                    return True
            return False

        all_dev, v4l2_dev = _get_all_devices()
        if len(v4l2_dev) == 0:
            _create_v4l2_device(all_dev)
            all_dev, v4l2_dev = _get_all_devices()
        if len(v4l2_dev) > 0:
            for dev in v4l2_dev:
                if _is_v4l2loopback_available(dev):
                    return dev
        self.status = Status.FAILED
        raise ApplicationException(f'Video simulation mode selected but no compatible video devices found on remote server {self.runner.ip_address}')

    def update_config(self, cfg):
        changed = super().update_config(cfg)


        out, _ = capture_shell("curl -s https://api.github.com/repos/tapis-project/camera-traps/tags")
        try:
            latest = json.loads(out)[0]['name']
        except json.decoder.JSONDecodeError:
            latest = 'latest'

        new_run_dir = cfg.get('run_dir', f'{self.runner.home_dir}/ct_run')
        if not hasattr(self, 'run_dir') or new_run_dir != self.run_dir:
            self.run_dir = new_run_dir
            self.run_dir_parent = os.path.dirname(new_run_dir)
            changed = True

        new_version = cfg.get('ct_version', latest)
        if not hasattr(self, 'version') or new_version != self.version:
            self.version = new_version
            changed = True

        new_gpu = cfg.get('gpu')
        if not hasattr(self, 'gpu') or new_gpu != self.gpu:
            self.gpu = new_gpu
            changed = True

        new_model = cfg.get('model')
        if not hasattr(self, 'model') or self.model != new_model:
            self.model = new_model
            changed = True

        new_model_cache = cfg.get('model_cache')
        if not hasattr(self, 'model_cache') or self.model_cache != new_model_cache:
            self.model_cache = new_model_cache
            changed = True

        new_input = cfg.get('input')
        if not hasattr(self, 'input') or self.input != new_input:
            self.input = new_input
            changed = True

        new_node_type = cfg.get('node_type')
        if not hasattr(self, 'node_type') or self.node_type != new_node_type:
            self.node_type = new_node_type
            changed = True

        new_input_dataset_type = cfg.get('input_dataset_type', 'image')
        if not hasattr(self, 'input_dataset_type') or self.input_dataset_type != new_input_dataset_type:
            self.input_dataset_type = new_input_dataset_type
            changed = True

        new_mode = cfg.get('mode', 'simulation')
        if new_mode == 'simulation' and self.input_dataset_type == 'video':
            new_mode = 'video_simulation'
        if not hasattr(self, 'mode') or self.mode != new_mode:
            self.mode = new_mode
            changed = True
        return changed

    def cleanup_environment(self):
        if self.allow_attaching and self.get_application_health() != Status.PENDING:
            # There is already a healthy job running, no need to delete it and
            # start over
            if self.get_application_health() == Status.RUNNING:
                LOGGER.info('Application already running. Not recreating run directory.')
                self.status = Status.RUNNING
                return
            # There is a job already running but it is in a bad state. 
            # Stop any running images, and proceed with setup
            if self.get_application_health() == Status.FAILED:
                LOGGER.info('Application in failed state. Shutting down containers and recreating run directory')
                self.status = Status.FAILED
                self.stop_running_containers()
                self.remove_app()
            if self.get_application_health() == Status.PENDING:
                self.status = Status.PENDING
        if self.status not in [Status.PENDING, Status.COMPLETE]:
            raise ApplicationException(f'Unexpected status of {self.status.name} in application manager')
        # Prune containers on system
        prune_cmd = 'docker container prune -f; docker image prune -f'
        self.runner.run(prune_cmd)
        # Delete run directory
        self.remove_app()
        self.status = Status.SETTINGUP

    def setup_environment(self):
        # Prune images/containers and pull the latest images
        self.status = Status.SETTINGUP
        pull_cmd = dedent(f"""
        cd {self.run_dir}
        export DOCKER_CLIENT_TIMEOUT=30
        docker compose pull
        docker pull tapis/powerjoular
        """)
        self.runner.run(pull_cmd)
        self.status = Status.READY

    def configure_app(self):
        # Generate config file
        changed = self.generate_cfg_file()
        if changed == False:
            self.status = Status.READY
            return
        # if job is already running and the config file is the same, do nothing
        ###
        # Install to run directory and cleanup config
        proxy_cmd = f' -e HTTP_PROXY={self.runner.httpproxy} -e HTTPS_PROXY={self.runner.httpproxy}'
        install_cmd = dedent(f"""
        cd {self.run_dir_parent}
        export DOCKER_CLIENT_TIMEOUT=30
        docker pull tapis/camera-traps-installer:{self.version}
        docker run --rm --user `id -u`:`id -g` -v {self.run_dir_parent}:/host/ -e INSTALL_HOST_PATH={self.run_dir_parent} -e INPUT_FILE=ct_controller.yml{proxy_cmd if self.runner.httpproxy is not None else ""} tapis/camera-traps-installer:{self.version}
        rm ct_controller.yml
        """)
        out = self.runner.run(install_cmd)
        LOGGER.info(out)
        self.status = Status.READY

    def setup_app(self):
        """
        Sets up the remote node so that it is ready to run:
            1. Prunes any stopped containers
            2. Generates the config file
            3. Runs the custom installer
        """

        self.cleanup_environment()
        self.configure_app()
        self.setup_environment()

    def remove_app(self):
        """Deletes the run directory"""

        cmd = f'rm -rf {self.run_dir}'
        out = self.runner.run(cmd)
        LOGGER.info(out)

    def run_app(self):
        """
        Run docker compose up in the remote run directory and capture output in the
        local log directory.
        """

        # restart jtop service if running on a Jetson
        if self.node_type == 'Jetson':
            self.runner.run('systemctl restart jtop.service')
        # Run docker compose up to start camera traps code
        cmd = dedent(f"""
        cd {self.run_dir}
        export DOCKER_CLIENT_TIMEOUT=30
        docker compose pull
        docker compose up
        """)

        outlog = f'{self.log_dir}/ct_out.log'
        errlog = f'{self.log_dir}/ct_err.log'
        self.status = Status.RUNNING
        self.runner.tracked_run(cmd, outlog, errlog)
        self.status = Status.COMPLETE

    def stop_app(self, ignore_failure=False):
        """
        Run docker compose down in the remote run directory
        """

        cmd = dedent(f"""
        cd {self.run_dir}
        docker compose down
        docker container prune -f
        docker image prune -f
        """)
        out = self.runner.run(cmd)
        LOGGER.info(out)
        self.status = Status.COMPLETE


    def copy_results(self):
        self.status = Status.SAVING
        try:
            self.runner.get(self.run_dir, self.log_dir)
        except FileNotFoundError:
            self.status = Status.FAILED
            raise ApplicationException(f'Run directory {self.run_dir} could not be found on remote server {self.runner.ip_address}')
        except OSError:
            self.status = Status.FAILED
            raise ApplicationException(f'Copy of run directory {self.run_dir} from {self.runner.ip_address} to {self.log_dir} failed')
        self.status = Status.COMPLETE

    def run_job(self):
        """Setup the remote run directory and launch camera traps"""

        self.setup_app()
        self.run_app()

    def shutdown_job(self):
        """Shutdown the camera traps container and cleanup the run directory"""

        self.status = Status.SHUTTINGDOWN
        self.stop_app()
        self.copy_results()
        self.remove_app()
        self.status = Status.SHUTDOWN

    def get_expected_images(self):
        if self.runner.file_exists(f'{self.run_dir}/docker-compose.yml'):
            images = self.runner.run(f'cd {self.run_dir}; docker compose config --images')
            return images.splitlines()
        else:
            return []

    def get_running_images(self):
        running = [image for image in self.runner.run('docker ps --filter "status=running" --format "{{.Image}}"').splitlines() if 'ctcontroller' not in image]

        exited = [image for image in self.runner.run('docker ps --filter "status=exited" --format "{{.Image}}"').splitlines() if 'ctcontroller' not in image]
        return running, exited

    def stop_running_containers(self):
        # if the run directory exists, just run docker compose down
        if self.runner.file_exists(self.run_dir):
            self.stop_app()
        # if the app state is still not pending, just stop all running containers
        if self.get_application_health() != Status.PENDING:
            self.runner.run("docker stop $(docker ps --format '{{.ID}} {{.Image}}' | grep -v 'controller' | awk '{print $1}')")


    def get_application_health(self):
        # If the run directory already exists, check if the app is still running or just never deleted properly
        running = True
        failed = False
        if self.runner.file_exists(self.run_dir):
            expected = self.get_expected_images()
            running_images, failed_images = self.get_running_images()
            running = bool(running_images) and all(image in expected for image in running_images)
            failed = any(image in expected for image in failed_images)
        else:
            # run directory does not exist, check for any possible containers that may interfere with camera traps
            running_images, failed_images = self.get_running_images()
            running = bool(running_images) and all(any(keyword in image for keyword in self.keywords) for image in running_images)
            failed = any(keyword in image for image in failed_images for keyword in self.keywords)

        # if we can see failed containers then set to failed
        if failed:
            return Status.FAILED
        # if we can verify all containers are up, set status to running
        elif running:
            return Status.RUNNING
        # if the status was set to running or failed, but we cannot verify it, set back to pending
        elif self.status == Status.FAILED or self.status == Status.RUNNING:
            return Status.PENDING
        # otherwise, just return the currently set status
        else:
            return self.status

    def get_status(self):
        self.status = self.get_application_health()
        return self.status
