import os
from __init__ import subcommand_map
from re import search
from subprocess import run
import openstackclient.shell as shell
from controller import Controller
#import logging
#logger = logging.getLogger(__name__)

class ChameleonController(Controller):
    def __init__(self, site: str, cmd: str, provision_id: str=None, config_file: str=None, user_name: str=None, private_key: str=None, key_name: str=None):
        self.key_name = key_name
        self.private_key = private_key
        super(ChameleonController, self).__init__(site, cmd, config_file, user_name)

        # If only registering or checking, do not setup provision variables
        if cmd == 'register' or cmd == 'check':
            return

        if provision_id is None:
            provision_id = self.get_provision_id()
        provision_dir = f'{self.user_dir}/provisions/{provision_id}'
        provision_file = f'{provision_dir}/provision.yaml'
        if os.path.exists(provision_file):
            self.read_provision_info(provision_file)
        else:
            os.makedirs(f'{provision_dir}')

        self.set('provision_dir', provision_dir)
        self.set('provision_id', provision_id)

        # Configure lease and instance names
        self.set('lease_name',self.provision_id + '-lease')
        self.set('ip_lease_name', self.provision_id + '-ip-lease')
        self.set('server_name', self.provision_id + '-server')

        # Set network id
        cmd = ['openstack', 'network', 'list', '--name', 'sharednet1', '-c', 'ID', '-f', 'value']
        self.set('network_id', self.capture_shell(cmd))
        
        # Set public network id
        cmd = ['openstack', 'network', 'show', 'public', '-c', 'id', '-f', 'value']
        self.set('public_network_id', self.capture_shell(cmd))

        # Parameters set during provisioning
        self.set('lease_id', None)
        self.set('ip_lease_id', None)
        self.set('ip_addresses', None)
        self.set('reservation_id', None)
        self.set('ip_reservation_id', None)
        self.set('image', None)
        self.set('remote_id', 'cc')

    def load_user_cache(self):
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

        # Assuming application credentials, do not check for password
        ## Attempt to get password from environment variable
        #if self.env.get("CHAMELEON_PASSWORD"):
        #    self.env["OS_PASSWORD"] = self.env.get("CHAMELEON_PASSWORD")
        #else:
        #    password = input('Please enter your chameleon password or pass to the environment variable CHAMELEON_PASSWORD: ')
        #    self.env["OS_PASSWORD"] = password

        # Do not leave empty string as region name
        if self.env.get("OS_REGION_NAME") is not None and self.env.get("OS_REGION_NAME") == "":
            del self.env["OS_REGION_NAME"]
        # Set ssh key info from command line
        self.ssh_key = {'name': self.key_name, 'path': self.private_key}

    def set(self, name: str, value):
        if name not in super().__dict__.keys() or  super().__getattribute__(name) is None:
            super().__setattr__(name, value)
            print(f'setting {name} to {value}')
        #else:
        #    print(f'Not setting {name} to {value}. Already defined as {super().__getattribute__(name)}')
        if self.cmd == 'provision':
            with open(self.provision_dir + '/provision.yaml', 'a+') as f:
                f.write(f'{name}: {value}\n')

    def run_check(self, check_type=''):
        cmd = subcommand_map.get(check_type)
        if cmd is None:
            raise Exception(f'"{check_type}" is not a valid input to the check subcommand')
    
        cmd.append('list')
        shell.main(cmd)
    
    def available_hosts(self):
        cmd = ['openstack', 'reservation', 'host', 'list',
               '-c', 'node_type',
               '-c', 'gpu.gpu',
               '-c', 'architecture.platform_type',
               '-c', 'processor.other_description']
        out = self.capture_shell(cmd)
        return out
    
    def get_node_type(self, cpu, gpu):
        pass
    
    #def get_leasename(self):
    #    if self.lease_name is None:
    #        self.set('lease_name',self.provision_id + '-lease')
    #    return self.lease_name
    
    def reserve_lease(self, nnodes, node_type):
        print('Reserving lease for physical nodes')
        resource_properties = f'["==", "$node_type", "{node_type}"]'
        reservation = f'min={nnodes},max={nnodes},resource_type=physical:host,resource_properties={resource_properties}'
        cmd = ['openstack'] + subcommand_map['lease'] + ['create', '--reservation', reservation, self.lease_name, '-f', 'value', '-c', 'id']
        print(' '.join(cmd))
        lease_out = self.capture_shell(cmd)
        lease_id = lease_out.split('\n')[1]
        self.set('lease_id', lease_id)
        #shell.main(cmd)
    
    #def get_public_network_id(self):
    #    cmd = ['openstack', 'network', 'show', 'public', '-c', 'id', '-f', 'value']
    #    self.set('public_network_id', self.capture_shell(cmd))
    #    return self.public_network_id
    
    #def get_lease_status(self, lease):
    #    cmd = ['openstack', 'reservation', 'lease', 'show', lease, '-c', 'status', '-f', 'value']
    #    print(cmd)
    #    return self.capture_shell(cmd)
    
    def check_lease_ready(self, lease_name, lease_id):
        cmd = ['openstack', 'reservation', 'lease', 'show', lease_id, '-c', 'status', '-f', 'value']
        status = self.capture_shell(cmd)
        #status= self.get_lease_status(lease_id)
        if status == 'ACTIVE':
            return True
        elif status == 'ERROR':
            raise Exception(f'The {lease_name} lease failed during provisioning.')
        elif status == 'TERMINATED':
            raise Exception(f'The lease {lease_name} has been terminated.')
        elif status == 'PENDING':
            return False
        else:
            raise Exception(f'Lease in invalid state: {status}')

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
            print(f'Server in invalid state {status}')
            raise Exception()
    
    #def get_ip_leasename(self):
    #    if self.ip_lease_name is None:
    #        self.set('ip_lease_name', self.provision_id + '-ip-lease')
    #    return self.ip_lease_name
    
    def reserve_ip(self, num):
        cmd = ['openstack'] + subcommand_map['lease'] + ['create', '--reservation', f'resource_type=virtual:floatingip,network_id={self.public_network_id},amount={num}', self.ip_lease_name, '-f', 'value', '-c', 'id']
        print(f'Reserving lease for floating ip addresses\n{cmd}')
        #shell.main(cmd)
        lease_out = self.capture_shell(cmd)
        lease_id = lease_out.split('\n')[1]
        self.set('ip_lease_id', lease_id)
    
    #def get_network_id(self):
    #    if self.network_id is None:
    #        cmd = ['openstack', 'network', 'list', '--name', 'sharednet1', '-c', 'ID', '-f', 'value']
    #        self.set('network_id', self.capture_shell(cmd))
    #    return self.network_id
    
    #def get_lease_id(self):
    #    if self.lease_id is None:
    #        cmd = ['openstack', 'reservation', 'lease', 'show', self.lease_name, '-c', 'id', '-f', 'value']
    #        self.set('lease_id', self.capture_shell(cmd))
    #    return self.lease_id
    
    def get_reservation_id(self):
        if self.reservation_id is None:
            cmd = ['openstack', 'reservation', 'lease', 'show', self.lease_name, '-c', 'reservations', '-f', 'value']
            out = self.capture_shell(cmd)
            # parse resid
            # sed command: sed -En 's/.*"id": "([^"]*).*/\1/p') $resid
            m=search(r'"id": "([^"]+)"', out )
            self.set('reservation_id', m.groups()[0])
        return self.reservation_id
    
    def select_image(self):
        # get available images
        cmd = ['openstack', 'image', 'list', '-c', 'Name', '-f', 'value', '--tag', 'ct_edge']
        if 'cpu' in self.node_info:
            cmd += ['--tag', self.node_info['cpu']]
        if 'gpu' in self.node_info and self.node_info['gpu'] == True:
            cmd += ['--tag', self.node_info['gpu']]
        print(cmd)
        self.set('image', self.capture_shell(cmd))
    
    #def get_server_name(self):
    #    if self.server_name is None:
    #        self.set('server_name', self.provision_id + '-server')
    #    return self.server_name
    
    def create_instance(self):
        import time
        # wait until reservations are ready
        print('Waiting for reservation leases to start', end='')
        while self.check_lease_ready(self.ip_lease_name, self.ip_lease_id) == False or self.check_lease_ready(self.lease_name, self.lease_id) == False:
            print('.', end='')
            time.sleep(3)
        print('\n')
        print('Creating instance on the lease')
        cmd = ['openstack'] + subcommand_map['server']  \
                            + ['create', '--image', self.image,
                               '--network', self.network_id,
                               '--flavor', 'baremetal',
                               '--key-name', self.ssh_key['name'],
                               '--hint', f'reservation={self.get_reservation_id()}',
                               '-c', 'id', '-f', 'value',
                               self.server_name]
        print(cmd)
        #shell.main(cmd)
        self.set('server_id', self.capture_shell(cmd))
        # Set ip address for instance
        self.get_ip_addresses()
    
    def delete_server(self):
        cmd = subcommand_map['server'] + ['delete', self.server_name]
        shell.main(cmd)

    def delete_leases(self):
        cmd = subcommand_map['lease'] + ['delete', self.lease_name]
        shell.main(cmd)
        cmd = subcommand_map['lease'] + ['delete', self.ip_lease_name]
        shell.main(cmd)
    
    def get_ip_reservation_id(self):
        cmd = ['openstack'] + subcommand_map['lease'] + ['show', self.ip_lease_name, '-c', 'reservations', '-f', 'value']
        out = self.capture_shell(cmd)
        #print(f'cmd: {cmd}')
        #print(f'resout: {out}')
        m=search(r'"id": "([^"]+)"', out )
        resid = m.groups()[0]
        self.set('ip_reservation_id', resid)
    
    def get_ip_addresses(self):
        cmd = ['openstack'] + subcommand_map['ip'] + ['list', '--tags', f'blazar,reservation:{self.get_ip_reservation_id}', '-c', 'Floating IP Address', '-f', 'value']
        self.set('ip_addresses', self.capture_shell(cmd))
    
    def associate_ip(self):
        import time
        print('Waiting for server to be ready', end='')
        while self.check_server_ready(self.server_id) == False:
            print('.', end='')
            time.sleep(3)
        print('\n')
        print("Associating floating IP address with instance")
        cmd = subcommand_map['server'] + ['add', 'floating', 'ip', self.server_name, self.ip_addresses]
        shell.main(cmd)
        check_cmd = ['openstack', 'server', 'show', self.server_name, '-c', 'addresses', '-f', 'value']
        print(f'{check_cmd=}')
        print(self.capture_shell(check_cmd))
        while self.capture_shell(check_cmd) == '':
            time.sleep(3)
    
    def allocate_ip(self):
        cmd = subcommand_map['lease'] + ['create', '--reservation', f'resource_type=virtual:floatingip,network_id={self.public_network_id},amount=1', self.ip_lease_name]
        print(cmd)
        shell.main(cmd)
    
    def set_node_info(self, cpu, gpu, node_type):
        if node_type is None:
            node_type = self.get_node_type(cpu, gpu)
        self.set('node_info',{'cpu': cpu, 'gpu': gpu, 'node_type': node_type})
    
    def provision_instance(self, nnodes: int, cpu: str, gpu: str, node_type: str):
        self.set_node_info(cpu, gpu, node_type)
        self.select_image()
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