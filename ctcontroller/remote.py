import paramiko

class RemoteRunner():
    def __init__(self, ip_address: str, username: str, pkey_path: str, provision_id: str):
        pkey = paramiko.RSAKey.from_private_key_file(pkey_path)
        client = paramiko.SSHClient()
        policy = paramiko.AutoAddPolicy()
        client.set_missing_host_key_policy(policy)
    
        print(f"Connecting to server: {ip_address}")
        client.connect(ip_address, username=username, pkey=pkey)
        self.ip_address = ip_address
        self.client = client
        self.provision_id = provision_id

    def run(self, cmd: str) -> str:
        print(f'Running {cmd} on remote server {self.ip_address}')
        _stdin, stdout, _stderr = self.client.exec_command(cmd, get_pty=True)
        return stdout.read().decode('utf-8').strip()

    def log_to_file(self, file, stream):
        for line in iter(stream.readline, ''):
            file.write(line)

    def tracked_run(self, cmd: str, outlog, errlog):
        from threading import Thread
        _, stdout, stderr = self.client.exec_command(cmd, get_pty=True)
        outf = open(outlog, 'a+')
        errf = open(outlog, 'a+')
        out_thread = Thread(target=self.log_to_file, args=(outf, stdout))
        err_thread = Thread(target=self.log_to_file, args=(errf, stderr))

        out_thread.start()
        err_thread.start()

        out_thread.join()
        err_thread.join()

        outf.close()
        errf.close()