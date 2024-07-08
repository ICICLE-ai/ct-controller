import os
import time
from threading import Thread
import paramiko

AuthenticationException = paramiko.ssh_exception.AuthenticationException

class RemoteRunner():
    def __init__(self, ip_address: str, username: str, pkey_path: str, num_retries=30):
        self.client = None
        self.sftp = None
        pkey = paramiko.RSAKey.from_private_key_file(pkey_path)
        client = paramiko.SSHClient()
        policy = paramiko.AutoAddPolicy()
        client.set_missing_host_key_policy(policy)

        for _itr in range(num_retries):
            try:
                client.connect(ip_address, username=username, pkey=pkey)
                break
            except OSError:
                #print('os error while trying to connect to {ip_address}')
                time.sleep(10)
        self.ip_address = ip_address
        self.client = client
        self.sftp = self.client.open_sftp()
        self.set_home_dir()

    def set_home_dir(self):
        _, stdout, _ = self.client.exec_command('pwd -P')
        self.home_dir = stdout.readlines()[0].strip()

    def run(self, cmd: str) -> str:
        print(f'Running "{cmd}" on remote server "{self.ip_address}"')
        _stdin, stdout, _stderr = self.client.exec_command(cmd, get_pty=True)
        return stdout.read().decode('utf-8').strip()

    def log_to_file(self, file, stream):
        for line in iter(stream.readline, ''):
            file.write(line)

    def tracked_run(self, cmd: str, outlog, errlog):
        print((f'Running "{cmd}" on remote server "{self.ip_address}".\n'
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
        fil = self.sftp.open(fpath, 'w')
        fil.close()

    def delete_file(self, fpath: str):
        self.sftp.remove(fpath)

    def file_exists(self, fpath: str) -> bool:
        try:
            self.sftp.stat(fpath)
            exists = True
        except IOError:
            exists = False
        return exists

    def __del__(self):
        if self.sftp:
            self.sftp.close()
        if self.client:
            self.client.close()

    def copy_dir(self, src, target):
        print(f'Copying from {src} on local system to {target} on remote')

        # Create top-level target directory if it does not exist
        #try:
        #    self.sftp.mkdir(target)
        #except IOError:
        #    pass

        for path, _, files in os.walk(src):
            try:
                self.sftp.mkdir(os.path.join(target,path))
            except IOError:
                pass
            for file in files:
                self.sftp.put(os.path.join(path,file),os.path.join(target,path,file))
        return os.path.join(target, os.path.basename(src))

    def copy_file(self, src: str, target: str):
        self.sftp.put(src, target)

    def mkdir(self, pth: str):
        self.sftp.mkdir(pth)
