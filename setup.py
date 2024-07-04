from setuptools import setup, find_packages

with open('VERSION.txt', 'r') as f:
    ver=f.read()

ver = ver.strip()

setup(name = 'ctcontroller',
      version = ver,
      packages = find_packages(),
      install_requires = [
          'paramiko>=3.4.0',
          'cryptography>=42.0.4',
          'python-chi==0.17.11',
          'pyyaml',
          'python-blazarclient @ git+https://github.com/ChameleonCloud/python-blazarclient.git@chameleoncloud/xena',
      ],
)
