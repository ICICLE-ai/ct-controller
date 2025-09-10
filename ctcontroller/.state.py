import json
from pydantic import BaseModel, create_model, field_validator
from typing import Dict, Optional
from .local import LocalRunner


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
            return 'waiting for startup message'
        return {'provisioner': self.provisioner.status, 'appmanager': self.appmanager.status}
