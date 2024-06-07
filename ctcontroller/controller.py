#import logging
import os
from __init__ import CT_ROOT

#logger = logging.getLogger(__name__)

class Controller:
    def __init__(self, site: str, cmd: str, config_file: str=None, user_name: str = None):
        self.site = site
        self.cmd = cmd
        if user_name:
            self.user_name = user_name
        else:
            self.get_user_name(config_file)
        if not self.use_existing_config():
            self.top_level_dir = self.get_top_level_dir()
            self.site_dir = self.top_level_dir + '/' + self.site
            self.user_dir = f'{self.site_dir}/{self.user_name}'
            self.config_file = f'{self.user_dir}/config.rc'
            self.set_config(config_file)
        self.env = os.environ
        self.user_cache = f'{self.user_dir}/cache.pcl'
        if not self.load_user_cache():
            self.setup_user()
        self.save_user_cache()

    def use_existing_config(self):
        for dir in os.environ.get('CT_CONTROLLER_ROOT'), os.curdir, os.path.expanduser('~'):
            user_dir = f'{dir}/{CT_ROOT}/{self.site}/{self.user_name}'
            config_path = f'{user_dir}/config.rc'
            if os.path.exists(config_path):
                self.config_file = config_path
                self.top_level_dir = f'{dir}/{CT_ROOT}'
                self.site_dir = f'{self.top_level_dir}/{self.site}'
                self.user_dir = f'{self.site_dir}/{self.user_name}'
                return True

    def get_top_level_dir(self):
        for d in os.path.expanduser('~'), os.curdir, os.environ.get('CT_CONTROLLER_ROOT'):
            dir = f'{d}/{CT_ROOT}'
            if os.access(dir, os.W_OK):
                return dir

    def set_config(self, config_file: str):
        custom_conf = os.environ.get("CT_CONTROLLER_CONF")
        if custom_conf:
            if os.path.exists(custom_conf):
                self.config_file = custom_conf
        else:
            import shutil
            if not os.path.exists(self.user_dir):
                os.makedirs(self.user_dir)
            if config_file and os.path.exists(config_file):
                print(f'Copying {config_file} to {self.config_file}')
                shutil.copy(config_file, self.config_file)
            else:
                import sys
                print(f'Invalid config file: {config_file}. Pass the path to a valid config file during registration.')
                sys.exit(1)

    def load_user_cache(self):
        if os.path.exists(self.user_cache):
            from pickle import load
            with open(self.user_cache, 'rb') as p:
                self.env.update(load(p))
            return True
        return False

    def save_user_cache(self):
        from pickle import dump, HIGHEST_PROTOCOL
        with open(self.user_cache, 'wb') as p:
            dump(dict(self.env), p, HIGHEST_PROTOCOL)

    def setup_user():
        pass

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