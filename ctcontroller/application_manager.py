"""
Contains the ApplicationManager class is a base class that defines basic functionality for
managing an application on a remote server.
"""

from .remote import RemoteRunner
from .local import LocalRunner
from .util import Status
from os import makedirs

class ApplicationManager():
    """
    A base class to manage the running of an application on a remote server.
    """

    def __init__(self, runner: RemoteRunner | LocalRunner, log_dir: str, cfg, allow_attaching: bool):
        makedirs(log_dir, exist_ok=True)
        self.runner = runner
        self.log_dir = log_dir
        self.allow_attaching = allow_attaching
        self.update_config(cfg)
        self.status = Status.PENDING

    def update_config(self, cfg):
        changed = False

        new_advanced = cfg.get('advanced_app_vars')
        if not hasattr(self, 'advanced') or new_advanced != self.advanced:
            self.advanced = new_advanced
            changed = True

        new_experiment_id = cfg.get('job_id')
        if not hasattr(self, 'experiment_id') or new_experiment_id != self.experiment_id:
            self.experiment_id = new_experiment_id
            changed = True

        new_user_id = cfg.get('requesting_user')
        if not hasattr(self, 'user_id') or new_user_id != self.user_id:
            self.user_id = new_user_id
            changed = True
        return changed

    def run_job(self):
        """Placeholder function to handle running an application."""

        pass

    def shutdown_job(self):
        """Placeholder function to handle shutting down an application."""

        pass

    def get_status(self):
        return self.status
