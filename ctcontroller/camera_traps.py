import os
from remote import RemoteRunner
from textwrap import dedent

class CameraTrapsManager():
    def __init__(self, runner: RemoteRunner, version: str, provision_id: str, top_log_dir: str, job_id: str=None, branch: str = None):
        self.branch = branch
        self.version = version
        self.runner = runner
        if branch:
            branch = f'-b {branch}'
        else:
            branch = ''
        self.provision_id = provision_id

        if job_id is None:
            job_id = self.get_job_id(top_log_dir)
        self.job_id = job_id
        self.log_dir = f'{top_log_dir}/{self.job_id}'
        self.setup_log_dir()

    def setup_app(self):
        cmd = dedent(f'''
        rm -rf camera-traps
        git clone https://github.com/tapis-project/camera-traps {branch}
        cd camera-traps
        cd releases/{version}
        ''')
        out = self.runner.run(cmd)
        print(out)

    def remove_app(self):
        cmd = dedent(f'rm -rf camera-traps')
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
        # Append jobid to provision's yaml

        # Run docker compose up to start camera traps code
        cmd = dedent(f"""
        cd camera-traps/releases/{self.version}
        docker compose up
        """)
        #out = self.runner.run(cmd)
        #print(out)

        outlog = f'{self.log_dir}/out.log'
        errlog = f'{self.log_dir}/err.log'
        self.runner.tracked_run(cmd, outlog, errlog)

    def docker_compose_down(self):
        cmd="docker compose down"
        out = self.runner.run(cmd)
        print(out)

    def run_job(self):
        self.setup_app()
        self.docker_compose_up()

    def shutdown_job(self):
        self.docker_compose_down()
        self.remove_app()