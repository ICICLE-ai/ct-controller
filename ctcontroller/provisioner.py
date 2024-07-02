import os
import yaml
from subprocess import run
from .error import print_and_exit

CT_ROOT = '.ctcontroller'

class Provisioner:
    def __init__(self, cfg):
        self.user = cfg['requesting_user']
        # If the SSH key and key name were provided, use them. Otherwise, try to use a service account.
        self.get_config(cfg['config_path'])
        if ('ssh_key' in cfg and cfg['ssh_key'] is not None and cfg['ssh_key'] != ''
            and 'key_name' in cfg and cfg['key_name'] is not None and cfg['key_name'] != ''
            and (cfg['target_user'] is not None or cfg['user_name_required'] == False)):
            self.set('private_key', cfg['ssh_key'])
            self.set('key_name', cfg['key_name'])
            self.set('use_service_acct', False)
            print('Using user-provided credentials')
        else:
            self.lookup_auth(cfg['config_path'])
        self.set('ssh_key', {'name': self.key_name, 'path': self.private_key})
        self.set('num_nodes', cfg['num_nodes'])
        self.set('node_type', cfg['node_type'])
        self.set('gpu', cfg['gpu'])

    def get_config(self, config_path):
        if not os.path.exists(config_path):
            raise Exception('Config file not found')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        self.site_config = config[self.site]

    def lookup_auth(self, config_path: str):
        if not os.path.exists(config_path):
            raise Exception('Config file not found')
        with open(config_path, 'r') as f:
            auth = yaml.safe_load(f)
        if self.user not in auth['Users']:
            print_and_exit(f'{self.user} does not have appropriate permissions to launch with a service account.')
        print('Using service account')
        self.set('key_name', auth[self.site]['Name'])
        self.set('private_key', auth[self.site]['Path'])
        self.set('use_service_acct', True)

    def set(self, name: str, value):
        print(f'setting {name} to {value}')
        super().__setattr__(name, value)

    def get(self, prop: str):
        return getattr(self, prop, None)

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
            print(f'\n\033[93mWARNING: "{cmdstr}" gave error message: "{err}"\033[00m\n')
        return out
    
    def get_remote_runner(self, ip_address=None, remote_id=None):
        from .remote import RemoteRunner
        if ip_address is None:
            ip_address = self.ip_addresses
        if remote_id is None:
            remote_id = self.get('remote_id')
        return RemoteRunner(ip_address, remote_id, self.ssh_key['path'])

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