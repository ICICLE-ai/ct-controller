import os
import pwd
import json
from .error import print_and_exit

class Controller():
    def __init__(self):
        # List of possible environment variables to be used by the controller
        self.vars = {
            'num_nodes':         {'required': True,  'category': ['provisioner'], 'type': str},
            'target_site':       {'required': True,  'category': ['provisioner'], 'type': str},
            'node_type':         {'required': True,  'category': ['provisioner'], 'type': str},
            'gpu':               {'required': True,  'category': ['provisioner',
                                                                  'application'], 'type': bool},
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
        for key, val in self.vars.items():
            var = f'CT_CONTROLLER_{key.upper()}'
            found = False
            if var in os.environ:
                typed_val = self.type_conversion(key, os.environ[var], val['type'])
                found = True
                if 'provisioner' in val['category']:
                    provisioner_config[key] = typed_val
                if 'application' in val['category']:
                    application_config[key] = typed_val
                if 'controller' in val['category']:
                    controller_config[key] = typed_val

            # Check for any required variables that have not been defined
            if val['required'] and not found:
                print_and_exit(f'Required variable CT_CONTROLLER_{key.upper()} \
                               required by ctcontroller not defined in your environment.')

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

    def type_conversion(self, key: str, val: str, target_type):
        if target_type == bool:
            if val.lower() in ['1', 't', 'true', 'yes', 'y']:
                new = True
            elif val.lower() in ['0', 'f', 'false', 'no', 'n']:
                new = False
            else:
                print_and_exit(f'{key}={val} is not valid. {key} must be a boolean.')
        elif target_type == int:
            if val.isdigit():
                new = int(val)
            else:
                print_and_exit(f'{key}={val} is not valid. {key} must be integer.')
        elif target_type == str:
            new = val
        elif target_type == 'json':
            try:
                new = json.loads(val)
            except ValueError:
                print_and_exit(f'Invalid json passed to {key}:\n{val}')
        else:
            print_and_exit(f'Invalid type {target_type} for variable {key}.')
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
            print_and_exit(f'Log directory {log_dir} is not writable.')
