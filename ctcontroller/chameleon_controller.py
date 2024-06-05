from __init__ import subcommand_map
from re import search
from subprocess import run
import openstackclient.shell as shell
from controller import Controller
#import logging
#logger = logging.getLogger(__name__)
#from controller import Controller

#def print_leases2():
#    print('running with api')
#    import openstack
#    from blazarclient import client as blazar_client
#    conn = openstack.connect()
#    sess = conn.session
#    blazar = blazar_client.Client(session=sess)
#    leases = blazar.lease.list()
#    for lease in leases:
#        print(f"Lease ID: {lease['id']}, Name: {lease['name']}, Status: {lease['status']}")
#
#def print_leases3(env):
#    print('running as subprocess')
#    from subprocess import run, CalledProcessError
#    cmd = ['openstack', 'reservation', 'lease', 'list']
#    p = run(cmd, capture_output=True, env=env)
#    print(f'cmd={" ".join(cmd)}')
#    print(f'{p.stdout=}')
#    print(f'{p.stderr=}')
#
#def print_leases():
#    print('running openstack client shell')
#    shell.main(['reservation', 'lease', 'list'])

class ChameleonController(Controller):
    def __init__(self, config_file=None):
        self.lease_name = None
        self.ip_lease_name = None
        self.key_name = None
        self.ip_addresses = []
        self.image = []
        self.public_network_id = None
        self.server_name = None
        self.reservation_id = None
        self.ip_reservation_id = None
        self.pkey_path = '/Users/skhuvis/.ssh/id_rsa_icicle'
        super(ChameleonController, self).__init__(config_file)

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
        return 'my-app-lease'
    
    def reserve_lease(self, nnodes, node_type):
        print('Reserving lease for physical nodes')
        resource_properties = f'["==", "$node_type", "{node_type}"]'
        reservation = f'min={nnodes},max={nnodes},resource_type=physical:host,resource_properties={resource_properties}'
        cmd = subcommand_map['lease'] + ['create', '--reservation', reservation, self.get_leasename()]
        print(' '.join(cmd))
        shell.main(cmd)
    
    def get_public_network_id(self):
        cmd = ['openstack', 'network', 'show', 'public', '-c', 'id', '-f', 'value']
        return self.capture_shell(cmd)
    
    def get_lease_status(self, lease):
        cmd = ['openstack', 'reservation', 'lease', 'show', lease, '-c', 'status', '-f', 'value']
        return self.capture_shell(cmd)
    
    def get_ip_leasename(self):
        return 'my-app-ip-lease'
    
    def reserve_ip(self, num):
        print('Reserving lease for floating ip addresses')
        PUBLIC_NETWORK_ID = self.get_public_network_id()
        cmd = subcommand_map['lease'] + ['create', '--reservation', f'resource_type=virtual:floatingip,network_id={PUBLIC_NETWORK_ID},amount={num}', self.get_ip_leasename()]
        print(cmd)
        shell.main(cmd)
    
    def get_network_id(self):
        cmd = ['openstack', 'network', 'list', '--name', 'sharednet1', '-c', 'ID', '-f', 'value']
        return self.capture_shell(cmd)
    
    def get_lease_id(self):
        cmd = ['openstack', 'reservation', 'lease', 'show', self.get_leasename(), '-c', 'id', '-f', 'value']
        return self.capture_shell(cmd)
    
    def get_reservation_id(self):
        cmd = ['openstack', 'reservation', 'lease', 'show', self.get_leasename(), '-c', 'reservations', '-f', 'value']
        out = self.capture_shell(cmd)
        # parse resid
        # sed command: sed -En 's/.*"id": "([^"]*).*/\1/p') $resid
        m=search(r'"id": "([^"]+)"', out )
        resid = m.groups()[0]
        return resid
    
    def get_image_name(self, node_info):
        # get available images
        cmd = ['openstack', 'image', 'list', '-c', 'Name', '-f', 'value', '--tag', 'ct_edge']
        if 'cpu' in node_info:
            cmd += ['--tag', node_info['cpu']]
        if 'gpu' in node_info and node_info.gpu == True:
            cmd += ['--tag', node_info['gpu']]
        print(cmd)
        return self.capture_shell(cmd)
    
    def get_key_name(self):
        return 'macbook'
    
    def get_server_name(self):
        return 'my-app-server'
    
    def create_instance(self, node_info):
        # wait until reservations are ready
        print('Waiting for reservation leases to start')
        # Code to poll for active reservation
        print('Creating instance on the lease')
        cmd = subcommand_map['server'] + ['create', '--image', self.get_image_name(node_info), '--network', self.get_network_id(), '--flavor', 'baremetal', '--key-name', self.get_key_name(), '--hint', f'reservation={self.get_reservation_id()}', self.get_server_name()]
        print(cmd)
        shell.main(cmd)
    
    def get_ip_reservation_id(self):
        cmd = ['openstack'] + subcommand_map['lease'] + ['show', self.get_ip_leasename(), '-c', 'reservations', '-f', 'value']
        out = self.capture_shell(cmd)
        m=search(r'"id": "([^"]+)"', out )
        resid = m.groups()[0]
        return resid
    
    def get_ip_addresses(self):
        ipres_id = self.get_ip_reservation_id()
        cmd = ['openstack'] + subcommand_map['ip'] + ['list', '--tags', f'blazar,reservation:{ipres_id}', '-c', 'Floating IP Address', '-f', 'value']
        return self.capture_shell(cmd)
    
    def associate_ip(self):
        print("Associating floating IP address with instance")
        ip_addresses = self.get_ip_addresses()
        cmd = subcommand_map['server'] + ['add', 'floating', 'ip', self.get_server_name(), ip_addresses]
        shell.main(cmd)
    
    def allocate_ip(self):
        cmd = subcommand_map['lease'] + ['create', '--reservation', f'resource_type=virtual:floatingip,network_id={self.get_public_network_id()},amount=1', self.get_ip_leasename()]
        print(cmd)
        shell.main(cmd)
    
    def connect(self):
        from remote import RemoteRunner
        self.ip_addresses = self.get_ip_addresses()
        self.runner = RemoteRunner(self.ip_addresses, 'cc', self.pkey_path)

    def check_connection(self):
        #import paramiko
        #key_path = '/Users/skhuvis/.ssh/id_rsa_icicle'
        #pkey = paramiko.RSAKey.from_private_key_file(key_path)
        #client = paramiko.SSHClient()
        #policy = paramiko.AutoAddPolicy()
        #client.set_missing_host_key_policy(policy)
    
        #ip = self.get_ip_addresses()
        #print("Connecting to server")
        #client.connect(ip, username='cc', pkey=pkey)
        remote_hostname = self.runner.run('hostname')
        if remote_hostname == self.get_server_name():
            print('Connected')
            return True
        else:
            print('Connection Failed')
            return False
    
    def deploy_instance(self, nnodes: int, cpu: str, gpu: str, node_type: str):
        import sys
        if node_type is None:
            node_type = self.get_node_type(cpu, gpu)
        node_info = {'cpu': cpu} # get node info from lease
        #get_image_name(node_info)
        #reserve_lease(nnodes, node_type)
        #reserve_ip(nnodes)
        #create_instance(node_info)
        #allocate_ip()
        #associate_ip()
        self.connect()
        self.check_connection() # ssh into instance
    
    def poll_instance(self):
        pass
    
    def shutdown_instance(self):
        pass