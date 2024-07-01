def print_and_exit(msg: str):
    print(f'\033[91m{msg}')
    import sys
    sys.exit(1)
