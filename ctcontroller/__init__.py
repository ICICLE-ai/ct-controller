#!/usr/env/python3
"""
This package exposes: 
(1) run: a command to run the ctcontroller workflow
(2) VERSION: the version of the ctcontroller package
"""

from .ct_main import main

VERSION = "0.2"

def run():
    """Calls the ctcontroller main function"""

    main()
