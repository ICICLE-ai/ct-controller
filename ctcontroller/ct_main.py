"""
The main module of the ctcontroller package.
It contains the main function that runs the entire provision-run-shutdown-deprovision workflow.
"""
from .camera_traps import CameraTrapsManager as AppManager
from .controller import Controller

def main():
    """
    Initiates the controller, provisioner, and application manager.
    The controller reads in the options provided by the user as environment variables and passes
    them to the provisioner.
    The provisioner then provisions the nodes according to the user's specifications and returns
    a runner on the provisioned nodes.
    The runner is passed to the app manager, which uses it to setup, run, shutdown, and cleanup
    the application on the provisioned nodes.
    Once the application has completed, the provisioner shuts down the instance and the program
    exits.
    """

    controller = Controller()
    if controller.provisioner_config['target_site'].startswith('CHI'):
        from .chameleon_provisioner import ChameleonProvisioner as SiteProvisioner  # pylint: disable=import-outside-toplevel
    elif controller.provisioner_config['target_site'] == 'TACC':
        from .tacc_provisioner import TACCProvisioner as SiteProvisioner # pylint: disable=import-outside-toplevel

    provisioner = SiteProvisioner(controller.provisioner_config)

    provisioner.provision_instance()
    ctmanager = AppManager(provisioner.get_remote_runner(),
                           log_dir=controller.log_directory,
                           cfg=controller.application_config)
    ctmanager.run_job()
    ctmanager.shutdown_job()
    provisioner.shutdown_instance()

if __name__ == '__main__':
    main()
