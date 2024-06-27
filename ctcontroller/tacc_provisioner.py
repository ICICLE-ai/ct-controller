from .provisioner import Provisioner
import os

class TACCProvisioner(Provisioner):
    def __init__(self, cfg):
        cfg['key_name'] = 'default'
        super(TACCProvisioner, self).__init__(cfg)
        self.set('remote_id', cfg['user_name'])

        # If only registering or checking, do not setup provision variables
        #if cmd == 'register' or cmd == 'check':
        #    return


        self.available_nodes = {
                                     'x86': [],
                                     'jetson': [
                                                'cicnano01.tacc.utexas.edu',
                                                'cicnano02.tacc.utexas.edu',
                                                'cicnano03.tacc.utexas.edu'
                                               ],
                                     'rpi': []
                                    }
        self.set('lock_file', 'ctcontroller.lock')
        self.set('ip_addresses', None)

    #def set(self, name: str, value):
    #    if name not in super().__dict__.keys() or  super().__getattribute__(name) is None:
    #        super().__setattr__(name, value)
    #        print(f'setting {name} to {value}')
    #    #else:
    #    #    print(f'Not setting {name} to {value}. Already defined as {super().__getattribute__(name)}')
    #    #if self.cmd == 'provision':
    #    with open(self.provision_dir + '/provision.yaml', 'a+') as f:
    #        f.write(f'{name}: {value}\n')

    def wait_available_node(self, node_type):
        import time
        print('Waiting for a node to be available')
        while self.reserve_node(node_type) == False:
            print('.', end='')
            time.sleep(3)
        print('\n')


    def reserve_node(self, node_type):
        from .remote import AuthenticationException
        available_nodes = self.available_nodes[node_type]
        if available_nodes == []:
            raise Exception(f'No node of type {node_type} is available')
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

    #def load_user_cache(self):
    #    # load ssh keys
    #    if os.path.exists(self.user_cache):
    #        from pickle import load
    #        with open(self.user_cache, 'rb') as p:
    #            self.env.update(load(p))
    #            self.ssh_key = load(p)
    #        return True
    #    return False

    #def save_user_cache(self):
    #    super(TACCProvisioner, self).save_user_cache()
    #    # save ssh keys
    #    from pickle import dump, HIGHEST_PROTOCOL
    #    with open(self.user_cache, 'ab') as p:
    #        dump(self.ssh_key, p, HIGHEST_PROTOCOL)


    #def provision_instance(self, nnodes: int, cpu: str, gpu: str, node_type: str):
    def provision_instance(self):
        #self.select_node()
        self.wait_available_node(self.node_type)
        #self.reserve_node(node_type)

    def release_node(self):
        self.get_remote_runner().delete_file(self.lock_file)

    def shutdown_instance(self):
        self.release_node()