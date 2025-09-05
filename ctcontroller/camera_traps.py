"""
Contains the CameraTrapsManager class which manages the camera traps application on
a remote node
"""

import os
import re
import logging
import json
from textwrap import dedent
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
        advanced (dict): a key-pair of advanced runtime options for camera traps

    Methods:
        generate_cfg_file(rmt_path): 
            Generates a config file and copies it to the remote node that will run camera traps
        setup_app():
        remove_app():
        docker_compose_up():
        docker_compose_down():
        run_job():
        shutdown_job():
    """

    def __init__(self, runner: RemoteRunner | LocalRunner, log_dir: str, cfg):
        """
        Constructions all necessary attributes for a CameraTrapsManager object
            
            Parameters:
                runner (RemoteRunner|LocalRunner): a runner attached to the target node
                log_dir (str): local directory where all output related to this run should be stored
                cfg (dict): a dictionary of configuration parameters and values passed from the
                            Controller object
        """

        super().__init__(runner, log_dir, cfg)

        out, _ = capture_shell("curl -s https://api.github.com/repos/tapis-project/camera-traps/tags")
        latest = json.loads(out)[0]['name']
        self.version = cfg.get('ct_version', latest)
        self.gpu = cfg.get('gpu')
        self.model = cfg.get('model')
        self.input = cfg.get('input')
        self.node_type = cfg.get('node_type')
        self.input_dataset_type = cfg.get('input_dataset_type', 'image')
        self.mode = cfg.get('mode', 'simulation')
        if self.mode == 'simulation' and self.input_dataset_type == 'video':
            self.mode = 'video_simulation'
        self.run_dir = None

    def generate_cfg_file(self):
        """Generates a config file and copies it to the remote node that will run camera traps"""

        rmt_pth = self.runner.home_dir
        with open(f'{self.log_dir}/ct_controller.yml', 'w', encoding='utf-8') as fil:
            relpath = os.path.relpath(self.run_dir, rmt_pth)
            fil.write(f'install_dir: {relpath}\n')
            fil.write(f'device_id: {self.runner.device_id}\n')
            fil.write(f'user_id: {self.user_id}\n')
            fil.write(f'experiment_id: {self.experiment_id}\n')
            fil.write(f'mode: {self.mode}\n')
            if self.version:
                fil.write(f'ct_version: {self.version}\n')
            if self.gpu:
                fil.write(f'use_gpu_in_scoring: {self.gpu}\n')
            if self.model:
                fil.write(f'model_id: {self.model}\n')
            if self.input:
                if validators.url(self.input):
                    if self.input_dataset_type == 'image':
                        fil.write('use_image_url: true\n')
                        fil.write(f'source_image_url: {self.input}\n')
                    elif self.input_dataset_type == 'video':
                        fil.write('source_video_url: {self.input}\n')
                else:
                    self.status = Status.FAILED
                    raise ApplicationException(f"Input dataset source: {self.input} is not a valid url")
            if self.mode == 'video_simulation':
                fil.write(f'motion_video_device: {self.get_video_device()}\n')
            if self.advanced:
                for key, val in self.advanced.items():
                    fil.write(f'{key}: {val}\n')
            fil.write(f'inference_server: false\n')
            if self.node_type == 'Jetson':
                fil.write('image_scoring_plugin_image: tapis/image_scoring_plugin_py_nano_3.8\n')
                fil.write('power_monitor_backend: jtop\n')
            if self.runner.cpu_arch == 'arm':
                fil.write('power_monitor_backend: scaphandre\n')
        self.runner.copy_file(f'{self.log_dir}/ct_controller.yml', f'{rmt_pth}/ct_controller.yml')


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

    def setup_app(self):
        """
        Sets up the remote node so that it is ready to run:
            1. Prunes any stopped containers
            2. Generates the config file
            3. Runs the custom installer
        """

        self.status = Status.SETTINGUP
        # restart jtop service if running on a Jetson
        if self.node_type == 'Jetson':
            self.runner.run('systemctl restart jtop.service')
        # Prune containers on system
        prune_cmd = 'docker container prune -f'
        self.runner.run(prune_cmd)
        # Generate config file
        self.run_dir = f'{self.runner.home_dir}/ct_run'
        self.generate_cfg_file()
        # Install to run directory and cleanup config
        proxy_cmd = f' -e HTTP_PROXY={self.runner.httpproxy} -e HTTPS_PROXY={self.runner.httpproxy}'
        install_cmd = dedent(f"""
        cd {self.runner.home_dir}
        rm -rf {self.run_dir}
        docker pull tapis/camera-traps-installer:{self.version}
        docker run -it --rm --user `id -u`:`id -g` -v {self.runner.home_dir}:/host/ -e INSTALL_HOST_PATH={self.runner.home_dir} -e INPUT_FILE=ct_controller.yml{proxy_cmd if self.runner.httpproxy is not None else ""} tapis/camera-traps-installer:{self.version}
        rm ct_controller.yml
        """)
        out = self.runner.run(install_cmd)
        LOGGER.info(out)
        # Prune images/containers and pull the latest images
        pull_cmd = dedent(f"""
        cd {self.run_dir}
        docker container prune -f
        docker image prune -f
        docker compose pull
        docker pull tapis/powerjoular
        """)
        self.runner.run(pull_cmd)

    def remove_app(self):
        """Deletes the run directory"""

        cmd = f'rm -rf {self.run_dir}'
        out = self.runner.run(cmd)
        LOGGER.info(out)

    def docker_compose_up(self):
        """
        Run docker compose up in the remote run directory and capture output in the
        local log directory.
        """

        # Run docker compose up to start camera traps code
        cmd = dedent(f"""
        cd {self.run_dir}
        docker compose pull
        docker compose up
        """)

        outlog = f'{self.log_dir}/ct_out.log'
        errlog = f'{self.log_dir}/ct_err.log'
        self.status = Status.RUNNING
        self.runner.tracked_run(cmd, outlog, errlog)
        self.status = Status.COMPLETE

    def docker_compose_down(self):
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


    def copy_results(self):
        self.status = 'transferring data'
        try:
            self.runner.get(self.run_dir, self.log_dir)
        except FileNotFoundError:
            self.status = Status.FAILED
            raise ApplicationException(f'Run directory {self.run_dir} could not be found on remote server {self.runner.ip_address}')
        except OSError:
            self.status = Status.FAILED
            raise ApplicationException(f'Copy of run directory {self.run_dir} from {self.runner.ip_address} to {self.log_dir} failed')

    def run_job(self):
        """Setup the remote run directory and launch camera traps"""

        self.setup_app()
        self.docker_compose_up()

    def shutdown_job(self):
        """Shutdown the camera traps container and cleanup the run directory"""

        self.status = Status.SHUTTINGDOWN
        self.docker_compose_down()
        self.copy_results()
        self.remove_app()
        self.status = Status.SHUTDOWN
