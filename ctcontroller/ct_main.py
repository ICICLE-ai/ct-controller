from .error import print_and_exit

class Controller():
    def __init__(self):
        import os
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
            'root':              {'required': False, 'category': 'provisioner', 'type': str},
            'provision_id':      {'required': False, 'category': 'provisioner', 'type': int}, # for debugging only
            'job_id':            {'required': False, 'category': 'application', 'type': int}  # for debugging only
        }

        # List of possible environment variables to be used by the controller
        provisioner_config = {}
        application_config = {}
        # iterate over variables and copy values into 
        for k, v in self.vars.items():
            var = f'CT_CONTROLLER_{k.upper()}'
            found = False
            if var in os.environ:
                found = True
                if v['category'] == 'provisioner':
                    provisioner_config[k] = os.environ[var]
                if v['category'] == 'application':
                    application_config[k] = os.environ[var]

            # Check for any required variables that have not been defined
            if v['required'] == True and found == False:
                print_and_exit(f'Required variable CT_CONTROLLER_{k.upper()} required by ctcontroller not defined in your environment.')

        self.provisioner_config = provisioner_config
        self.application_config = application_config

def main():
    controller = Controller()
    if controller.provisioner_config['site'].startswith('CHI'):
        from .chameleon_provisioner import ChameleonProvisioner as SiteProvisioner
    elif controller.provisioner_config['site'] == 'TACC':
        from .tacc_provisioner import TACCProvisioner as SiteProvisioner
    from .camera_traps import CameraTrapsManager as AppManager

    provisioner = SiteProvisioner(controller.provisioner_config)

    provisioner.provision_instance()
    ctmanager = AppManager(provisioner.get_remote_runner(), top_log_dir=provisioner.provision_dir, cfg=controller.application_config)
    ctmanager.run_job()
    ctmanager.shutdown_job()
    provisioner.shutdown_instance()

if __name__ == '__main__':
    main()