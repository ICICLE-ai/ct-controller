from cli import parse_args
from chameleon_controller import ChameleonController
from camera_traps import CameraTrapsManager

def main(args: list):
    parsed_args = parse_args(args)
    print(parsed_args)
    controller = ChameleonController()

    if parsed_args.subcommand == 'register':
        controller.register_credentials(parsed_args.config_file)

    #print(f'before: {controller.env}')
    controller.login()
    #print(f'after: {controller.env}')

    if parsed_args.subcommand == 'check':
        controller.run_check(parsed_args.check_type)
        pass
    if parsed_args.subcommand == 'provision':
        controller.deploy_instance(parsed_args.nodes, parsed_args.cpu_type, parsed_args.gpu, parsed_args.node_type)
        #controller.poll_instance()
        ctmanager = CameraTrapsManager(controller.runner, '0.3.3')
        ctmanager.docker_compose_up()
        #controller.shutdown_instance()

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])