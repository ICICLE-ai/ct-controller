import os
from .error import print_and_exit

class Controller():
    def __init__(self):
        # List of possible environment variables to be used by the controller
        self.vars = {
            'num_nodes':         {'required': True,  'category': 'provisioner', 'type': str},
            'site':              {'required': True,  'category': 'provisioner', 'type': str},
            'node_type':         {'required': True,  'category': 'provisioner', 'type': str},
            'gpu':               {'required': True,  'category': 'provisioner', 'type': bool},
            'model':             {'required': True,  'category': 'application', 'type': str},
            'input':             {'required': True,  'category': 'application', 'type': str},
            'ssh_key':           {'required': True,  'category': 'provisioner', 'type': str},
            'key_name':          {'required': False, 'category': 'provisioner', 'type': str},
            'ct_version':        {'required': True,  'category': 'application', 'type': str},
            'user_name':         {'required': True,  'category': 'provisioner', 'type': str},
            'output':            {'required': False, 'category': 'controller',  'type': str},
            'job_id':            {'required': False, 'category': 'application', 'type': str}
        }

        provisioner_config = {}
        application_config = {}
        controller_config = {}

        # iterate over variables and copy values into config dictionaries
        for k, v in self.vars.items():
            var = f'CT_CONTROLLER_{k.upper()}'
            found = False
            if var in os.environ:
                val = self.type_conversion(k, os.environ['var'])
                found = True
                if v['category'] == 'provisioner':
                    provisioner_config[k] = val
                if v['category'] == 'application':
                    application_config[k] = val
                if v['category'] == 'controller':
                    controller_config[k] = val

            # Check for any required variables that have not been defined
            if v['required'] == True and found == False:
                print_and_exit(f'Required variable CT_CONTROLLER_{k.upper()} required by ctcontroller not defined in your environment.')

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
        if type == int:
            if val.isdigit():
                new = int(val)
            else:
                raise print_and_exit(f'{key}={val} is not valid. {key} must be integer.')
        elif type == str:
            new = val
        else:
            raise Exception(f'Invalid type for variable {key}.')
        return new

    # Determine the log directory and check that it is writable
    def set_log_dir(self):
        if 'root' in self.controller_config:
            log_dir = self.controller_config['output']
        else:
            log_dir = './output'
        if os.access(log_dir, os.W_OK):
            self.log_directory = log_dir
        else:
            print_and_exit(f'Log directory {self.log_dir} is not writable.')