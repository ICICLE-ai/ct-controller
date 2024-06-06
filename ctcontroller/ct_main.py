from cli import parse_args

def start_job(manager):
    manager.docker_compose_up()

def shutdown_job(manager):
    manager.docker_compose_down()

def main(args: list):
    parsed_args = parse_args(args)
    print(parsed_args)
    if parsed_args.site == 'Chameleon':
        from chameleon_controller import ChameleonController as SiteController
        from camera_traps import CameraTrapsManager as AppManager
    elif parsed_args.site == 'TACC':
        raise Exception('TACC site not yet configured')

    # If registering, initialize controller and return
    if parsed_args.subcommand == 'register':
        controller = SiteController(parsed_args.site, config_file=parsed_args.config_file, user_name=parsed_args.user_name)
        return

    if 'job_id' in parsed_args:
        job_id = parsed_args.job_id
    else:
        job_id = None
    if 'provision_id' in parsed_args:
        provision_id = parsed_args.provision_id
    else:
        provision_id = None
    controller = SiteController(parsed_args.site, provision_id=provision_id, job_id=job_id, user_name=parsed_args.user_name)

    controller.login()

    if parsed_args.subcommand == 'check':
        controller.run_check(parsed_args.check_type)
        return
    if parsed_args.subcommand == 'provision':
        controller.provision_instance(parsed_args.nodes, parsed_args.cpu_type, parsed_args.gpu, parsed_args.node_type)
    if parsed_args.subcommand == 'run':
        if parsed_args.provision_id is None:
            controller.provision_instance(parsed_args.nodes, parsed_args.cpu_type, parsed_args.gpu, parsed_args.node_type)
        ctmanager = AppManager(controller.runner, '0.3.3')
        start_job(ctmanager)
    if parsed_args.subcommand == 'kill':
        shutdown_job(ctmanager)

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])