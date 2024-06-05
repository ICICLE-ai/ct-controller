#import logging
import os

#logger = logging.getLogger(__name__)

class Controller:
    def __init__(self, config_file: str=None):
        self.env = os.environ
        self.hardware = None
        self.config_file = self.search_config(config_file)

    def login(self):
        with open(self.config_file, 'r') as f:
            for line in f.readlines():
                if 'export' in line:
                    out = line.replace('export ', '').replace('"', '').strip('\n')
                    var, _, val = out.partition('=')
                    self.env[var] = val

        # Set password
        if self.env.get("CHAMELEON_PASSWORD"):
            self.env["OS_PASSWORD"] = self.env.get("CHAMELEON_PASSWORD")
        else:
            password = input('Please enter your chameleon password or pass to the environment variable CHAMELEON_PASSWORD: ')
            self.env["OS_PASSWORD"] = password

        # Do not leave empty string as region name
        if self.env.get("OS_REGION_NAME") is not None and self.env.get("OS_REGION_NAME") == "":
            del self.env["OS_REGION_NAME"]

    def search_config(self, config_file: str=None):
        if config_file:
            if os.path.exists(config_file):
                return config_file
        config_file= None
        for loc in self.env.get("CT_CONTROLLER_CONF"), os.curdir, os.path.join(os.path.expanduser("~"),".ctcontroller"):
            if loc is None:
                continue
            config_file = os.path.join(loc, ".ctcontrollerrc")
            if os.path.exists(config_file):
                return config_file
        return None

    def register_credentials(self, config_file: str):
        import shutil
        existing = []
        for loc in self.env.get("CT_CONTROLLER_CONF"), os.path.join(os.path.expanduser("~"),".ctcontroller"), os.curdir:
            if loc is None:
                continue
            dest = os.path.join(loc, ".ctcontrollerrc") 
            if os.path.exists(dest):
                existing.append(dest)
                continue
            if loc == os.path.join(os.path.expanduser("~"),".ctcontroller") and not os.path.isdir(loc):
                os.makedirs(loc)
            shutil.copy(config_file, dest)
            self.config_file = dest
            return
        raise Exception(f'Could not register credentials. Existing credentials already exist. Please remove one of these files:\n{",".join(existing)}')