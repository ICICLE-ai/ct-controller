"""
Contains the RemoteRunner class which manages the connection between the local machine and
a provisioned remote server where the application will be run.
"""
import io
import os
import time
import stat
import logging
from pathlib import Path
from threading import Thread
from typing import TextIO
import paramiko

LOGGER = logging.getLogger("CT Controller")

AuthenticationException = paramiko.ssh_exception.AuthenticationException

class RemoteRunner():
    """
    A class to manage the connection between the local machine and a provisioned remote server.

    Attributes:
        client: the ssh client client connected to the remote server
        sftp: the sftp connection to the remote server
        ip_address: the ip address of the remote server
        home_dir: the path to the home directory on the remote server
        device_id: a unique device_id for the remote server

    Methods:
        run(cmd):
            Runs a command on the remote server.
        log_to_file(file, stream): 
            Writes the stream to a file on the local machine.
        tracked_run(cmd, outlog, errlog): 
            Runs a command on the remote node and logs the stdout/stderr to files on
            the local machine in the background.
        create_file(fpath):
            Creates an empty file on the remote server at the specified path.
        delete_file(fpath):
            Deletes the file on the remote server at the specified path.
        file_exists(fpath):
            Returns True if the file exists on the remote server at the specified path
            and False if it does not.
        copy_dir(src, target):
            Recusively copies the directory src directory on the local machine to the
            target path on the remote server.
        copy_file(src, target):
            Copies the file located at src on the local machine to the target path on the
            remote server.
        mkdir(pth):
            Creates a directory at the specified path on the remote server.
    """

    def __init__(self, ip_address: str, username: str, pkey_path: str, port=22, device_id=None, num_retries=30, jump_host=None, jump_user=None, jump_pkey_path=None, jump_port=22, httpproxy=None):
        self.client = None
        self.sftp = None
        self.httpproxy=httpproxy
        if jump_host:
            PKey = self.get_key_class(path=pkey_path)
            jump_pkey = PKey.from_private_key_file(pkey_path)
            jump_client = paramiko.SSHClient()
            jump_policy = paramiko.AutoAddPolicy()
            jump_client.set_missing_host_key_policy(jump_policy)
            jump_client.connect(jump_host, username=jump_user, pkey=jump_pkey)
            transport = jump_client.get_transport()
            dest_addr = (ip_address, port)
            local_addr = (jump_host, jump_port)
            channel = transport.open_channel("direct-tcpip", dest_addr, local_addr)
            if not os.path.exists(jump_pkey_path):
                sftp_client = jump_client.open_sftp()
                with sftp_client.open(jump_pkey_path, 'r') as remote_key:
                    key = remote_key.read().decode('utf-8')
                    PKey = self.get_key_class(pkey=key)
                    pkey = PKey.from_private_key(io.StringIO(key))
                sftp_client.close()
            else:
                PKey = self.get_key_class(path=jump_pkey_path)
                pkey = PKey.from_private_key_file(jump_pkey_path)
        else:
            channel = None
            PKey = self.get_key_class(path=pkey_path)
            pkey = PKey.from_private_key_file(pkey_path)
        client = paramiko.SSHClient()
        policy = paramiko.AutoAddPolicy()
        client.set_missing_host_key_policy(policy)

        for _itr in range(num_retries):
            try:
                client.connect(ip_address, username=username, pkey=pkey, sock=channel)
                break
            except OSError:
                LOGGER.warning(f'os error while trying to connect to {ip_address}')
                time.sleep(10)
        self.ip_address = ip_address
        self.client = client
        self.sftp = self.client.open_sftp()

        _, pwdout, _ = self.client.exec_command('pwd -P')
        self.home_dir = pwdout.readlines()[0].strip()
        if device_id:
            self.device_id = device_id
        else:
            self.device_id = self.run('hostname')

    def __del__(self):
        if self.sftp:
            self.sftp.close()
        if self.client:
            self.client.close()

    def run(self, cmd: str) -> str:
        """
        Run a command on the remote server

            Parameters:
                cmd (str): the comand to be run
            
            Returns:
                str: the stdout from the execution of the command
        """

        LOGGER.info(f'Running "{cmd}" on remote server "{self.ip_address}"')
        _stdin, stdout, _stderr = self.client.exec_command(cmd, get_pty=True)
        return stdout.read().decode('utf-8').strip()

    def log_to_file(self, file: TextIO, stream):
        """
            Log each line of a stream to a local file

            Parameters:
                file (TextIO): the file pointer to a local file
                stream: the stream that is being logged
        """

        for line in iter(stream.readline, ''):
            file.write(line)

    def tracked_run(self, cmd: str, outlog: str, errlog: str):
        """
        Runs a command on the remote server, logging the stdout and stderr to local files
        in background threads.
        The main thread parses the outputs to determine when the application has completed.

            Parameters:
                cmd (str): the command to run on the remote server
                outlog (str): local path the stdout log file
                errlog (str): local path to the stderr log file
        """

        LOGGER.info((f'Running "{cmd}" on remote server "{self.ip_address}".\n'
              f'Logging stdout=>{outlog} and stderr=>{errlog}'))
        _, stdout, stderr = self.client.exec_command(cmd, get_pty=True)
        outf = open(outlog, 'a+', encoding='utf-8')
        errf = open(errlog, 'a+', encoding='utf-8')
        out_thread = Thread(target=self.log_to_file, args=(outf, stdout))
        err_thread = Thread(target=self.log_to_file, args=(errf, stderr))

        out_thread.start()
        err_thread.start()

        out_thread.join()
        err_thread.join()

        outf.close()
        errf.close()

    def create_file(self, fpath: str):
        """
        Creates an empty file on the remote server

            Parameters:
                fpath (str): path on the remote server
        """

        fil = self.sftp.open(fpath, 'w')
        fil.close()

    def delete_file(self, fpath: str):
        """
        Deletes a file on the remote server

            Parameters:
                fpath (str): path on the remote server
        """

        self.sftp.remove(fpath)

    def file_exists(self, fpath: str) -> bool:
        """
        Checks if a file exists on the remote server

            Parameters:
                fpath (str): path on the remote server
            
            Returns:
                True if file exists
                False if file does not exist
        """

        try:
            self.sftp.stat(fpath)
            exists = True
        except IOError:
            exists = False
        return exists

    def copy_dir(self, src: str, target: str):
        """
        Recursively copies a directory from the local machine to the remote server.

            Parameters:
                src (str): path to source directory on local machine
                target (str): path to target directory on remote server
        """

        LOGGER.info(f'Copying from {src} on local system to {target} on remote')

        for path, _, files in os.walk(src):
            try:
                self.sftp.mkdir(os.path.join(target,path))
            except IOError:
                pass
            for file in files:
                self.sftp.put(os.path.join(path,file),os.path.join(target,path,file))
        return os.path.join(target, os.path.basename(src))

    def copy_file(self, src: str, target: str):
        """
        Copies a file from the local machine to the remote server.

            Parameters:
                src (str): path to source file on local machine
                target (str): path to target file on remote server
        """

        self.sftp.put(src, target)

    def get(self, src: str, target: str) -> None:
        """
        Copies a remote file or directory from the remote server to the local machine.

            Parameters:
                src (str): path to the source file/directory on the remote server
                target (str): path to the target file/directory on the local server
        """

        # check if src is a file or directory
        targpath = f'{target}/{os.path.basename(src)}'
        st = self.sftp.stat(src)

        if stat.S_ISDIR(st.st_mode):
            Path(targpath).mkdir(parents=True, exist_ok=True)
            for fil in self.sftp.listdir(src):
                self.get(f'{src}/{fil}', targpath)
        else: # src is a file
           self.sftp.get(src, targpath)

    def mkdir(self, pth: str):
        """
        Creates an empty directory on the remote server
        
            Parameters:
                pth (str): remote path where directory should be created
        """

        self.sftp.mkdir(pth)

    def get_key_class(self, path: str=None, pkey: str=None):
        if path:
            with open(path, 'r') as f:
                header = f.readline()
        elif pkey:
            header = pkey.split('\n')[0]
        else:
            return paramiko.PKey

        if 'BEGIN RSA PRIVATE KEY' in header:
            return paramiko.RSAKey
        elif 'BEGIN OPENSSH PRIVATE KEY' in header:
            return paramiko.Ed25519Key
        elif 'BEGIN EC PRIVATE KEY' in header:
            return paramiko.ECDSAKey
        elif 'BEGIN DSA PRIVATE KEY' in header:
            return paramiko.DSSKey
        else:
            return paramiko.PKey
