"""Contains the base Provisioner class used to create site-specific provisioners."""
import os
import yaml
from .remote import RemoteRunner
from .util import ProvisionException

CT_ROOT = '.ctcontroller'

class Provisioner:
    """
    The base Provisioner class used to create site-specific provisioners.
    Contains basic setup steps and subroutines necessary for any site provisioner.

    Attributes:
        site (str): 
        user (str): 
        private_key (str): 
        key_name (str): 
        use_service_acct (bool): 
        ssh_key (dict): 
        num_nodes (int): 
        gpu (bool): 
        runner (RemoteRunner): 
        ip_addresses (str): 
        device_id (str): 
        site_config (str): 

    Methods:
        get_config(config_path):
        lookup_auth(config_path): 
        get(prop): 
        get_remote_runner(ip_address, remote_id): 
        connect(): 
    """

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
        self.device_id = None

    def get_config(self, config_path: str):
        """
        If the config file exists, load the site-specific configuration options into a dictionary.
        If the config file does not exist, print an error message and exit.

            Parameters:
                config_path (str): the path to the config file.
        """

        if not os.path.exists(config_path):
            raise ProvisionException('Config file not found')
        with open(config_path, 'r', encoding='utf-8') as fil:
            config = yaml.safe_load(fil)
        self.site_config = config[self.site]

    def lookup_auth(self, config_path: str):
        """
        Reads in the config file (if it exists).
        If the requesting user is authorized, uses any service account specified in the
        config file to sets the key name and private key.

            Parameters:
                config_path (str): the path to the config file.
        """

        if not os.path.exists(config_path):
            raise ProvisionException('Config file not found')
        with open(config_path, 'r', encoding='utf-8') as fil:
            auth = yaml.safe_load(fil)
        if ('Users' in auth and self.user not in auth['Users']
            and auth['Settings']['AuthenticateUsers']):
            raise ProvisionException((f'{self.user} does not have appropriate permissions to launch '
                           'with a service account.'))
        print('Using service account')
        self.key_name = auth[self.site]['Name']
        self.private_key = auth[self.site]['Path']
        self.use_service_acct = True

    def __setattr__(self, name: str, value) -> None:
        print(f'setting {name} to {value}')
        super().__setattr__(name, value)

    def get(self, prop: str):
        """Returns the value of prop or None if it is not defined."""
        return getattr(self, prop, None)

    def get_remote_runner(self, ip_address=None, remote_id=None):
        """
        Initialize a RemoteRunner connected to the provisioned server at the specified ip_address
        logged in with the specified username id.

            Parameters:
                ip_address (str): IP address of the server to connect
                remote_id (str): username on the remote server
            
            Returns:
                RemoteRunner:  runner connected to the specified remote server
        """
        if ip_address is None:
            ip_address = self.ip_addresses
        if remote_id is None:
            remote_id = self.get('remote_id')
        return RemoteRunner(ip_address, remote_id, self.ssh_key['path'], self.device_id)

    #def connect(self):
    #    self.runner = self.get_remote_runner()
