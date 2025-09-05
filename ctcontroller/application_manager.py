"""
Contains the ApplicationManager class is a base class that defines basic functionality for
managing an application on a remote server.
"""

from .remote import RemoteRunner
from .local import LocalRunner
from .util import Status

class ApplicationManager():
    """
    A base class to manage the running of an application on a remote server.
    """

    def __init__(self, runner: RemoteRunner | LocalRunner, log_dir: str, cfg):
        self.runner = runner
        self.log_dir = log_dir
        self.advanced = cfg.get('advanced_app_vars')
        self.experiment_id = cfg.get('job_id')
        self.user_id = cfg.get('requesting_user')
        self.status = Status.PENDING

    def run_job(self):
        """Placeholder function to handle running an application."""

        pass

    def shutdown_job(self):
        """Placeholder function to handle shutting down an application."""

        pass
