import os
from subprocess import run
import yaml
from .remote import RemoteRunner
from .error import print_and_exit

CT_ROOT = '.ctcontroller'

class Provisioner:
    def __init__(self, cfg):
        self.site = cfg['target_site']
        self.user = cfg['requesting_user']
        # If the SSH key and key name were provided, use them.
        # Else try to use a service account.
        self.get_config(cfg['config_path'])
        if ('ssh_key' in cfg and cfg['ssh_key'] is not None and cfg['ssh_key'] != ''
            and 'key_name' in cfg and cfg['key_name'] is not None and cfg['key_name'] != ''
            and (cfg['target_user'] is not None or not cfg['user_name_required'])):
            self.private_key = cfg['ssh_key']
            self.key_name = cfg['key_name']
            self.use_service_acct = False
            print('Using user-provided credentials')
        else:
            self.lookup_auth(cfg['config_path'])
        self.ssh_key = {'name': self.key_name, 'path': self.private_key}
        self.num_nodes = cfg['num_nodes']
        self.node_type  =cfg['node_type']
        self.gpu = cfg['gpu']
        self.runner = None
        self.ip_addresses = None

    def get_config(self, config_path):
        if not os.path.exists(config_path):
            print_and_exit('Config file not found')
        with open(config_path, 'r', encoding='utf-8') as fil:
            config = yaml.safe_load(fil)
        self.site_config = config[self.site]

    def lookup_auth(self, config_path: str):
        if not os.path.exists(config_path):
            print_and_exit('Config file not found')
        with open(config_path, 'r', encoding='utf-8') as fil:
            auth = yaml.safe_load(fil)
        if self.user not in auth['Users']:
            print_and_exit((f'{self.user} does not have appropriate permissions to launch '
                           'with a service account.'))
        print('Using service account')
        self.key_name = auth[self.site]['Name']
        self.private_key = auth[self.site]['Path']
        self.use_service_acct = True

    #def set(self, name: str, value):
    def __setattr__(self, name: str, value) -> None:
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
            print_and_exit(f'Invalid shell command: {cmd}')
        proc = run(cmd, capture_output=True, check=False)
        out = proc.stdout.decode('utf-8').strip()
        err = proc.stderr.decode('utf-8').strip()
        if err != '':
            print(f'\n\033[93mWARNING: "{cmdstr}" gave error message: "{err}"\033[00m\n')
        return out, err

    def get_remote_runner(self, ip_address=None, remote_id=None):
        if ip_address is None:
            ip_address = self.ip_addresses
        if remote_id is None:
            remote_id = self.get('remote_id')
        return RemoteRunner(ip_address, remote_id, self.ssh_key['path'])

    def connect(self):
        self.runner = self.get_remote_runner()
