from remote import RemoteRunner
from textwrap import dedent

class CameraTrapsManager():
    def __init__(self, runner: RemoteRunner, version: str, branch: str = None):
        self.branch = branch
        self.version = version
        self.runner = runner
        if branch:
            branch = f'-b {branch}'
        else:
            branch = ''
        cmd = dedent(f'''
        rm -rf camera-traps
        git clone https://github.com/tapis-project/camera-traps {branch}
        cd camera-traps
        cd releases/{version}
        ''')
        out = self.runner.run(cmd)
        print(out)

    def docker_compose_up(self):
        cmd = dedent(f"""
        cd camera-traps/releases/{self.version}
        docker compose up
        """)
        out = self.runner.run(cmd)
        print(out)

    def docker_compose_down(self):
        cmd="docker compose down"
        out = self.runner.run(cmd)
        print(out)