import json
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, create_model, field_validator
from typing import Dict, Optional
from os import environ
from .local import LocalRunner
from .ct_main import setup, run, shutdown
from .util import ApplicationException, ProvisionException, Status

app = FastAPI()

localrunner = LocalRunner()

class APIOptions(BaseModel):
    num_nodes: Optional[int] = 1
    target_site: Optional[str] = 'local'
    node_type: Optional[str] = localrunner.cpu_arch
    gpu: Optional[bool] = False
    model: Optional[str] = None
    input_set: Optional[str] = None
    ssh_key: Optional[str] = None
    key_name: Optional[str] = None
    ct_version: Optional[str] = 'latest'
    target_user: Optional[str] = None
    output_dir: Optional[str] = None
    job_id: Optional[str] = None
    advanced_app_vars: Optional[Dict[str, str]] = None
    mode: Optional[str] = 'demo'
    input_dataset_type: Optional[str] = None
    config_path: Optional[str] = ''

    @field_validator("advanced_app_vars", mode="before")
    def parse_advanced_app_vars(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

class CTControllerState:
    def __init__(self):
        self.controller = None
        self.provisioner = None
        self.appmanager = None

    def get_status(self):
        if self.controller == None:
            return {'hardware': Status.PENDING.name, 'app': Status.PENDING.name}
        return {'hardware': self.provisioner.status.name, 'app': self.appmanager.status.name}

state = CTControllerState()

@app.post('/start')
async def startup_api(options: APIOptions):
    if state.get_status() == {'hardware': Status.PENDING.name, 'app': Status.PENDING.name}:
        asyncio.create_task(startup_task(options))
        return {'message': 'started application'}
    else:
        return {'message': 'application already running'}

async def startup_task(options: APIOptions):
    for k, v in options:
        if v:
            if type(v) is dict:
                v_str = json.dumps(v)
            else:
                v_str = str(v)
            environ[f'CT_CONTROLLER_{k.upper()}'] = v_str
    state.controller, state.provisioner, state.appmanager = await asyncio.to_thread(setup)
    await asyncio.to_thread(run, state.provisioner, state.appmanager)

@app.get('/health')
def health():
    return {'status': state.get_status()}

@app.post('/shutdown')
def shutdown_endpoint():
    hardware_status = state.get_status()['hardware']
    if hardware_status == Status.RUNNING.name:
        try:
            shutdown(state.provisioner, state.appmanager)
            return {'message': 'shutdown'}
        except ApplicationException as e:
            return {'message': f'application shutdown failed with error {str(e)}'}
        except ProvisionException as e:
            return {'message': f'deprovisioning failed with error {str(e)}'}
    elif hardware_status == Status.PENDING.name:
        return {'message': 'hardware and app not yet started'}
    else:
        return {'message': 'already shutdown'}

