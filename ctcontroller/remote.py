import paramiko

class RemoteRunner():
    def __init__(self, ip_address, username, pkey_path):
        pkey = paramiko.RSAKey.from_private_key_file(pkey_path)
        client = paramiko.SSHClient()
        policy = paramiko.AutoAddPolicy()
        client.set_missing_host_key_policy(policy)
    
        print(f"Connecting to server: {ip_address}")
        client.connect(ip_address, username=username, pkey=pkey)
        self.ip_address = ip_address
        self.client = client

    def run(self, cmd: str) -> str:
        print(f'Running {cmd} on remote server {self.ip_address}')
        _stdin, stdout, _stderr = self.client.exec_command(cmd, get_pty=True)
        return stdout.read().decode('utf-8').strip()