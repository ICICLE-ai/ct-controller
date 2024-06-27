from .camera_traps import CameraTrapsManager as AppManager
from .controller import Controller

def main():
    controller = Controller()
    if controller.provisioner_config['site'].startswith('CHI'):
        from .chameleon_provisioner import ChameleonProvisioner as SiteProvisioner
    elif controller.provisioner_config['site'] == 'TACC':
        from .tacc_provisioner import TACCProvisioner as SiteProvisioner

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