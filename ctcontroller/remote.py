import paramiko

class RemoteRunner():
    def __init__(self, ip_address, username, pkey_path):
        pkey = paramiko.RSAKey.from_private_key_file(pkey_path)
        client = paramiko.SSHClient()
        policy = paramiko.AutoAddPolicy()
        client.set_missing_host_key_policy(policy)
    
        print("Connecting to server")
        client.connect(ip_address, username=username, pkey=pkey)
        self.client = client

    def run(self, cmd: str) -> str:
        stdin, stdout, stderr = self.client.exec_command(cmd)
        return stdout.read().decode('utf-8').strip()