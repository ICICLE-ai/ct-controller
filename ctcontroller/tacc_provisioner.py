from .error import print_and_exit
from .provisioner import Provisioner
import os
import yaml

class TACCProvisioner(Provisioner):
    def __init__(self, cfg):
        cfg['key_name'] = 'default'
        self.site = cfg['site']
        cfg['user_name_required'] = True
        super(TACCProvisioner, self).__init__(cfg)

        self.get_remote_id(cfg)
        self.available_nodes = self.site_config['Hosts']
        self.set('lock_file', 'ctcontroller.lock')
        self.set('ip_addresses', None)

    def get_remote_id(self, cfg):
        if self.use_service_acct:
            self.set('remote_id', None)
        elif 'target_user' in cfg:
            self.set('remote_id', cfg['target_user'])
        else:
            print_and_exit('User id on remote server was not specified.')

    def reserve_node(self, node_type):
        from .remote import AuthenticationException
        available_nodes = self.available_nodes[node_type]
        if available_nodes == []:
            print_and_exit(f'No node of type {node_type} is available')
        for node in self.available_nodes[node_type]:
            try:
                if self.remote_id is not None:
                    remote_id = self.remote_id
                else:
                    remote_id = node['Username']
                runner = self.get_remote_runner(ip_address=node['IP'], remote_id=node['Username'])
            except AuthenticationException:
                print(f'Authentication failed while connecting to node {node}')
                continue
            except TimeoutError:
                print(f'SSH connection timed out while connecting node {node}')
                continue
            if runner.file_exists(self.lock_file):
                print(f'node {node} in use, going to next node...')
                del runner
                continue
            else:
                runner.create_file(self.lock_file)
                self.runner = runner
                self.set('ip_addresses', node['IP'])
                self.set('remote_id', node['Username'])
                print(f'node {node['IP']} available')
                return True
        return False

    def provision_instance(self):
        import time
        print('Waiting for a node to be available')
        while self.reserve_node(self.node_type) == False:
            print('.', end='')
            time.sleep(3)
        print('\n')

    def release_node(self):
        self.get_remote_runner().delete_file(self.lock_file)

    def shutdown_instance(self):
        self.release_node()