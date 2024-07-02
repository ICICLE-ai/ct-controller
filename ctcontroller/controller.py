import os
import pwd
import json
from .error import print_and_exit

class Controller():
    def __init__(self):
        # List of possible environment variables to be used by the controller
        self.vars = {
            'num_nodes':         {'required': True,  'category': ['provisioner'], 'type': str},
            'site':              {'required': True,  'category': ['provisioner'], 'type': str},
            'node_type':         {'required': True,  'category': ['provisioner'], 'type': str},
            'gpu':               {'required': True,  'category': ['provisioner', 'application'], 'type': bool},
            'model':             {'required': False, 'category': ['application'], 'type': str},
            'input':             {'required': False, 'category': ['application'], 'type': str},
            'ssh_key':           {'required': False, 'category': ['provisioner'], 'type': str},
            'key_name':          {'required': False, 'category': ['provisioner'], 'type': str},
            'ct_version':        {'required': False, 'category': ['application'], 'type': str},
            'target_user':       {'required': False, 'category': ['provisioner'], 'type': str},
            'output_dir':        {'required': False, 'category': ['controller'],  'type': str},
            'job_id':            {'required': False, 'category': ['provisioner'], 'type': str},
            'advanced_app_vars': {'required': False, 'category': ['application'], 'type': 'json'},
            'config_path':       {'required': True,  'category': ['provisioner'], 'type': str}
        }

        provisioner_config = {}
        application_config = {}
        controller_config = {}

        # iterate over variables and copy values into config dictionaries
        for k, v in self.vars.items():
            var = f'CT_CONTROLLER_{k.upper()}'
            found = False
            if var in os.environ:
                val = self.type_conversion(k, os.environ[var], v['type'])
                found = True
                if 'provisioner' in v['category']:
                    provisioner_config[k] = val
                if 'application' in v['category']:
                    application_config[k] = val
                if 'controller' in v['category']:
                    controller_config[k] = val

            # Check for any required variables that have not been defined
            if v['required'] == True and found == False:
                print_and_exit(f'Required variable CT_CONTROLLER_{k.upper()} required by ctcontroller not defined in your environment.')

        # Get the requester's username
        if '_tapisJobOwner' in os.environ:
            self.tapis = True
            provisioner_config['requesting_user'] = os.environ['_tapisJobOwner']
        else:
            self.tapis = False
            provisioner_config['requesting_user'] = pwd.getpwuid(os.getuid())[0]

        self.provisioner_config = provisioner_config
        self.application_config = application_config
        self.controller_config  = controller_config

        self.set_log_dir()

    def type_conversion(self, key: str, val: str, type):
        if type == bool:
            if val.lower() in ['1', 't', 'true', 'yes', 'y']:
                new = True
            elif val.lower() in ['0', 'f', 'false', 'no', 'n']:
                new = False
            else:
                raise print_and_exit(f'{key}={val} is not valid. {key} must be a boolean.')
        elif type == int:
            if val.isdigit():
                new = int(val)
            else:
                raise print_and_exit(f'{key}={val} is not valid. {key} must be integer.')
        elif type == str:
            new = val
        elif type == 'json':
            try:
                new = json.loads(val)
            except ValueError:
                print_and_exit(f'Invalid json passed to {key}:\n{val}')
        else:
            raise Exception(f'Invalid type {type} for variable {key}.')
        return new

    # Determine the log directory and check that it is writable
    def set_log_dir(self):
        if 'root' in self.controller_config:
            log_dir = self.controller_config['output_dir']
        else:
            log_dir = './output'
        if os.access(log_dir, os.W_OK):
            self.log_directory = log_dir
        else:
            print_and_exit(f'Log directory {self.log_dir} is not writable.')