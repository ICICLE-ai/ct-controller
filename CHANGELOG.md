# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Removed

## [0.2] 2025-04-29

### Added
- This changelog has been created to track changes.
- When code is pushed to the `dev` branch, build and push the image to
  dockerhub with the `latest` tag. On succesful build, trigger test suite.
- Delete the remote run directory after the application has finished running.

### Changed
- If a specific model id is specified to the camera traps applications, pass it
  as `model_id` instead of `model_type`.
- Specify a 6 hour lease for Chameleon hardware, rather than the default 1 day.
- Use ad-hoc floating IPs rather than floating IP reservation leases.

### Removed

## [0.1] 2024-09-13

### Added
- This repository contains code to build a tool to manage the provisioning and
  releasing of edge hardware as well as running and shutting down the
  camera-traps application.
- README.md describes how to build and run ct-controller.
- Makefile to build the python package and docker container.
- Configured continuous integration to automatically generate docker images of
  the software on release.
- The `ctcontroller/` subdirectory contains a python library to provision
  hardware at Chameleon and TACC, setup and run the camera traps code on the
  provisioned hardware, save the output locally, and cleanup the remote system,
  and deprovision it.
