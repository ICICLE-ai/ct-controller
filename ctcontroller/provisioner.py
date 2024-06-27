#import logging
import os
from subprocess import run

#logger = logging.getLogger(__name__)

CT_ROOT = '.ctcontroller'

class Provisioner:
    def __init__(self, cfg):
        if 'root' in cfg:
            self.top_level_dir = self.get_top_level_dir(cfg['root'])
        else:
            self.top_level_dir = f'./{CT_ROOT}'
        #self.site = cfg['site']
        #self.site_dir = self.top_level_dir + '/' + self.site
        #self.user_name = cfg['user_name']
        #self.user_dir = f'{self.site_dir}/{self.user_name}'
        #if 'provision_id' not in cfg or cfg['provision_id'] is None:
        #    provision_id = self.get_provision_id()
        #provision_dir = f'{self.user_dir}/provisions/{provision_id}'
        #provision_file = f'{provision_dir}/provision.yaml'
        #if os.path.exists(provision_file):
        #    self.read_provision_info(provision_file)
        #else:
        #    os.makedirs(f'{provision_dir}')

        #    self.set('provision_dir', provision_dir)
        #    self.set('provision_id', provision_id)
        self.set('private_key', cfg['ssh_key'])
        self.set('key_name', cfg['key_name'])
        self.set('ssh_key', {'name': self.key_name, 'path': self.private_key})
        self.set('num_nodes', cfg['num_nodes'])
        self.set('node_type', cfg['node_type'])
        self.set('gpu', cfg['gpu'])
        #self.env = os.environ
        #self.user_cache = f'{self.user_dir}/cache.pcl'
        #if not self.load_user_cache():
        #    self.setup_user()
        #self.save_user_cache()

    #def use_existing_config(self):
    #    for dir in os.environ.get('CT_CONTROLLER_ROOT'), os.curdir, os.path.expanduser('~'):
    #        user_dir = f'{dir}/{CT_ROOT}/{self.site}/{self.user_name}'
    #        config_path = f'{user_dir}/config.rc'
    #        if os.path.exists(config_path):
    #            self.config_file = config_path
    #            self.top_level_dir = f'{dir}/{CT_ROOT}'
    #            self.site_dir = f'{self.top_level_dir}/{self.site}'
    #            self.user_dir = f'{self.site_dir}/{self.user_name}'
    #            return True

    #def get_top_level_dir(self, user_defined = None):
    #    if user_defined is not None:
    #        if os.access(user_defined, os.W_OK):
    #            return user_defined
    #    for d in os.path.expanduser('~'), os.curdir, os.environ.get('CT_CONTROLLER_ROOT'):
    #        dir = f'{d}/{CT_ROOT}'
    #        print(f'{dir=}')
    #        if os.access(dir, os.W_OK):
    #            return dir

    #def set_config(self, config_file: str):
    #    custom_conf = os.environ.get("CT_CONTROLLER_CONF")
    #    if custom_conf:
    #        if os.path.exists(custom_conf):
    #            self.config_file = custom_conf
    #    else:
    #        import shutil
    #        if not os.path.exists(self.user_dir):
    #            os.makedirs(self.user_dir)
    #        if config_file and os.path.exists(config_file):
    #            print(f'Copying {config_file} to {self.config_file}')
    #            shutil.copy(config_file, self.config_file)
    #        else:
    #            import sys
    #            print(f'Invalid config file: {config_file}. Pass the path to a valid config file during registration.')
    #            sys.exit(1)

    #def load_user_cache(self):
    #    if os.path.exists(self.user_cache):
    #        from pickle import load
    #        with open(self.user_cache, 'rb') as p:
    #            self.env.update(load(p))
    #        return True
    #    return False

    #def save_user_cache(self):
    #    from pickle import dump, HIGHEST_PROTOCOL
    #    with open(self.user_cache, 'wb') as p:
    #        dump(dict(self.env), p, HIGHEST_PROTOCOL)

    #def get_provision_id(self):
    #    top_provision_dir = f'{self.user_dir}/provisions'
    #    if os.path.exists(top_provision_dir):
    #        subdirs = [f.name for f in os.scandir(top_provision_dir) if f.is_dir()]
    #        numbered_subdirs = [-1] + [int(d) for d in subdirs if d.isdigit()]
    #        provision_id = str(max(numbered_subdirs) + 1)
    #    else:
    #        os.makedirs(top_provision_dir, exist_ok=True)
    #        provision_id = '0'
    #    return provision_id

    def set(self, name: str, value):
        print(f'setting {name} to {value}')
        super().__setattr__(name, value)
    #    if name not in self.__dict__.keys() or  self.__getattribute__(name) is None:
    #        super().__setattr__(name, value)
    #        print(f'setting {name} to {value}')
    #    #else:
    #    #    print(f'Not setting {name} to {value}. Already defined as {super().__getattribute__(name)}')
    #    #if self.cmd == 'provision':
    #    with open(self.provision_dir + '/provision.yaml', 'a+') as f:
    #        f.write(f'{name}: {value}\n')

    #def read_provision_info(self, provision_file: str):
    #    import yaml
    #    print(f'Reading provision info from {provision_file}')
    #    with open(provision_file, 'r') as f:
    #        provision_info = yaml.safe_load(f)
    #    for k, v in provision_info.items():
    #        self.__setattr__(k, str(v))

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

    #def provision_instance(self):
    #    pass

    #def login(self):
    #    if not self.load_user_cache():
    #        self.setup_user()
    #    self.save_user_cache()
    #    print(f'ssh key: {self.ssh_key}'); import sys; sys.exit(1)

    #def search_config(self, config_file: str=None):
    #    if config_file:
    #        if os.path.exists(config_file):
    #            return config_file
    #    config_file= None
    #    for loc in self.env.get("CT_CONTROLLER_CONF"), os.curdir, os.path.join(os.path.expanduser("~"),".ctcontroller"):
    #        if loc is None:
    #            continue
    #        config_file = os.path.join(loc, ".ctcontrollerrc")
    #        if os.path.exists(config_file):
    #            return config_file
    #    return None

    #def register_credentials(self, config_file: str):
    #    import shutil
    #    existing = []
    #    for loc in self.env.get("CT_CONTROLLER_CONF"), os.path.join(os.path.expanduser("~"),".ctcontroller"), os.curdir:
    #        if loc is None:
    #            continue
    #        dest = os.path.join(loc, ".ctcontrollerrc") 
    #        if os.path.exists(dest):
    #            existing.append(dest)
    #            continue
    #        if loc == os.path.join(os.path.expanduser("~"),".ctcontroller") and not os.path.isdir(loc):
    #            os.makedirs(loc)
    #        shutil.copy(config_file, dest)
    #        self.config_file = dest
    #        return
    #    raise Exception(f'Could not register credentials. Existing credentials already exist. Please remove one of these files:\n{",".join(existing)}')