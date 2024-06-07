from __init__ import subcommand_map
from re import search
from subprocess import run
import openstackclient.shell as shell
from controller import Controller
#import logging
#logger = logging.getLogger(__name__)

class ChameleonController(Controller):
    def __init__(self, site: str, provision_id: str=None, config_file: str=None, user_name: str=None, private_key: str=None, key_name: str=None):
        self.key_name = key_name
        self.private_key = private_key
        super(ChameleonController, self).__init__(site, config_file, user_name)
        if provision_id is None:
            self.set_provision_id()
        else:
            self.provision_id = provision_id
        self.provision_dir = f'{self.user_dir}/provisions/{self.provision_id}'
        self.lease_name = None
        self.ip_lease_name = None
        self.ip_addresses = []
        self.image = []
        self.public_network_id = None
        self.server_name = None
        self.reservation_id = None
        self.ip_reservation_id = None
        self.network_id = None
        self.lease_id = None

    def load_user_cache(self):
        import os
        # load ssh keys
        if os.path.exists(self.user_cache):
            from pickle import load
            with open(self.user_cache, 'rb') as p:
                self.env.update(load(p))
                self.ssh_key = load(p)
            return True
        return False

    def save_user_cache(self):
        super(ChameleonController, self).save_user_cache()
        # save ssh keys
        from pickle import dump, HIGHEST_PROTOCOL
        with open(self.user_cache, 'ab') as p:
            dump(self.ssh_key, p, HIGHEST_PROTOCOL)

    def get_user_name(self, user_config_file):
        if user_config_file:
            with open(user_config_file, 'r') as f:
                for line in f.readlines():
                    if 'OS_USERNAME' in line:
                        try:
                            self.user_name = line.split('=')[1].replace("\"", "").strip()
                            return
                        except IndexError:
                            continue


    def setup_user(self):
        # Read config file
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
        # Set ssh key info from command line
        self.ssh_key = {'name': self.key_name, 'path': self.private_key}

    def capture_shell(self, cmd):
        if isinstance(cmd, str):
            cmd = cmd.split(' ')
        elif isinstance(cmd, list):
            pass
        else:
            raise Exception('Invalid shell command')
        p = run(cmd, capture_output=True)
        out = p.stdout.decode('utf-8').strip()
        return out
    
    def run_check(self, check_type=''):
        cmd = subcommand_map.get(check_type)
        if cmd is None:
            raise Exception(f'"{check_type}" is not a valid input to the check subcommand')
    
        cmd.append('list')
        shell.main(cmd)
    
    def available_hosts(self):
        cmd = ['reservation', 'host', 'list',
               '-c', 'node_type',
               '-c', 'gpu.gpu',
               '-c', 'architecture.platform_type',
               '-c', 'processor.other_description']
        out = self.capture_shell(cmd)
        return out
    
    def get_node_type(self, cpu, gpu):
        pass
    
    def get_leasename(self):
        if self.lease_name is None:
            self.lease_name = self.provision_id + '-lease'
        return self.lease_name
    
    def reserve_lease(self, nnodes, node_type):
        print('Reserving lease for physical nodes')
        resource_properties = f'["==", "$node_type", "{node_type}"]'
        reservation = f'min={nnodes},max={nnodes},resource_type=physical:host,resource_properties={resource_properties}'
        cmd = subcommand_map['lease'] + ['create', '--reservation', reservation, self.get_leasename()]
        print(' '.join(cmd))
        shell.main(cmd)
    
    def get_public_network_id(self):
        cmd = ['openstack', 'network', 'show', 'public', '-c', 'id', '-f', 'value']
        self.public_network_id = self.capture_shell(cmd)
        return self.public_network_id
    
    def get_lease_status(self, lease):
        cmd = ['openstack', 'reservation', 'lease', 'show', lease, '-c', 'status', '-f', 'value']
        print(cmd)
        return self.capture_shell(cmd)
    
    def check_leases_ready(self):
        physical = self.get_lease_status(self.lease_name)
        ip = self.get_lease_status(self.ip_lease_name)
        if physical  == 'ACTIVE' and  ip == 'ACTIVE':
            return True
        elif physical == 'ERROR':
            raise Exception('The hardware lease failed during provisioning.')
        elif ip == 'ERROR':
            raise Exception('The floating IP lease failed during provisioning.')
        elif physical == 'TERMINATED':
            raise Exception('The hardware lease has been terminated.')
        elif ip == 'TERMINATED':
            raise Exception('The floating IP lease has been terminated.')
        elif physical == 'PENDING' or ip == 'PENDING':
            return False
        else:
            raise Exception('Lease in invalid state')

    def check_server_ready(self, server_name):
        cmd = ['openstack', 'server', 'show', server_name, '-c', 'status', '-f', 'value']
        status = self.capture_shell(cmd)
        if status == 'ACTIVE':
            return True
        elif status == 'BUILD':
            return False
        elif status == 'TERMINATED':
            raise Exception(f'Server {server_name} instance was terminated')
        elif status == 'ERROR':
            raise Exception(f'Server {server_name} instance could not be created')
        else:
            raise Exception('Server in invalid state')
    
    def get_ip_leasename(self):
        if self.ip_lease_name is None:
            self.ip_lease_name = self.provision_id + '-ip-lease'
        return self.ip_lease_name
    
    def reserve_ip(self, num):
        print('Reserving lease for floating ip addresses')
        cmd = subcommand_map['lease'] + ['create', '--reservation', f'resource_type=virtual:floatingip,network_id={self.get_public_network_id()},amount={num}', self.get_ip_leasename()]
        print(cmd)
        shell.main(cmd)
    
    def get_network_id(self):
        if self.network_id is None:
            cmd = ['openstack', 'network', 'list', '--name', 'sharednet1', '-c', 'ID', '-f', 'value']
            self.network_id = self.capture_shell(cmd)
        return self.network_id
    
    def get_lease_id(self):
        if self.lease_id is None:
            cmd = ['openstack', 'reservation', 'lease', 'show', self.get_leasename(), '-c', 'id', '-f', 'value']
            self.lease_id = self.capture_shell(cmd)
        return self.lease_id
    
    def get_reservation_id(self):
        if self.reservation_id is None:
            cmd = ['openstack', 'reservation', 'lease', 'show', self.get_leasename(), '-c', 'reservations', '-f', 'value']
            out = self.capture_shell(cmd)
            # parse resid
            # sed command: sed -En 's/.*"id": "([^"]*).*/\1/p') $resid
            m=search(r'"id": "([^"]+)"', out )
            self.reservation_id = m.groups()[0]
        return self.reservation_id
    
    def get_image_name(self):
        # get available images
        if self.image == []:
            cmd = ['openstack', 'image', 'list', '-c', 'Name', '-f', 'value', '--tag', 'ct_edge']
            if 'cpu' in self.node_info:
                cmd += ['--tag', self.node_info['cpu']]
            if 'gpu' in self.node_info and self.node_info['gpu'] == True:
                cmd += ['--tag', self.node_info['gpu']]
            print(cmd)
            self.image = self.capture_shell(cmd)
        return self.image
    
    def get_server_name(self):
        if self.server_name is None:
            self.server_name = self.provision_id + '-server'
        return self.server_name
    
    def create_instance(self):
        import time
        # wait until reservations are ready
        print('Waiting for reservation leases to start')
        while self.check_leases_ready() == False:
            print('.', end='')
            time.sleep(3)
        print('Creating instance on the lease')
        cmd = subcommand_map['server'] + ['create', '--image', self.get_image_name(),
                                          '--network', self.get_network_id(),
                                          '--flavor', 'baremetal',
                                          '--key-name', self.ssh_key['name'],
                                          '--hint', f'reservation={self.get_reservation_id()}',
                                          self.get_server_name()]
        print(cmd)
        shell.main(cmd)
    
    def delete_server(self):
        cmd = subcommand_map['server'] + ['delete', self.server_name]
        shell.main(cmd)

    def delete_leases(self):
        cmd = subcommand_map['lease'] + ['delete', self.lease_name]
        shell.main(cmd)
        cmd = subcommand_map['lease'] + ['delete', self.ip_lease_name]
        shell.main(cmd)
    
    def get_ip_reservation_id(self):
        cmd = ['openstack'] + subcommand_map['lease'] + ['show', self.get_ip_leasename(), '-c', 'reservations', '-f', 'value']
        out = self.capture_shell(cmd)
        #print(f'cmd: {cmd}')
        #print(f'resout: {out}')
        m=search(r'"id": "([^"]+)"', out )
        resid = m.groups()[0]
        return resid
    
    def get_ip_addresses(self):
        ipres_id = self.get_ip_reservation_id()
        cmd = ['openstack'] + subcommand_map['ip'] + ['list', '--tags', f'blazar,reservation:{ipres_id}', '-c', 'Floating IP Address', '-f', 'value']
        return self.capture_shell(cmd)
    
    def associate_ip(self):
        import time
        while self.check_server_ready(self.server_name) == False:
            time.sleep(3)
        print("Associating floating IP address with instance")
        ip_addresses = self.get_ip_addresses()
        cmd = subcommand_map['server'] + ['add', 'floating', 'ip', self.get_server_name(), ip_addresses]
        shell.main(cmd)
        check_cmd = ['openstack', 'server', 'show', self.get_server_name(), '-c', 'addresses', '-f', 'value']
        print(f'{check_cmd=}')
        print(self.capture_shell(check_cmd))
        while self.capture_shell(check_cmd) == '':
            time.sleep(3)
    
    def allocate_ip(self):
        cmd = subcommand_map['lease'] + ['create', '--reservation', f'resource_type=virtual:floatingip,network_id={self.get_public_network_id()},amount=1', self.get_ip_leasename()]
        print(cmd)
        shell.main(cmd)
    
    def connect(self):
        from remote import RemoteRunner
        self.ip_addresses = self.get_ip_addresses()
        self.runner = RemoteRunner(self.ip_addresses, 'cc', self.ssh_key['path'])

    def check_connection(self):
        remote_hostname = self.runner.run('hostname')
        if remote_hostname == self.get_server_name():
            print('Connected')
            return True
        else:
            print('Connection Failed')
            return False

    def set_node_info(self, cpu, gpu, node_type):
        if node_type is None:
            node_type = self.get_node_type(cpu, gpu)
        self.node_info = {'cpu': cpu, 'gpu': gpu, node_type: node_type}
    
    def set_provision_id(self):
        import os
        top_provision_dir = f'{self.user_dir}/provisions'
        if os.path.exists(top_provision_dir):
            subdirs = [f.path for f in os.scandir(top_provision_dir) if f.is_dir()]
            numbered_subdirs = [-1] + [int(d) for d in subdirs if d.isdigit()]
            self.provision_id = str(max(numbered_subdirs) + 1)
        else:
            os.makedirs(top_provision_dir, exist_ok=True)
            self.provision_id = '0'

    def provision_instance(self, nnodes: int, cpu: str, gpu: str, node_type: str):
        self.set_node_info(cpu, gpu, node_type)
        self.get_image_name()
        self.reserve_lease(nnodes, node_type)
        self.reserve_ip(nnodes)
        self.create_instance()
        #self.allocate_ip() #duplicate?
        self.associate_ip()
        self.connect()
        self.check_connection() # ssh into instance

    def shutdown_instance(self):
        self.delete_server()
        self.delete_leases()
        pass
