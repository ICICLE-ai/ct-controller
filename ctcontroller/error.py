"""
Contains functions to gracefully handle errors.
"""

import sys

def print_and_exit(msg: str):
    """
    Prints the error message and exits the entire application with an exit code of 1

    Parameters:
        msg (str): the message that should be printed before exiting
    """

    print(f'\033[91mERROR: {msg}')
    sys.exit(1)


class ApplicationException(Exception):
    """Exception raised during application setup, run, or cleanup."""

    def __init__(self, msg: str):
        self.msg = '\033[91m' + msg
        super().__init__(self.msg)

class ControllerException(Exception):
    """Exception raised by controller object."""

    def __init__(self, msg: str):
        self.msg = '\033[91m' + msg
        super().__init__(self.msg)

class ProvisionException(Exception):
    """Exception raised when provisioner fails to provision hardware."""

    def __init__(self, msg: str):
        self.msg = '\033[91m' + msg
        super().__init__(self.msg)