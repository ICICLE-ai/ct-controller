"""
Contains functions to gracefully handle errors.
"""

import sys

def print_and_exit(msg: str):
    """
    Prints the error message and exits the entire application with an exit code of 1

    Parameters:
        msg (str): the message that should be printed before exiting
    """

    print(f'\033[91mERROR: {msg}')
    sys.exit(1)
