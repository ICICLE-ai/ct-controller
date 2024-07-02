import os
from re import search
from subprocess import run
import openstackclient.shell as shell
from .provisioner import Provisioner
from .error import print_and_exit
import random
import string
import yaml

subcommand_map = {
    'lease': ['reservation', 'lease'],
    'server': ['server'],
    'ip': ['floating', 'ip'],
    'image': ['image']
}

class ChameleonProvisioner(Provisioner):
    def __init__(self, cfg):
        self.site = cfg['site']
        cfg['user_name_required'] = False
        super(ChameleonProvisioner, self).__init__(cfg)


        subsite = self.site.split('@')[1].lower()

        # set Chameleon-specific environment variables
        os.environ['OS_AUTH_TYPE'] = 'v3applicationcredential'
        os.environ['OS_AUTH_URL'] = f'https://chi.{subsite}.chameleoncloud.org:5000/v3'
        os.environ['OS_IDENTITY_API_VERSION'] = '3'
        os.environ['OS_REGION_NAME'] = self.site
        os.environ['OS_INTERFACE'] = 'public'

        # ensure that app credentials are already defined in the environment
        if os.environ.get('OS_APPLICATION_CREDENTIAL_ID') is None or os.environ.get('OS_APPLICATION_CREDENTIAL_SECRET') is None:
            print_and_exit('Chameleon Application credentials must be specified in the environment')

        # Configure lease and instance names
        if 'job_id' not in cfg:
            self.job_id = ''.join(random.choices(string.ascii_letters, k=7))
        self.set('lease_name',self.job_id + '-lease')
        self.set('ip_lease_name', self.job_id + '-ip-lease')
        self.set('server_name', self.job_id + '-server')

        # Set network id
        cmd = ['openstack', 'network', 'list', '--name', 'sharednet1', '-c', 'ID', '-f', 'value']
        network_id, _ = self.capture_shell(cmd)
        self.set('network_id', network_id)
        
        # Set public network id
        cmd = ['openstack', 'network', 'show', 'public', '-c', 'id', '-f', 'value']
        public_network_id, _ = self.capture_shell(cmd)
        self.set('public_network_id', public_network_id)

        # Parameters set during provisioning
        self.set('lease_id', None)
        self.set('ip_lease_id', None)
        self.set('ip_addresses', None)
        self.set('reservation_id', None)
        self.set('ip_reservation_id', None)
        self.set('image', None)
        self.set('remote_id', 'cc')
        self.set('cpu_arch', self.get_cpu_arch())

    def lookup_auth(self, config_path):
        if not os.path.exists(config_path):
            raise Exception('Config file not found')
        with open(config_path, 'r') as f:
            auth = yaml.safe_load(f)
        if self.user not in auth['Users']:
            print_and_exit(f'{self.user} does not have appropriate permissions to launch with a service account.')
        self.set('key_name', auth[self.site]['Name'])
        self.set('private_key', auth[self.site]['Path'])
        os.environ['OS_APPLICATION_CREDENTIAL_ID'] = auth[self.site]['ID']
        os.environ['OS_APPLICATION_CREDENTIAL_SECRET'] = auth[self.site]['Secret']

    def get_cpu_arch(self):
        cmd = ['openstack', 'reservation', 'host', 'list', '-f',
               'csv', '-c', 'node_type', '-c', 'architecture.platform_type', '-c', 'cpu_arch']
        all_nodes, _ = self.capture_shell(cmd)
        for node in all_nodes.split('\n'):
            if f'"{self.node_type}"' in node:
                break
        node = node.replace(self.node_type, '')
        node_info = node.split(',')
        for i in node_info:
            arch  = i.strip("\"")
            if arch != '':
                return arch
        else: #platform == '' and arch == ''
            print_and_exit(f'Cannot determine CPU architecture of specified node type {self.node_type}')
        

    def run_check(self, check_type=''):
        cmd = subcommand_map.get(check_type)
        if cmd is None:
            raise print_and_exit(f'"{check_type}" is not a valid input to the check subcommand')
    
        cmd.append('list')
        shell.main(cmd)
    
    def available_hosts(self):
        cmd = ['openstack', 'reservation', 'host', 'list',
               '-c', 'node_type',
               '-c', 'gpu.gpu',
               '-c', 'architecture.platform_type',
               '-c', 'processor.other_description']
        out, _ = self.capture_shell(cmd)
        return out
    
    def get_node_type(self, cpu, gpu):
        pass
    
    def reserve_lease(self):
        print('Reserving lease for physical nodes')
        resource_properties = f'["==", "$node_type", "{self.node_type}"]'
        reservation = f'min={self.num_nodes},max={self.num_nodes},resource_type=physical:host,resource_properties={resource_properties}'
        cmd = ['openstack'] + subcommand_map['lease'] + ['create', '--reservation', reservation, self.lease_name, '-f', 'value', '-c', 'id']
        print(' '.join(cmd))
        lease_out, _ = self.capture_shell(cmd)
        lease_id = lease_out.split('\n')[1]
        self.set('lease_id', lease_id)
    
    def check_lease_ready(self, lease_name, lease_id):
        cmd = ['openstack', 'reservation', 'lease', 'show', lease_id, '-c', 'status', '-f', 'value']
        status, _ = self.capture_shell(cmd)
        if status == 'ACTIVE':
            return True
        elif status == 'ERROR':
            raise print_and_exit(f'The {lease_name} lease failed during provisioning.')
        elif status == 'TERMINATED':
            raise print_and_exit(f'The lease {lease_name} has been terminated.')
        elif status == 'STARTING':
            return False
        elif status == 'PENDING':
            return False
        else:
            raise print_and_exit(f'Lease in invalid state: {status}')

    def check_server_ready(self, server_name):
        cmd = ['openstack', 'server', 'show', server_name, '-c', 'status', '-f', 'value']
        status, _ = self.capture_shell(cmd)
        if status == 'ACTIVE':
            return True
        elif status == 'BUILD':
            return False
        elif status == 'STARTING':
            return False
        elif status == 'TERMINATED':
            raise print_and_exit(f'Server {server_name} instance was terminated')
        elif status == 'ERROR':
            raise print_and_exit(f'Server {server_name} instance could not be created')
        else:
            raise Exception(f'Server {server_name} in invalid state {status}')
    
    def reserve_ip(self):
        cmd = ['openstack'] + subcommand_map['lease'] + ['create', '--reservation', f'resource_type=virtual:floatingip,network_id={self.public_network_id},amount={self.num_nodes}', self.ip_lease_name, '-f', 'value', '-c', 'id']
        print(f'Reserving lease for floating ip addresses\n{cmd}')
        lease_out, err = self.capture_shell(cmd)
        if 'ERROR: Not enough floating IPs available' in err:
            self.shutdown_instance()
            print_and_exit('Leases have been deleted. Try rerunning later.')
        lease_id = lease_out.split('\n')[1]
        self.set('ip_lease_id', lease_id)
    
    def get_reservation_id(self):
        if self.reservation_id is None:
            cmd = ['openstack', 'reservation', 'lease', 'show', self.lease_name, '-c', 'reservations', '-f', 'value']
            out, _ = self.capture_shell(cmd)
            # parse resid
            m=search(r'"id": "([^"]+)"', out )
            self.set('reservation_id', m.groups()[0])
        return self.reservation_id
    
    def select_image(self):
        # get available images
        cmd = ['openstack', 'image', 'list', '-c', 'Name', '-f', 'value', '--tag', 'ct_edge']
        if 'cpu' in self.node_info:
            cmd += ['--tag', self.node_info['cpu']]
        if 'gpu' in self.node_info and self.node_info['gpu'] == True:
            cmd += ['--tag', 'gpu']
        print(cmd)
        image, _ = self.capture_shell(cmd)
        self.set('image', image)
    
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
        server_id, _ = self.capture(cmd)
        self.set('server_id', server_id)
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
        out, _ = self.capture_shell(cmd)
        m  = search(r'"id": "([^"]+)"', out )
        resid = m.groups()[0]
        self.set('ip_reservation_id', resid)
    
    def get_ip_addresses(self):
        self.get_ip_reservation_id()
        cmd = ['openstack'] + subcommand_map['ip'] + ['list', '--tags', f'blazar,reservation:{self.ip_reservation_id}', '-c', 'Floating IP Address', '-f', 'value']
        print(cmd)
        ip_addresses = self.capture_shell(cmd)
        self.set('ip_addresses', ip_addresses)
    
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
        #print(f'{check_cmd=}')
        #print(self.capture_shell(check_cmd))
        while self.capture_shell(check_cmd) == '':
            time.sleep(3)
    
    def allocate_ip(self):
        cmd = subcommand_map['lease'] + ['create', '--reservation', f'resource_type=virtual:floatingip,network_id={self.public_network_id},amount=1', self.ip_lease_name]
        print(cmd)
        shell.main(cmd)

    def set_node_info(self):
        self.set('node_info',{'cpu': self.cpu_arch, 'gpu': self.gpu, 'node_type': self.node_type})
    
    def provision_instance(self):
        self.set_node_info()
        self.select_image()
        self.reserve_lease()
        self.reserve_ip()
        self.create_instance()
        self.associate_ip()
        self.connect()
        self.check_connection() # ssh into instance

    def shutdown_instance(self):
        self.delete_server()
        self.delete_leases()
