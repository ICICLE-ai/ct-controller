from setuptools import setup, find_packages

with open('VERSION.txt', 'r') as f:
    ver=f.read()

ver = ver.strip()

setup(name = 'ctcontroller',
      version = ver,
      packages = find_packages(),
      install_requires = [
          'paramiko==3.3.1',
          'cryptography==41.0.3',
          'python-openstackclient==6.3.0',
          'pyyaml',
      ],
)
