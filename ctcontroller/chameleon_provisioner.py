"""Contains the ChameleonProvisioner for provisioning hardware on Chameleon Cloud."""

from re import search
import os
import time
import yaml
import logging
import openstackclient.shell as shell
from .provisioner import Provisioner
from .util import ProvisionException, capture_shell

LOGGER = logging.getLogger("CT Controller")
subcommand_map = {
    'lease': ['reservation', 'lease'],
    'server': ['server'],
    'ip': ['floating', 'ip'],
    'image': ['image']
}

class ChameleonProvisioner(Provisioner):
    """
    A subclass of the Provisioner class to handle the provisioning and deprovisioning
    of hardware on Chameleon Cloud.

    Attributes:

        lease_name (str): 
        ip_lease_name (str): 
        server_name (str): 
        network_id (str): 
        public_network_id (str): 
        lease_id (str): 
        ip_lease_id (str): 
        reservation_id (str): 
        ip_reservation_id (str): 
        image (str): 
        server_id (str): 
        remote_id (str): 
        cpu_arch (str): 
        node_info (dict): 

    Methods:
        lookup_auth(config_path):
        get_cpu_arch():
        run_check(check_type):
        available_hosts(): 
        reserve_lease():
        check_lease_ready(lease_name, lease_id): 
        check_server_ready(server_name): 
        reserve_ip():
        get_reservation_id():
        select_image():
        create_instance():
        delete_server():
        delete_leases():
        get_ip_reservation_id():
        set_ip_addresses():
        associate_ip():
        provision_instance():
        shutdown_instance():
    
    """

    def __init__(self, cfg):
        cfg['user_name_required'] = False
        super().__init__(cfg)

        subsite = self.site.split('@')[1].lower()

        # set Chameleon-specific environment variables
        os.environ['OS_AUTH_TYPE'] = 'v3applicationcredential'
        os.environ['OS_AUTH_URL'] = f'https://chi.{subsite}.chameleoncloud.org:5000/v3'
        os.environ['OS_IDENTITY_API_VERSION'] = '3'
        os.environ['OS_REGION_NAME'] = self.site
        os.environ['OS_INTERFACE'] = 'public'

        # ensure that app credentials are already defined in the environment
        if (os.environ.get('OS_APPLICATION_CREDENTIAL_ID') is None or
            os.environ.get('OS_APPLICATION_CREDENTIAL_SECRET') is None):
            raise ProvisionException('Chameleon Application credentials must be specified in the environment')

        # Configure lease and instance names
        self.job_id = cfg['job_id']
        self.lease_name = self.job_id + '-lease'
        self.ip_lease_name = self.job_id + '-ip-lease'
        self.server_name = self.job_id + '-server'

        # Set network id
        cmd = ['openstack', 'network', 'list', '--name', 'sharednet1', '-c', 'ID', '-f', 'value']
        network_id, _ = capture_shell(cmd)
        self.network_id = network_id

        # Set public network id
        cmd = ['openstack', 'network', 'show', 'public', '-c', 'id', '-f', 'value']
        public_network_id, _ = capture_shell(cmd)
        self.public_network_id = public_network_id

        # Parameters set during provisioning
        self.lease_id = None
        self.ip_lease_id = None
        self.reservation_id = None
        self.ip_reservation_id = None
        self.image = None
        self.server_id = None
        self.remote_id = 'cc'
        self.cpu_arch = self.get_cpu_arch()
        self.node_info = {'cpu': self.cpu_arch, 'gpu': self.gpu, 'node_type': self.node_type}

    def lookup_auth(self, config_path):
        """
        Reads in the config file (if it exists).
        If the requesting user is authorized, uses any service account specified in the
        config file to sets the key name and private key.
        This extends the base class function to also set openstack application credentials.

            Parameters:
                config_path (str): the path to the config file.
        """

        if not os.path.exists(config_path):
            raise ProvisionException('Config file not found')
        with open(config_path, 'r', encoding='utf-8') as fil:
            auth = yaml.safe_load(fil)
        if ('Users' in auth and self.user not in auth['Users']
            and auth['Settings']['AuthenticateUsers']):
            raise ProvisionException(f'{self.user} does not have appropriate permissions \
                                     to launch with a service account.')
        self.key_name = auth[self.site]['Name']
        self.private_key = auth[self.site]['Path']
        os.environ['OS_APPLICATION_CREDENTIAL_ID'] = auth[self.site]['ID']
        os.environ['OS_APPLICATION_CREDENTIAL_SECRET'] = auth[self.site]['Secret']

    def get_cpu_arch(self):
        """
        Determines the CPU architecture of the requested node type.
        If the architecture cannot be determined it prints an error message and shuts down.

            Returns:
                arch (str): the cpu architecture of the 
        """

        cmd = ['openstack', 'reservation', 'host', 'list', '-f',
               'csv', '-c', 'node_type', '-c', 'architecture.platform_type', '-c', 'cpu_arch']
        all_nodes, _ = capture_shell(cmd)
        for node in all_nodes.split('\n'):
            if f'"{self.node_type}"' in node:
                break
        else:
            node = ''
        node = node.replace(self.node_type, '')
        node_info = node.split(',')
        for i in node_info:
            arch  = i.strip("\"")
            if arch != '':
                break
        else: #arch == ''
            raise ProvisionException(f'Cannot determine CPU architecture of specified \
                           node type {self.node_type}')
        return arch


    def run_check(self, check_type=''):
        """
        Prints the leases, servers, ips, and/or images provisioned/available to the user.

            Parameters:
                check_type(str): which of {lease, server, ip, image} to display.
                                 If not specified print all.
        """

        cmd = subcommand_map.get(check_type)
        if cmd is None:
            raise ProvisionException(f'"{check_type}" is not a valid input to the check \
                           subcommand')
        cmd.append('list')
        shell.main(cmd)

    def available_hosts(self):
        """
        Returns a string containing all hosts available on Chameleon Cloud along with
        their node_type, GPU, platform type and processor description.
        """

        cmd = ['openstack', 'reservation', 'host', 'list',
               '--quote', 'none',
               '-f', 'csv',
               '-c', 'node_type',
               '-c', 'gpu.gpu',
               '-c', 'gpu.gpu_model',
               '-c', 'architecture.platform_type',
               '-c', 'processor.other_description']
        out, _ = capture_shell(cmd)
        return out.split('\n')

    #def get_node_type(self, cpu, gpu):
    #    pass

    def reserve_lease(self):
        """
        Reserves lease for the physical hardware for the specified node type and sets the
        lease_id as an object attribute.
        """

        LOGGER.info('Reserving lease for physical nodes')
        resource_properties = f'["==", "$node_type", "{self.node_type}"]'
        reservation = (f'min={self.num_nodes},max={self.num_nodes},'
                       f'resource_type=physical:host,resource_properties={resource_properties}')
        cmd = ['openstack'] + subcommand_map['lease'] + \
            ['create', '--reservation', reservation, self.lease_name, '-f', 'value', '-c', 'id']
        LOGGER.info(' '.join(cmd))
        lease_out, _ = capture_shell(cmd)
        lease_id = lease_out.split('\n')[1]
        self.lease_id = lease_id

    def check_lease_ready(self, lease_name, lease_id) -> bool:
        """
        Checks whether the lease is active. If the lease failed to allocate prints an
        error message and exits.

            Parameters:
                lease_name (str): the name of the lease
                lease_id (str): the id of the lease

            Returns:
                bool: true if the lease is active and false if it is not
        """

        cmd = ['openstack', 'reservation', 'lease', 'show', lease_id, '-c', 'status', '-f', 'value']
        ready = False
        status, _ = capture_shell(cmd)
        if status == 'ACTIVE':
            ready = True
        elif status == 'ERROR':
            raise ProvisionException(f'The {lease_name} lease failed during provisioning.')
        elif status == 'TERMINATED':
            raise ProvisionException(f'The lease {lease_name} has been terminated.')
        elif status == 'STARTING':
            ready = False
        elif status == 'PENDING':
            ready = False
        else:
            raise ProvisionException(f'Lease in invalid state: {status}')
        return ready

    def check_server_ready(self, server_name) -> bool:
        """
        Checks whether the server is active. If the server failed to initialize prints an
        error message and exits.

            Parameters:
                server_name (str): the name of the server

            Returns:
                bool: true if the server is active and false if it is not
        """

        cmd = ['openstack', 'server', 'show', server_name, '-c', 'status', '-f', 'value']
        ready = False
        status, _ = capture_shell(cmd)
        if status == 'ACTIVE':
            ready = True
        elif status == 'BUILD':
            ready = False
        elif status == 'STARTING':
            ready = False
        elif status == 'TERMINATED':
            raise ProvisionException(f'Server {server_name} instance was terminated')
        elif status == 'ERROR':
            raise ProvisionException(f'Server {server_name} instance could not be created')
        else:
            raise ProvisionException(f'Server {server_name} in invalid state {status}')
        return ready

    def reserve_ip(self):
        """
        Reserves the lease for the floating IP address.
        If no floating IPs are available it shuts down the instance and exits with an error
        message.
        If floating IPs are available, sets the lease id as an object attribute.
        """

        res = (f'resource_type=virtual:floatingip,network_id={self.public_network_id},'
               f'amount={self.num_nodes}')
        cmd = ['openstack'] + subcommand_map['lease'] \
            + ['create', '--reservation', res, self.ip_lease_name, '-f', 'value', '-c', 'id']
        LOGGER.info(f'Reserving lease for floating ip addresses\n{cmd}')
        lease_out, err = capture_shell(cmd)
        if 'ERROR: Not enough floating IPs available' in err:
            #self.shutdown_instance()
            raise ProvisionException('Leases have been deleted. Try rerunning later.')
        lease_id = lease_out.split('\n')[1]
        self.ip_lease_id = lease_id

    def get_reservation_id(self):
        """
        Returns the reservation id of the lease reservation for the physical hardware.
        If it is not already set, parses the lease information sets it as an object attribute.

            Returns:
                reservation_id (str): reservation id of physical hardware lease
        """

        if self.reservation_id is None:
            cmd = ['openstack', 'reservation', 'lease', 'show', self.lease_name, '-c', \
                   'reservations', '-f', 'value']
            out, _ = capture_shell(cmd)
            # parse resid
            match=search(r'"id": "([^"]+)"', out )
            self.reservation_id = match.groups()[0]
        return self.reservation_id

    def select_image(self):
        """
        Looks for valid image that can be used to run the application on the specified hardware.
        If a valid image is found, sets it as an object attribute, else prints
        an error message and exits.
        """

        self.set_gpu_arch()
        # get available images
        cmd = ['openstack', 'image', 'list', '-c', 'Name', '-f', 'value', '--tag', 'ct_edge']
        if 'cpu' in self.node_info:
            cmd += ['--tag', self.node_info['cpu']]
        if 'gpu' in self.node_info and self.node_info['gpu']:
            cmd += ['--tag', 'gpu']
            if self.node_info['gpu_arch'] != '':
                cmd += ['--tag', self.node_info['gpu_arch'].lower()]
        LOGGER.info(cmd)
        image, _ = capture_shell(cmd)
        if image is None or image == '':
            msg = ('Valid image not found for node of type ',
                   f'{self.node_info["cpu"]}',
                   (' with GPU' if self.node_info["gpu"] else ''))
            print(msg)
            raise ProvisionException(msg)
        # if multiple images are compatible, select the first one
        image = image.split('\n')[0]
        self.image = image

    def create_instance(self):
        """
        Creates a server on the provisioned hardware using a compatible image.
        Once the server has been initialized it associates the allocated floating IP with it.
        The server id is set as an object attribute.
        """

        # wait until reservations are ready
        LOGGER.info('Waiting for reservation leases to start')
        while (not self.check_lease_ready(self.ip_lease_name, self.ip_lease_id) or
               not self.check_lease_ready(self.lease_name, self.lease_id)):
            LOGGER.info('.')
            time.sleep(3)
        LOGGER.info('Creating instance on the lease')
        cmd = ['openstack'] + subcommand_map['server']  \
                            + ['create', '--image', self.image,
                               '--network', self.network_id,
                               '--flavor', 'baremetal',
                               '--key-name', self.ssh_key['name'],
                               '--hint', f'reservation={self.get_reservation_id()}',
                               '-c', 'id', '-f', 'value',
                               self.server_name]
        LOGGER.info(cmd)
        server_id, _ = capture_shell(cmd)
        self.server_id = server_id
        # Set ip address for instance
        self.set_ip_addresses()

    def delete_server(self):
        """Deletes the server."""

        cmd = subcommand_map['server'] + ['delete', self.server_name]
        shell.main(cmd)

    def delete_leases(self):
        """Deprovision the leases for the physical hardware and floating IP addresses."""

        cmd = subcommand_map['lease'] + ['delete', self.lease_name]
        shell.main(cmd)
        cmd = subcommand_map['lease'] + ['delete', self.ip_lease_name]
        shell.main(cmd)

    def get_ip_reservation_id(self):
        """Sets the reservation id for the floating IP reservation as an object attribute."""

        cmd = ['openstack'] + subcommand_map['lease'] + \
            ['show', self.ip_lease_name, '-c', 'reservations', '-f', 'value']
        out, _ = capture_shell(cmd)
        match  = search(r'"id": "([^"]+)"', out )
        resid = match.groups()[0]
        self.ip_reservation_id = resid

    def set_ip_addresses(self):
        """
        Sets the IP address reservation by the reservation lease for floating IPs
        as an object attribute.
        """

        if self.ip_addresses is None:
            self.get_ip_reservation_id()
            cmd = ['openstack'] + subcommand_map['ip'] \
                + ['list', '--tags', f'blazar,reservation:{self.ip_reservation_id}', '-c', \
                   'Floating IP Address', '-f', 'value']
            LOGGER.info(cmd)
            ip_addresses, _ = capture_shell(cmd)
            self.ip_addresses = ip_addresses

    def associate_ip(self):
        """
        Once the server has been initialized, associates the reserved floating IP address
        with the server. Then waits for the association has completed before returning.
        """

        LOGGER.info('Waiting for server to be ready')
        while not self.check_server_ready(self.server_id):
            LOGGER.info('.')
            time.sleep(3)
        LOGGER.info("Associating floating IP address with instance")
        cmd = subcommand_map['server'] + ['add', 'floating', 'ip', self.server_name, \
                                          self.ip_addresses]
        shell.main(cmd)
        check_cmd = ['openstack', 'server', 'show', self.server_name, '-c', 'addresses', '-f', \
                     'value']
        address = ''
        while address == '':
            time.sleep(3)
            address, _ = capture_shell(check_cmd)

    def set_device_id(self):
        """Sets the device id of the provisioned node as an object attribute."""

        self.set_ip_addresses()
        runner = self.get_remote_runner()
        node_id = runner.run("curl -s 169.254.169.254/openstack/latest/vendor_data2.json \
                             | jq -M '.chameleon.node'").strip('"')
        cmd = ['openstack', 'reservation', 'host', 'show', node_id, '-c', 'node_name', '-f', 'value']
        device_id, _ = capture_shell(cmd)
        self.device_id = device_id

    def set_gpu_arch(self):
        self.node_info['gpu_arch'] = ''
        if self.node_info['gpu']:
            all_hosts = self.available_hosts()
            model_index = next((i for i, s in enumerate(all_hosts[0]) if 'gpu.gpu_model' in s), -1)
            for host_info in all_hosts:
                if self.node_info['node_type'] in host_info:
                    gpu_arch = host_info.split(',')[model_index]
                    self.node_info['gpu_arch'] = gpu_arch
                    LOGGER.info(f'gpu_arch set to {gpu_arch}')
                    break

    def provision_instance(self):
        """
        Initializes the instance by reserving the hardware and floating IP, selecting a
        compatible image, creating an image on the hardware, and associating the IP with it.
        """

        try:
            self.select_image()
            self.reserve_lease()
            self.reserve_ip()
            self.create_instance()
            self.associate_ip()
            self.set_device_id()
        except ProvisionException as e:
            self.shutdown_instance()
            raise e

    def shutdown_instance(self):
        """Shuts down the instance and deprovisions the hardware and IP leases."""

        self.delete_server()
        self.delete_leases()
