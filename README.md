# ctcontroller

The `ctcontroller` tool can be used to manage the provisioning and releasing of edge hardware as well as running and shutting down the camera-traps application.

## Installation

### From source

Clone the repo and ensure that you run from the root of the ctcontroller repository.
```
git clone https://github.com/ICICLE-ai/ctcontroller.git
cd ctcontroller
```

### Pip

`ctcontroller` can also be installed via pip with:

```
pip install https://github.com/ICICLE-ai/ct-controller@v${VER}
```


### Docker image

`ctcontroller` is also available [here](https://hub.docker.com/r/tapis/ctcontroller) as a docker image on Dockerhub. To pull down the latest version:

```
docker pull tapis/ctcontroller
```

## Running

### Source/pip

If installation is via pip or source, export the variables described [below](#control_variables) to your path. For instance, to run on a non-GPU x86 node at TACC you might export:
```
export CT_CONTROLLER_TARGET_SITE=TACC
export CT_CONTROLLER_NODE_TYPE=x86
export CT_CONTROLLER_GPU=0
export CT_CONTROLLER_CONFIG_PATH=./config.yml
```

Then, import and run the `ctcontroller` package:

```
cd ctcontroller
python -c "import ctcontroller; ctcontroller.run()"
```

### Docker image

If using the docker image, the environment variables should be passed via the command-line to the docker image. Also note that any external files will need to be mounted and paths. In particular, if you would like to save any of the output files make sure that the output directory is set to a path that will be available after the container shuts down. For instance, the same non-GPU x86 node at TACC might be run with:

```
docker run \ 
--mount type=bind,source="$HOME/.ssh",target=/ssh_keys \
--mount type=bind,source="./output",target=/output \
--mount type=bind,source="./config.yml",target=/config.yml \
-e CT_CONTROLLER_TARGET_SITE=TACC \
-e CT_CONTROLLER_NODE_TYPE=x86 \
-e CT_CONTROLLER_GPU=0 \
-e CT_CONTROLLER_CONFIG_PATH=./config.yml \
-e CT_CONTROLLER_OUTPUT_DIR=/output \
tapis/ctcontroller
```

## Architecture Overview

`ctcontroller` is made up of two main subcomponents:

1. The Provisioner:
	1. TACC provisioner
	2. Chameleon provisioner
2. The Application Manager:
	1. Camera Traps controller

The provisioner handles the provisioning and deprovisioning of hardware and currently supports two sites: Chameleon Cloud and bare metal nodes at TACC. It can be extended to other sites by defining a new subclass of `Provisioner`.

The Application Controller handles the setup, running, shutting down, and cleaning up of the application that was provisioned by the `Provisioner`. It currently only supports the Camera Traps application but can be extended to other applications by defining a new class.


## Control Variables
`ctcontroller` accepts the following environment variables to be defined at runtime:

| Variable | Description | Required |
| ---------| ----------- | -------- |
| `CT_CONTROLLER_NUM_NODES` | number of nodes that will be provisioned | Yes |
| `CT_CONTROLLER_TARGET_SITE` | site where the nodes will be provisioned | Yes |
| `CT_CONTROLLER_NODE_TYPE` | identifier of the type of node that will be provisioned | Yes |
| `CT_CONTROLLER_GPU` | boolean which tells the provisioner if the node needs to have a GPU and the Application Controller needs to run the application on the GPU | Yes |
| `CT_CONTROLLER_CONFIG_PATH` | path to a config file | Yes |
| `CT_CONTROLLER_MODEL` | model used by the application | No |
| `CT_CONTROLLER_INPUT` | input images into the application | No |
| `CT_CONTROLLER_SSH_KEY` | path to the ssh key | No |
| `CT_CONTROLLER_KEY_NAME` | name of the ssh key (needed for OpenStack/Chameleon) | No |
| `CT_CONTROLLER_CT_VERSION` | version of the application to be run | No |
| `CT_CONTROLLER_TARGET_USER` | username to be used on target system | No |
| `CT_CONTROLLER_OUTPUT_DIR` | path to output directory | No |
| `CT_CONTROLLER_JOB_ID` | unique job ID to be used for provisioning hardware | No |
| `CT_CONTROLLER_ADVANCED_APP_VARS` | variables to be passed to application controller | No |

## Configuration File

The path to the configuration file is specified through the environment variable `CT_CONTROLLER_CONFIG_PATH`. `ctcontroller` expects this file to be a YAML file. [sample_config.yml](sample_config.yml) is a sample config file. Configuration files can be used to specify target host nodes to be provisioned, service account credentials, and authorized users.
