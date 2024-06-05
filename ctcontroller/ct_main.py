from cli import parse_args
from chameleon_controller import ChameleonController
from camera_traps import CameraTrapsManager

def get_provision_id():
    return 'my-app'

def get_job_id():
    return 'my-job'

def start_job(manager: CameraTrapsManager):
    manager.docker_compose_up()

def shutdown_job(manager: CameraTrapsManager):
    manager.docker_compose_down()

def main(args: list):
    parsed_args = parse_args(args)
    print(parsed_args)
    if 'user_name' in parsed_args:
        user_name = parsed_args.user_name
    else:
        user_name = None
    if 'config_file' in parsed_args:
        config_file = parsed_args.config_file
    else:
        config_file = None
    controller = ChameleonController(parsed_args.site[0], get_provision_id(), get_job_id(), config_file, user_name)

    if parsed_args.subcommand == 'register':
        #controller.register_credentials(parsed_args.config_file)
        return

    controller.login()

    if parsed_args.subcommand == 'check':
        controller.run_check(parsed_args.check_type)
        return
    if parsed_args.subcommand == 'provision':
        controller.deploy_instance(parsed_args.nodes, parsed_args.cpu_type, parsed_args.gpu, parsed_args.node_type)
        ctmanager = CameraTrapsManager(controller.runner, '0.3.3')
        start_job(ctmanager)
        #controller.shutdown_instance()
    if parsed_args.subcommand == 'kill':
        shutdown_job(ctmanager)

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])