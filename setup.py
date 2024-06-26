from setuptools import setup, find_packages

setup(name = 'ctcontroller',
      version = '0.1',
      packages = find_packages(),
      install_requires = [
          'paramiko==3.3.1',
          'cryptography==41.0.3',
      ],
)
