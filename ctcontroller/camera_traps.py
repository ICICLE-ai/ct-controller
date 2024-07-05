import os
from textwrap import dedent
from .remote import RemoteRunner
from .error import print_and_exit

# Class to manage the camera traps application on a remote node
class CameraTrapsManager():
    def __init__(self, runner: RemoteRunner, log_dir: str, cfg):
        self.runner = runner
        self.log_dir = log_dir
        self.run_dir = None

        self.version = cfg.get('ct_version')
        self.gpu = cfg.get('gpu')
        self.model = cfg.get('model')
        self.input = cfg.get('input')
        self.advanced = cfg.get('advanced_app_vars')

    # Generates a config file and copies it to target node
    def generate_cfg_file(self, rmt_pth):
        with open('ct_controller.yml', 'w', encoding='utf-8') as fil:
            relpath = os.path.relpath(self.run_dir, rmt_pth)
            fil.write(f'install_dir: {relpath}\n')
            if self.version:
                fil.write(f'ct_version: {self.version}\n')
            if self.gpu:
                fil.write(f'use_gpu_in_scoring: {self.gpu}\n')
            if self.model:
                print_and_exit('Custom model not currently supported')
            if self.input:
                print_and_exit('Custom input not currently supported')
            if self.advanced:
                for key, val in self.advanced.items():
                    fil.write(f'{key}: {val}\n')
        self.runner.copy_file('ct_controller.yml', f'{rmt_pth}/ct_controller.yml')


    def setup_app(self):
        # Prune containers on system
        prune_cmd = 'docker container prune -f'
        self.runner.run(prune_cmd)
        # Copy over run scripts
        self.run_dir = f'{self.runner.home_dir}/ct_run'
        # Generate config file
        self.generate_cfg_file(self.runner.home_dir)
        # Install to run directory and cleanup config
        install_cmd = dedent(f"""
        cd {self.runner.home_dir}
        docker run -it --rm --user `id -u`:`id -g` -v {self.runner.home_dir}:/host/ -e INSTALL_HOST_PATH={self.runner.home_dir} -e INPUT_FILE=ct_controller.yml tapis/camera-traps-installer
        rm ct_controller.yml
        """)
        out = self.runner.run(install_cmd)
        print(out)

    def remove_app(self):
        cmd = f'rm -rf {self.run_dir}'
        out = self.runner.run(cmd)
        print(out)

    def docker_compose_up(self):
        # Run docker compose up to start camera traps code
        cmd = dedent(f"""
        cd {self.run_dir}
        docker compose up
        """)
        #out = self.runner.run(cmd)
        #print(out)

        outlog = f'{self.log_dir}/ct_out.log'
        errlog = f'{self.log_dir}/ct_err.log'
        self.runner.tracked_run(cmd, outlog, errlog)

    def docker_compose_down(self):
        cmd = dedent(f"""
        cd {self.run_dir}
        docker compose down
        """)
        out = self.runner.run(cmd)
        print(out)

    def run_job(self):
        self.setup_app()
        self.docker_compose_up()

    def shutdown_job(self):
        self.docker_compose_down()
        self.remove_app()
