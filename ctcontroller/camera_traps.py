import os
from remote import RemoteRunner
from textwrap import dedent

class CameraTrapsManager():
    #def __init__(self, runner: RemoteRunner, version: str, provision_id: str, top_log_dir: str, job_id: str=None, branch: str = None):
    def __init__(self, runner: RemoteRunner, top_log_dir: str, cfg):
        self.runner = runner
        self.version = cfg['ct_version']
        if 'job_id' not in cfg or cfg['job_id'] is None:
            job_id = self.get_job_id(top_log_dir)
        self.job_id = job_id
        self.log_dir = f'{top_log_dir}/{self.job_id}'
        self.setup_log_dir()
        self.run_dir = 'inputs'

    def setup_app(self):
        # Prune containers on system
        cmd = 'docker container prune -f'
        self.runner.run(cmd)
        # Copy over run scripts
        self.runner.copy_dir(f'./{self.run_dir}', self.runner.home_dir)

    def remove_app(self):
        cmd = dedent(f'rm -rf {self.run_dir}')
        out = self.runner.run(cmd)
        print(out)

    def setup_log_dir(self):
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def get_job_id(self, top_log_dir):
        if os.path.exists(top_log_dir):
            subdirs = [f.name for f in os.scandir(top_log_dir) if f.is_dir()]
            numbered_subdirs = [-1] + [int(d) for d in subdirs if d.isdigit()]
            job_id = str(max(numbered_subdirs) + 1)
        else:
            os.makedirs(top_log_dir, exist_ok=True)
            job_id = '0'
        return job_id

    def docker_compose_up(self):
        # Run docker compose up to start camera traps code
        cmd = dedent(f"""
        cd {self.run_dir}
        docker compose up
        """)
        #out = self.runner.run(cmd)
        #print(out)

        outlog = f'{self.log_dir}/out.log'
        errlog = f'{self.log_dir}/err.log'
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