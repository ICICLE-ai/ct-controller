#from cli import parse_args
from __init__ import print_and_exit

#def start_job(manager):
#    manager.run_job()
#
#def shutdown_job(manager, job_id):
#    manager.docker_compose_down()

def parse_environment_variables():
    import os

    #if 'CT_CONTROLLER_CFG' in os.environ:
    #    os.environ['CT_CONTROLLER_CFG']

    # List of possible environment variables to be used by the controller
    vars = {
            'num_nodes':         {'required': True,  'type': str},
            'site':              {'required': True,  'type': str},
            'node_type':         {'required': True,  'type': str},
            'gpu':               {'required': True,  'type': bool},
            'model':             {'required': True,  'type': str},
            'input':             {'required': True,  'type': str},
            'ssh_key':           {'required': True,  'type': str},
            'key_name':          {'required': False, 'type': str},
            'ct_version':        {'required': True,  'type': str},
            'user_name':         {'required': True,  'type': str},
            'root':              {'required': False, 'type': str},
            'provision_id':      {'required': False, 'type': int},
            'job_id':            {'required': False, 'type': int}
           }
    cfg = {}
    # iterate over variables and copy values into 
    for v in vars.keys():
        var = f'CT_CONTROLLER_{v.upper()}'
        if var in os.environ:
            cfg[v] = os.environ[var]

    # Check for any required variables that have not been defined
    for k, v in vars.items():
        if v['required'] == True and (k not in cfg or cfg[k] == None):
            print_and_exit(f'Required variable CT_CONTROLLER_{k.upper()} required by ctcontroller not defined in your environment.')
    return cfg

def main():
    #parsed_args = parse_args(args)
    #print(parsed_args)
    cfg = parse_environment_variables()
    if cfg['site'].startswith('CHI'):
        from chameleon_provisioner import ChameleonProvisioner as SiteProvisioner
    elif cfg['site'] == 'TACC':
        from tacc_provisioner import TACCProvisioner as SiteProvisioner
    from camera_traps import CameraTrapsManager as AppManager

    # If registering, initialize controller and return
    #if parsed_args.subcommand == 'register':
    #    controller = SiteController(cfg['site'], 'register', cfg['config_file'], user_name=cfg['user_name'], private_key=cfg['private_key'], key_name=cfg['key_name'])
    #    return

    #if 'job_id' in parsed_args:
    #    job_id = parsed_args.job_id
    #else:
    #    job_id = None
    #if 'provision_id' in parsed_args:
    #    provision_id = parsed_args.provision_id
    #else:
    #    provision_id = None
    provisioner = SiteProvisioner(cfg)

    #print('logging in...')
    #controller.login()

    #if parsed_args.subcommand == 'check':
    #    controller.run_check(parsed_args.check_type)
    #elif parsed_args.subcommand == 'provision':
    #provisioner.provision_instance(cfg['num_nodes'], cfg['cpu_arch'], cfg['gpu'])
    provisioner.provision_instance()
    #elif parsed_args.subcommand == 'run':
    #    if parsed_args.provision_id is None:
    #import sys; sys.exit(1)
    ctmanager = AppManager(provisioner.get_remote_runner(), top_log_dir=provisioner.provision_dir, cfg=cfg)
    ctmanager.run_job()
    #ctmanager.shutdown_job()
    #provisioner.shutdown_instance()

if __name__ == '__main__':
    main()