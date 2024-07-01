import os
from .remote import RemoteRunner
from textwrap import dedent

class CameraTrapsManager():
    def __init__(self, runner: RemoteRunner, log_dir: str, cfg):
        self.runner = runner
        self.log_dir = log_dir
        self.src_dir = cfg['app_src']
        self.run_dir = None

        self.version = cfg.get('ct_version')
        self.gpu = cfg.get('gpu')
        self.model = cfg.get('model')
        self.input = cfg.get('input')
        self.advanced = cfg.get('advanced_app_vars')

    def generate_cfg_file(self, rmt_pth):
        with open('ct_controller.yml', 'w') as f:
            relpath = os.path.relpath(self.run_dir, rmt_pth)
            f.write(f'install_dir: {relpath}\n')
            if self.version:
                f.write(f'ct_version: {self.version}\n')
            if self.gpu:
                f.write(f'use_gpu_in_scoring: {self.gpu}\n')
            if self.model:
                raise Exception('Custom model not currently supported')
            if self.input:
                raise Exception('Custom input not currently supported')
            if self.advanced:
                for k, v in self.advanced.items():
                    f.write(f'{k}: {v}\n')
        self.runner.copy_file('ct_controller.yml', f'{rmt_pth}/ct_controller.yml')


    def setup_app(self):
        # Prune containers on system
        prune_cmd = 'docker container prune -f'
        self.runner.run(prune_cmd)
        # Copy over run scripts
        remote_installer_path = self.runner.copy_dir(f'./{self.src_dir}', f'{self.runner.home_dir}')
        self.run_dir = f'{remote_installer_path}/run'
        # Generate config file
        self.generate_cfg_file(remote_installer_path)
        # Install to run directory
        install_cmd = dedent(f"""
        cd {remote_installer_path}
        sh install.sh {remote_installer_path} ct_controller.yml
        """)
        out = self.runner.run(install_cmd)
        print(out)
        # Delete installer after installation has completed
        #cleanup_cmd = f'rm -rf  {remote_installer_path}'
        #out = self.runner.run(cleanup_cmd)
        #print(out)

    def remove_app(self):
        cmd = f'rm -rf {self.run_dir}'
        #out = self.runner.run(cmd)
        #print(out)

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