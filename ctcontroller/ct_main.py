from cli import parse_args

#def start_job(manager):
#    manager.run_job()
#
#def shutdown_job(manager, job_id):
#    manager.docker_compose_down()

def main(args: list):
    parsed_args = parse_args(args)
    print(parsed_args)
    if parsed_args.site == 'Chameleon':
        from chameleon_controller import ChameleonController as SiteController
    elif parsed_args.site == 'TACC':
        from tacc_controller import TACCController as SiteController
    from camera_traps import CameraTrapsManager as AppManager

    # If registering, initialize controller and return
    if parsed_args.subcommand == 'register':
        controller = SiteController(parsed_args.site, 'register', config_file=parsed_args.config_file, user_name=parsed_args.user_name, private_key=parsed_args.private_key, key_name=parsed_args.key_name)
        return

    if 'job_id' in parsed_args:
        job_id = parsed_args.job_id
    else:
        job_id = None
    if 'provision_id' in parsed_args:
        provision_id = parsed_args.provision_id
    else:
        provision_id = None
    controller = SiteController(parsed_args.site, parsed_args.subcommand, provision_id=provision_id, user_name=parsed_args.user_name)

    #print('logging in...')
    #controller.login()

    if parsed_args.subcommand == 'check':
        controller.run_check(parsed_args.check_type)
    elif parsed_args.subcommand == 'provision':
        controller.provision_instance(parsed_args.nodes, parsed_args.cpu_type, parsed_args.gpu, parsed_args.node_type)
    elif parsed_args.subcommand == 'run':
        if parsed_args.provision_id is None:
            controller.provision_instance(parsed_args.nodes, parsed_args.cpu_type, parsed_args.gpu, parsed_args.node_type)
        ctmanager = AppManager(controller.get_remote_runner(), parsed_args.ct_version, provision_id=provision_id, top_log_dir=controller.provision_dir, branch=parsed_args.branch)
        job_id = ctmanager.run_job()
    elif parsed_args.subcommand == 'kill':
        ctmanager = AppManager(controller.get_remote_runner(), None, provision_id=provision_id, top_log_dir=controller.provision_dir, job_id=job_id)
        ctmanager.shutdown_job()
        if parsed_args.provision_id:
            controller.shutdown_instance()

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])