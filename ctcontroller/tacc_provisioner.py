"""Contains the TACCProvisioner for provisioning bare-metal hardware at TACC."""

import time
from .util import ProvisionException
from .provisioner import Provisioner
from .remote import AuthenticationException

class TACCProvisioner(Provisioner):
    """
    A subclass of the Provisioner class to handle the provisioning and deprovisioning
    of bare-metal hardware at TACC.

    Attributes:
        lock_file (str): name of the lock file used to reserve a node
        available_nodes (dict): a dictionary of nodes accessible at the TACC site
        remote_id (str): username to be used on the remote server

    Methods:

        reserve_node(node_type):
            Checks if any of the nodes that match node_type are available.
        provision_instance():
            Periodically checks until a compatible resource has become available
        shutdown_instance():
            Deprovisions the node
    """

    def __init__(self, cfg):
        cfg['key_name'] = 'default'
        cfg['user_name_required'] = True
        super().__init__(cfg)

        self.available_nodes = self.site_config['Hosts']
        self.lock_file = 'ctcontroller.lock'

        if self.use_service_acct:
            self.remote_id = None
        elif 'target_user' in cfg:
            self.remote_id = cfg['target_user']
        else:
            raise ProvisionException('User id on remote server was not specified.')

    def reserve_node(self, node_type) -> bool:
        """
        Loops over nodes at TACC that match the requested node type and reserves the
        first node if available.

            Parameters: 
                node_type (dict): a dictionary describing the requested node type

            Returns:
                bool: True if an available node was reserved
                      False if there were no available nodes to reserver
        """

        available_nodes = self.available_nodes[node_type]
        if available_nodes == []:
            raise ProvisionException(f'No node of type {node_type} is available')
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
                self.device_id = runner.device_id
                print(f'node {node["IP"]} available')
                return True
            print(f'node {node} in use, going to next node...')
            del runner
        return False

    def provision_instance(self) -> None:
        """Periodically checks for an available node and exits once it has been reserved."""

        print('Waiting for a node to be available')
        while not self.reserve_node(self.node_type):
            print('.', end='')
            time.sleep(3)
        print('\n')

    def shutdown_instance(self) -> None:
        """Deprovisions the node by deleting the lock file."""

        self.get_remote_runner().delete_file(self.lock_file)
