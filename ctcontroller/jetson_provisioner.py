"""
Provisioner for attaching ct-controller to an existing Jetson device over SSH.
"""

from .util import Status, ProvisionException
from .provisioner import Provisioner


class JetsonProvisioner(Provisioner):
    def __init__(self, cfg):
        super().__init__(cfg)

        if not cfg.get("jetson_ip"):
            raise ProvisionException("jetson_ip is required for JetsonProvisioner")

        self.ip_addresses = cfg["jetson_ip"]
        self.remote_id = cfg.get("target_user") or self.user
        self.allow_attaching = True

    def provision_instance(self):
        self.status = Status.READY

    def shutdown_instance(self):
        self.status = Status.SHUTDOWN