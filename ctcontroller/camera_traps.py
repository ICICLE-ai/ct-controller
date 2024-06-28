import os
from .remote import RemoteRunner
from textwrap import dedent

class CameraTrapsManager():
    def __init__(self, runner: RemoteRunner, log_dir: str, cfg):
        self.runner = runner
        #self.version = cfg['ct_version']
        self.log_dir = log_dir
        self.run_dir = 'inputs'

    def setup_app(self):
        # Prune containers on system
        cmd = 'docker container prune -f'
        self.runner.run(cmd)
        # Copy over run scripts
        self.runner.copy_dir(f'./{self.run_dir}', f'{self.runner.home_dir}')

    def remove_app(self):
        cmd = dedent(f'rm -rf {self.run_dir}')
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