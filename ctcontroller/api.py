import json
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, create_model, field_validator, model_validator
from datetime import datetime, timedelta
from typing import Dict, Optional
from os import environ
from .local import LocalRunner
from .util import ApplicationException, ProvisionException, Status
from .ct_main import setup, shutdown

LOGGER = logging.getLogger("CT Controller")

app = FastAPI()

localrunner = LocalRunner()

class ControllerOptions(BaseModel):
    node_type: Optional[str] = localrunner.cpu_arch
    gpu: Optional[bool] = False
    ssh_key: Optional[str] = None
    key_name: Optional[str] = None
    target_user: Optional[str] = None
    job_id: Optional[str] = None

class AppOptions(BaseModel):
    model: Optional[str] = None
    input_set: Optional[str] = None
    input_dataset_type: Optional[str] = None
    ct_version: Optional[str] = 'latest'
    advanced_app_vars: Optional[Dict[str, str]] = None

    @model_validator(mode='before')
    @classmethod
    def extract_advanced_options(cls, values):
        declared_fields = set(cls.__fields__.keys())
        advanced = {key: val for key, val in values.items() if key not in declared_fields}
        for key in advanced:
            values.pop(key)
        values['advanced_app_vars'] = advanced
        return values


class CTControllerState:
    def __init__(self):
        self.controller = None
        self.provisioner = None
        self.appmanager = None

    def get_status(self):
        if self.controller == None:
            return {'hardware': Status.PENDING.name, 'app': Status.PENDING.name}
        return {'hardware': self.provisioner.get_status().name, 'app': self.appmanager.get_status().name}

state = CTControllerState()

async def stream_app_files(fnames):
    pos = [0] * len(fnames)
    done = [False] * len(fnames)
    
    while not all(done):
        for i, fname in enumerate(fnames):
            if done[i]:
                continue
            with open(filename, "rb") as f:
                f.seek(pos[i])
                chunk = f.read(1024)
                if chunk:
                    yield chunk
                    pos[i] += len(chunk)
                await asyncio.sleep(loop_interval)

                last_check += loop_interval
                if last_check >= poll_interval:
                    last_check = 0.0
                    if state.appmanager.status != Status.RUNNING:
                        break


@app.post('/run', summary='Run the application')
async def run_api():
    """
    After the application has been configured, this endpoint launches the application.
    """
    if state.get_status()['hardware'] != Status.READY.name:
        return {'message': 'ctcontroller has not been started up properly'}
    elif state.get_status() == {'hardware': Status.READY.name, 'app': Status.READY.name}:
        asyncio.create_task(run_task())
        return {'message': 'started application'}
    elif state.get_status() == {'hardware': Status.READY.name, 'app': Status.RUNNING.name}:
        return {'message': 'application already running'}
    else:
        return {'message': f'application not ready, currently {state.get_status()["app"]}. Run stop/configure to resolve the issue.'}

async def run_task():
    await asyncio.to_thread(run, state.provisioner, state.appmanager)

def run(provisioner, appmanager):
    try:
        appmanager.setup_environment()
        appmanager.run_app()
    except ApplicationException as e:
        LOGGER.exception(e.msg)
        appmanager.shutdown_job()
        provisioner.shutdown_instance()
        raise
   
# Provisions the hardware and prepares the app for deployment
@app.post('/startup', summary='Starts up ctcontroller')
def startup(options: ControllerOptions=ControllerOptions()):
    """
    Starts up the ctcontroller.
    Provisions the hardware and cleans up any previous jobs, preparing the run directory for a new job.
    """
    state.controller, state.provisioner, state.appmanager = setup_api(options.model_dump())
    return {'message': 'ctcontroller is ready'}

def setup_api(options: dict=None):
    controller, provisioner, appmanager = setup(options=options, job_local_log=True)
    try:
        #appmanager.setup_app()
        appmanager.cleanup_environment()
    except ApplicationException as e:
        LOGGER.exception(e.msg)
        appmanager.shutdown_job()
        provisioner.shutdown_instance()
        raise
    return controller, provisioner, appmanager


@app.post('/stop', summary='Stops the app.')
def stop():
    """
    Shuts down the app and copies over any logs to the log directory
    """
    msg = ''
    try:
        state.appmanager.stop_app()
    except ApplicationException as e:
        msg = f'Error while stopping app: {e}. '
    else:
        msg += 'stopped app. '
    try:
        state.appmanager.copy_results()
    except ApplicationException as e:
        msg += f'Error while copying results: {e}. '
    else:
        msg += 'copied logs. '

    return {'message': msg}

@app.post('/configure', summary='Configures the app')
def configure(options: AppOptions=AppOptions()):
    """
    Uses the submitted configurations to generate a config yaml and generate
    the run directory.
    """
    if state.controller is None:
        return {'message': 'ctcontroller needs to be started first'}
    state.controller.update_application_config(options.model_dump())
    if state.appmanager.update_config(state.controller.application_config):
        state.appmanager.configure_app()
        return {'message': 'app configured'}
    else:
        return {'message': 'app configuration did not change'}

@app.get('/health', summary='Gets the status.')
def health():
    """
    Gets the status of the hardware and app.
    """
    return {'status': state.get_status()}

@app.get('/dl_config', summary='Get config.yaml')
def config():
    """
    Downloads the latest configuration file used to build the run directory
    """
    return FileResponse(path=f'{state.appmanager.log_dir}/ct_controller.yml', media_type='application/x-yaml', filename='config.yaml')

@app.get('/controller_logs/download', summary='Get controller logs')
def dl_controller_logs():
    """
    Downloads the logs of the controller.
    Note: This does not include application logs.
    """
    return FileResponse(path=f'{state.controller.log_directory}/run.log', media_type='text/plain', filename='controller.log')

@app.get('/app_logs/download/stdout', summary='Get application stdout')
def dl_app_out_logs():
    """
    Downloads the application logs.
    """
    return FileResponse(path=f'{state.appmanager.log_dir}/ct_out.log', media_type='text/plain', filename='ct_out.log')

@app.get('/app_logs/download/stderr', summary='Get application stderr')
def dl_app_err_logs():
    """
    Downloads the application logs.
    """
    return FileResponse(path=f'{state.appmanager.log_dir}/ct_err.log', media_type='text/plain', filename='ct_err.log')

@app.get('/app_logs/stream', summary='Stream application output')
def stream_app_out():
    """
    Streams application output as a StreamingResponse
    """
    return StreamingResponse(stream_app_files([f'{state.appmanager.log_dir}/ct_out.log', f'{state.appmanager.log_dir}/ct_err.log']), media_type="text/plain")

@app.post('/shutdown', summary='Shuts down controller')
def shutdown_endpoint():
    """
    Performs a full shut down the application.
    This includes:
      - stopping the application
      - copying output directory to log directory,
      - deleting run directory
      - deprovisioning hardware
    """
    global state
    hardware_status = state.get_status()['hardware']
    if hardware_status == Status.READY.name:
        msg = stop()
        state.appmanager.remove_app()
        state.provisioner.shutdown_instance()
        state.provisioner = None
        state.appmanager = None
        state.controller = None
        msg['message'] += 'shutdown complete'
        return msg
    elif hardware_status == Status.PENDING.name:
        return {'message': 'hardware and app not yet started'}
    else:
        return {'message': 'already shutdown'}

