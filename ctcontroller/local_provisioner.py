"""Contains the TACCProvisioner for provisioning bare-metal hardware at TACC."""

import os
import time
import logging
from .util import ProvisionException, Status
from .provisioner import Provisioner
from .remote import AuthenticationException

LOGGER = logging.getLogger("CT Controller")

class LocalProvisioner(Provisioner):
    """
    A subclass of the Provisioner class to handle the simple case of running on the hardware that ctcontroller is running on.

    Attributes:
        lock_file (str): name of the lock file used to reserve a node
        available_nodes (dict): a dictionary of nodes accessible at the TACC site
        remote_id (str): username to be used on the remote server

    Methods:

        provision_instance():
            Not appicable for localhost
        shutdown_instance():
            Not applicable for localhost
    """
    def __init__(self, cfg):
        self.site = cfg['target_site']
        self.user = cfg['requesting_user']
        self.ip_addresses = 'localhost'
        self.lock_file = os.path.expanduser('~/ctcontroller.lock')

    def provision_instance(self):
        self.status = Status.SETTINGUP
        if os.path.exists(self.lock_file):
            self.status = Status.FAILED
            raise ProvisionException('Localhost already provisioned')
        else:
            with open(self.lock_file, 'w') as f:
                pass
        self.status = Status.READY

    def shutdown_instance(self):
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)
        else:
            LOGGER.WARNING('Cannot deprovision localhost, it was never provisioned')
        self.status = Status.SHUTDOWN
