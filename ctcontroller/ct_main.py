"""
The main module of the ctcontroller package.
It contains the main function that runs the entire provision-run-shutdown-deprovision workflow.
"""
import logging
from .controller import Controller
from .util import ApplicationException, ProvisionException

LOGGER = logging.getLogger("CT Controller")


def get_app_manager_class(app_type: str):
    if app_type == "camera_traps":
        from .camera_traps import CameraTrapsManager
        return CameraTrapsManager
    if app_type == "custom_jetson_infer":
        from .custom_jetson_app import CustomJetsonAppManager
        return CustomJetsonAppManager
    raise ApplicationException(f"Unsupported app_type: {app_type}")


def setup(options: dict = None, job_local_log=False):
    controller = Controller(options)

    if controller.provisioner_config['target_site'].startswith('CHI'):
        from .chameleon_provisioner import ChameleonProvisioner as SiteProvisioner
    elif controller.provisioner_config['target_site'] == 'TACC':
        from .tacc_provisioner import TACCProvisioner as SiteProvisioner
    elif controller.provisioner_config['target_site'] == 'local':
        from .local_provisioner import LocalProvisioner as SiteProvisioner
    elif controller.provisioner_config['target_site'] == 'jetson':
        from .jetson_provisioner import JetsonProvisioner as SiteProvisioner
    else:
        raise ProvisionException(f"Unsupported target_site: {controller.provisioner_config['target_site']}")

    try:
        provisioner = SiteProvisioner(controller.provisioner_config)
        provisioner.provision_instance()
    except ProvisionException as e:
        LOGGER.exception(e.msg)
        raise

    try:
        if job_local_log:
            app_log_dir = f'{controller.log_directory}/{controller.application_config["job_id"]}'
        else:
            app_log_dir = controller.log_directory

        LOGGER.info("controller.application_config = %s", controller.application_config)
        LOGGER.info("controller.provisioner_config = %s", controller.provisioner_config)

        app_type = controller.application_config.get("app_type", "camera_traps")
        AppManager = get_app_manager_class(app_type)

        ctmanager = AppManager(
            provisioner.get_remote_runner(),
            log_dir=app_log_dir,
            cfg=controller.application_config,
            allow_attaching=provisioner.allow_attaching
        )
    except ApplicationException as e:
        LOGGER.exception(e.msg)
        provisioner.shutdown_instance()
        raise

    return controller, provisioner, ctmanager


def run(provisioner, ctmanager):
    try:
        ctmanager.run_job()
    except ApplicationException as e:
        LOGGER.exception(e.msg)
        ctmanager.shutdown_job()
        provisioner.shutdown_instance()
        raise


def shutdown(provisioner, ctmanager):
    try:
        ctmanager.shutdown_job()
    except ApplicationException:
        provisioner.shutdown_instance()
        raise
    else:
        provisioner.shutdown_instance()


def main():
    controller, provisioner, ctmanager = setup()
    run(provisioner, ctmanager)
    shutdown(provisioner, ctmanager)