"""Contains the TACCProvisioner for provisioning bare-metal hardware at TACC."""

import time
from .error import print_and_exit
from .provisioner import Provisioner
from .remote import AuthenticationException

class TACCProvisioner(Provisioner):
    """
    A subclass of the Provisioner class to handle the provisioning and deprovisioning
    of bare-metail hardware at TACC.

    Attributes:
        site (str): 
        use_service_acct (bool): 
        lock_file (str): 
        available_nodes (dict): 
        site_config (dict): 
        remote_id (): 

    Methods:

        get_remote_id(cfg):
            Determine the username to be used when connecting to the provisioned hardware
        reserve_node(node_type):
        provision_instance():
        shutdown_instance():
    """

    def __init__(self, cfg):
        cfg['key_name'] = 'default'
        self.site = cfg['target_site']
        cfg['user_name_required'] = True
        super().__init__(cfg)

        self.get_remote_id(cfg)
        self.available_nodes = self.site_config['Hosts']
        self.lock_file = 'ctcontroller.lock'

    def get_remote_id(self, cfg):
        if self.use_service_acct:
            self.remote_id = None
        elif 'target_user' in cfg:
            self.remote_id = cfg['target_user']
        else:
            print_and_exit('User id on remote server was not specified.')

    def reserve_node(self, node_type):
        available_nodes = self.available_nodes[node_type]
        if available_nodes == []:
            print_and_exit(f'No node of type {node_type} is available')
        for node in self.available_nodes[node_type]:
            try:
                if self.remote_id is not None:
                    remote_id = self.remote_id
                else:
                    remote_id = node['Username']
                runner = self.get_remote_runner(ip_address=node['IP'], remote_id=remote_id)
            except AuthenticationException:
                print(f'Authentication failed while connecting to node {node}')
                continue
            except TimeoutError:
                print(f'SSH connection timed out while connecting node {node}')
                continue
            if not runner.file_exists(self.lock_file):
                runner.create_file(self.lock_file)
                self.runner = runner
                self.ip_addresses = node['IP']
                self.remote_id = node['Username']
                print(f'node {node["IP"]} available')
                return True
            print(f'node {node} in use, going to next node...')
            del runner
        return False

    def provision_instance(self):
        print('Waiting for a node to be available')
        while not self.reserve_node(self.node_type):
            print('.', end='')
            time.sleep(3)
        print('\n')

    def shutdown_instance(self):
        self.get_remote_runner().delete_file(self.lock_file)
