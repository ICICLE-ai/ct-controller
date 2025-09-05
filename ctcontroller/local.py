"""
Contains the LocalRunner class, providing analogous functionality to RemoteRunner on the localhost.
"""

import socket
import os
import logging
from shutil import copy, copytree
from subprocess import run as shell_run

LOGGER = logging.getLogger("CT Controller")

class LocalRunner():
    """
    A drop-in replacement for RemoteRunner that runs commands on the localhost

    Attributes:
        ip_address: the ip address
        home_dir: the path to the home directory on the
        device_id: a unique device_id for the localhost

    Methods:
        run(cmd):
            Runs a command.
        tracked_run(cmd, outlog, errlog): 
            Runs a command and logs the stdout/stderr to files
            in the background.
        create_file(fpath):
            Creates an empty file at the specified path.
        delete_file(fpath):
            Deletes the file at the specified path.
        file_exists(fpath):
            Returns True if the file exists at the specified path
            and False if it does not.
        copy_dir(src, target):
            Recusively copies the directory src directory to the
            target path.
        copy_file(src, target):
            Copies the file located from src to target path.
        mkdir(pth):
            Creates a directory at the specified path.
    """

    def __init__(self):
        self.ip_address = self.get_ip_address()
        self.home_dir = os.getenv('HOME')
        self.device_id = self.run('hostname')
        self.cpu_arch = self.get_cpu_arch()
        self.httpproxy=None

    def get_cpu_arch(self) -> str:
        """
        Determine whether runner is running on an ARM-based on x86-based architecture
        """
        machine = self.run('uname -m')
        if any(arch in machine for arch in ['arm', 'aarch']):
            return 'arm'
        else:
            return 'x86'

    def get_ip_address(self):
        # if running inside docker
        try:
            result = shell_run(['ip', 'route'], capture_output=True, text=True, check=True)
            for line in result.stdout.splitlines():
                if 'default via' in line:
                    return line.split()[2]
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            host_ip = s.getsockname()[0]
            s.close()
            return host_ip
        except socket.error:
            raise Exception('Could not determine ip address')


    def run(self, cmd: str) -> str:
        """
        Run a command on the localhost shell

            Parameters: 
                cmd (str): the command to be run

            Returns:
            str: the stdout from the execution of the command
        """

        LOGGER.info(f'Running {cmd}')
        output = shell_run(cmd, capture_output=True, shell=True)
        return output.stdout.decode('utf-8').strip()

    def tracked_run(self, cmd: str, outlog: str, errlog: str):
        """
        Runs a shell command, logging the stdout and stderr to local files
        in background threads.

            Parameters:
                cmd (str): the command to run on the remote server
                outlog (str): local path the stdout log file
                errlog (str): local path to the stderr log file
        """

        LOGGER.info((f'Running "{cmd}".\n'
              f'Logging stdout=>{outlog} and stderr=>{errlog}'))
        with open(outlog, "w") as out, open(errlog, "w") as err:
            shell_run(cmd, stdout=out, stderr=err, shell=True)

    def create_file(self, fpath: str):
        """
        Creates an empty file

            Parameters:
                fpath (str): path to file to be created
        """

        with open(fpath, 'w') as f:
            pass

    def delete_file(self, fpath: str):
        """
        Deletes a file

            Parameters:
                fpath (str): path to file to be deleted
        """

        if file_exists(fpath):
            os.remove(fpath)

    def file_exists(self, fpath: str) -> bool:
        """
        Checks if a file exists

            Parameters:
                fpath (str): path to file to be checked for existence
            
            Returns:
                True if file exists
                False if file does not exist
        """

        return os.path.exists(fpath)


    def copy_file(self, src: str, target: str):
        """
        Copies a file from source to target path.

            Parameters:
                src (str): path to source file on local machine
                target (str): path to target file on remote server
        """

        copy(src, target)

    def get(self, src: str, target: str) -> None:
        """
        Copies a directory from source to target path.

            Parameters:
                src (str): path to source directory
                target (str): path to target directory
        """

        target_path = target + '/' + src.split('/')[-1]
        copytree(src, target_path, dirs_exist_ok=True)

    def mkdir(self, pth: str):
        """
        Creates an empty directory
        
            Parameters:
                pth (str): path where directory should be created
        """
        os.makedirs(pth, exist_ok=True)
