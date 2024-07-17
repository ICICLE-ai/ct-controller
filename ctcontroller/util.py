"""
Contains common helper functions and classes.
"""

import sys
from subprocess import run

def capture_shell(cmd):
    """
    Runs a shell command and returns the stdout and stderr.
    If the command prints anything to stderr then print it as a warning.

        Parameters:
            cmd (str or list): command to run on the command-line

        Returns:
            stdout: standard output from the command
            stderr: standard error from the command    
    """

    if isinstance(cmd, str):
        cmd = cmd.split(' ')
        cmdstr = cmd
    elif isinstance(cmd, list):
        cmdstr = ' '.join(cmd)
    else:
        raise ControllerException(f'Invalid shell command: {cmd}')
    proc = run(cmd, capture_output=True, check=False)
    out = proc.stdout.decode('utf-8').strip()
    err = proc.stderr.decode('utf-8').strip()
    if err != '':
        print(f'\n\033[93mWARNING: "{cmdstr}" gave error message: "{err}"\033[00m\n')
    return out, err

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
        self.msg = '\033[91m' + msg + '\033[00m'
        super().__init__(self.msg)

class ControllerException(Exception):
    """Exception raised by controller object."""

    def __init__(self, msg: str):
        self.msg = '\033[91m' + msg + '\033[00m'
        super().__init__(self.msg)

class ProvisionException(Exception):
    """Exception raised when provisioner fails to provision hardware."""

    def __init__(self, msg: str):
        self.msg = '\033[91m' + msg + '\033[00m'
        super().__init__(self.msg)