import os
import yaml
from subprocess import run

CT_ROOT = '.ctcontroller'

class Provisioner:
    def __init__(self, cfg):
        if cfg['use_service_acct']:
            self.lookup_auth(cfg['config_path'])
        else:
            self.set('private_key', cfg['ssh_key'])
            self.set('key_name', cfg['key_name'])
        self.set('ssh_key', {'name': self.key_name, 'path': self.private_key})
        self.set('num_nodes', cfg['num_nodes'])
        self.set('node_type', cfg['node_type'])
        self.set('gpu', cfg['gpu'])

    def lookup_auth(self, config_path):
        if not os.path.exists(config_path):
            raise Exception('Config file not found')
        with open(config_path, 'r') as f:
            auth = yaml.safe_load(f)
        self.set('key_name', auth[self.site]['Name'])
        self.set('private_key', auth[self.site]['Path'])

    def set(self, name: str, value):
        print(f'setting {name} to {value}')
        super().__setattr__(name, value)

    def capture_shell(self, cmd):
        if isinstance(cmd, str):
            cmd = cmd.split(' ')
            cmdstr = cmd
        elif isinstance(cmd, list):
            cmdstr = ' '.join(cmd)
        else:
            raise Exception(f'Invalid shell command: {cmd}')
        p = run(cmd, capture_output=True)
        out = p.stdout.decode('utf-8').strip()
        err = p.stderr.decode('utf-8').strip()
        if err != '':
            print(f'\n\033[93mWARNING: "{cmdstr}" gave error message: "{err}"\n')
        return out
    
    def get_remote_runner(self, ip_address=None):
        from .remote import RemoteRunner
        if ip_address is None:
            ip_address = self.ip_addresses
        return RemoteRunner(ip_address, self.remote_id, self.ssh_key['path'])

    def connect(self):
        from .remote import RemoteRunner
        self.runner = self.get_remote_runner()

    def check_connection(self):
        remote_hostname = self.runner.run('hostname')
        if remote_hostname == self.server_name:
            print('Connected')
            return True
        else:
            print('Connection Failed')
            return False