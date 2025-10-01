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
        self.allow_attaching = True

    # in local/demo environment, do not block on running instance but always continue
    def provision_instance(self):
        self.status = Status.READY

    def shutdown_instance(self):
        self.status = Status.SHUTDOWN
