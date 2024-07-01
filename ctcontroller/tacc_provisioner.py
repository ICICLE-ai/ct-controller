from .error import print_and_exit
from .provisioner import Provisioner
import os

class TACCProvisioner(Provisioner):
    def __init__(self, cfg):
        cfg['key_name'] = 'default'
        self.site = cfg['site']
        super(TACCProvisioner, self).__init__(cfg)
        self.set('remote_id', cfg['user_name'])

        self.available_nodes = {
                                     'x86': ['c040.rodeo.tacc.utexas.edu'],
                                     'jetson': [
                                                'cicnano01.tacc.utexas.edu',
                                                'cicnano02.tacc.utexas.edu',
                                                'cicnano03.tacc.utexas.edu'
                                               ],
                                     'rpi': []
                                    }
        self.set('lock_file', 'ctcontroller.lock')
        self.set('ip_addresses', None)

    def reserve_node(self, node_type):
        from .remote import AuthenticationException
        available_nodes = self.available_nodes[node_type]
        if available_nodes == []:
            print_and_exit(f'No node of type {node_type} is available')
        for node in self.available_nodes[node_type]:
            try:
                runner = self.get_remote_runner(node)
            except AuthenticationException:
                #print(f'node {node} cannot be accessed')
                continue
            except TimeoutError:
                #print(f'node {node} cannot be accessed')
                continue
            if runner.file_exists(self.lock_file):
                #print(f'node {node} in use, going to next node...')
                del runner
                continue
            else:
                runner.create_file(self.lock_file)
                self.runner = runner
                self.set('ip_addresses', node)
                print(f'node {node} available')
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