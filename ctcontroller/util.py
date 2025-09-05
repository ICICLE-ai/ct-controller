"""
Contains common helper functions and classes.
"""

import logging
from os import environ
from subprocess import run
from enum import Enum

LOGGER = logging.getLogger("CT Controller")

def setup_logger(log_dir: str):
    """Sets up a logger."""

    log_level = environ.get("CT_CONTROLLER_LOG_LEVEL", "INFO")
    if log_level == "DEBUG":
        LOGGER.setLevel(logging.DEBUG)
    elif log_level == "INFO":
        LOGGER.setLevel(logging.INFO)
    elif log_level == "WARN":
        LOGGER.setLevel(logging.WARN)
    elif log_level == "ERROR":
        LOGGER.setLevel(logging.ERROR)
    if not LOGGER.handlers:

        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]')
        handler = logging.StreamHandler()
        fileHandler = logging.FileHandler(f"{log_dir}/run.log")
        handler.setFormatter(formatter)
        fileHandler.setFormatter(formatter)
        LOGGER.addHandler(handler)
        LOGGER.addHandler(fileHandler)

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
        LOGGER.warning(f'\n\033[93mWARNING: "{cmdstr}" gave error message: "{err}"\033[00m\n')
    return out, err

class ApplicationException(Exception):
    """Exception raised during application setup, run, or cleanup."""

    def __init__(self, msg: str):
        if type(msg) is tuple:
            msg = ''.join(msg)
        self.msg = '\033[91m' + msg + '\033[00m'
        super().__init__(self.msg)

class ControllerException(Exception):
    """Exception raised by controller object."""

    def __init__(self, msg: str):
        if type(msg) is tuple:
            msg = ''.join(msg)
        self.msg = '\033[91m' + msg + '\033[00m'
        super().__init__(self.msg)

class ProvisionException(Exception):
    """Exception raised when provisioner fails to provision hardware."""

    def __init__(self, msg: str):
        if type(msg) is tuple:
            msg = ''.join(msg)
        self.msg = '\033[91m' + msg + '\033[00m'
        super().__init__(self.msg)

class Status(Enum):
    PENDING=1
    SETTINGUP=2
    READY=3
    RUNNING=4
    COMPLETE=5
    SHUTTINGDOWN=6
    SHUTDOWN=7
    FAILED=8
