"""
Contains the controller class definition used to manage the user inputs and provide them
to the provisioner and application manager.
"""
import os
import pwd
import random
import string
import logging
import json
from .util import ControllerException, setup_logger

LOGGER = logging.getLogger("CT Controller")

class Controller():
    """
    A class that takes user inputs to set appropriate configuration parameters to
    provision and run the camera traps application.
    """

    def __init__(self):
        # List of possible environment variables to be used by the controller
        self.vars = {
            'num_nodes':         {'required': True,  'category': ['provisioner'], 'type': str},
            'target_site':       {'required': True,  'category': ['provisioner'], 'type': str},
            'node_type':         {'required': True,  'category': ['provisioner',
                                                                  'application'], 'type': str},
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
                raise ControllerException(f'Required variable CT_CONTROLLER_{key.upper()} \
                               required by ctcontroller not defined in your environment.')


        self.provisioner_config = provisioner_config
        self.application_config = application_config
        self.controller_config  = controller_config

        self.check_tapis()
        self.set_user()
        self.set_job_id()
        self.set_log_dir()
        setup_logger(self.log_directory)

    def type_conversion(self, key: str, val: str, target_type):
        """
        Converts the value of a key obtained from the environment into the appropriate type.
        Some basic error checking is done to ensure that a valid type is passed and the
        input string can be converted to that type.

        Parameters:
            key (str): the key whose value is being converted
            val (str): the value that is being converted
            target_type (type or str): the type that the value is being converted to
        """
        if target_type == bool:
            if val.lower() in ['1', 't', 'true', 'yes', 'y']:
                new = True
            elif val.lower() in ['0', 'f', 'false', 'no', 'n']:
                new = False
            else:
                raise ControllerException(f'{key}={val} is not valid. {key} must be a boolean.')
        elif target_type == int:
            if val.isdigit():
                new = int(val)
            else:
                raise ControllerException(f'{key}={val} is not valid. {key} must be integer.')
        elif target_type == str:
            new = val
        elif target_type == 'json':
            try:
                new = json.loads(val)
            except ValueError:
                raise ControllerException(f'Invalid json passed to {key}:\n{val}')
        else:
            raise ControllerException(f'Invalid type {target_type} for variable {key}.')
        return new

    def check_tapis(self):
        """Checks if this application was launched as a Tapis job and sets the tapis parameter."""

        if '_tapisJobOwner' in os.environ:
            self.tapis = True
        else:
            self.tapis = False

    def set_user(self):
        """
        Set the requesting user as a provisioner and application config parameters.
        If using Tapis, use _tapisJobOwner. Else, use the username running this application.
        """

        if self.tapis:
            requesting_user = os.environ['_tapisJobOwner']
        else:
            requesting_user = pwd.getpwuid(os.getuid())[0]
        self.provisioner_config['requesting_user'] = requesting_user
        self.application_config['requesting_user'] = requesting_user

    def set_job_id(self):
        """
        Sets the job id of this run. If using Tapis, use _tapisJobUUID.
        Else, set to a random string if not provided as an environment variable already.
        """

        if self.tapis:
            self.provisioner_config['job_id'] = os.environ['_tapisJobUUID']
            self.application_config['job_id'] = os.environ['_tapisJobUUID']
        elif 'job_id' not in self.provisioner_config:
            job_id = ''.join(random.choices(string.ascii_letters, k=7))
            self.provisioner_config['job_id'] = job_id
            self.application_config['job_id'] = job_id

    # Determine the log directory and check that it is writable
    def set_log_dir(self):
        """
        If a log directory was provided by the user, use it. Otherwise, use a
        subdirectory called output.
        It checks if the selected log directory is writable by the application
        and exits if it is not.
        """

        if 'output_dir' in self.controller_config:
            log_dir = self.controller_config['output_dir']
        else:
            log_dir = './output'
        if os.access(log_dir, os.W_OK):
            self.log_directory = log_dir
        else:
            raise ControllerException(f'Log directory {log_dir} is not writable.')
