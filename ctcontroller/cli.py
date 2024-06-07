import argparse
import os
import sys
from __init__ import subcommand_map

def file_path(path):
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid path")

class _HelpAction(argparse._HelpAction):

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()

        # retrieve subparsers from parser
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)]
        # there will probably only be one subparser_action,
        # but better save than sorry
        for subparsers_action in subparsers_actions:
            # get all subparsers and print help
            for choice, subparser in subparsers_action.choices.items():
                print("=== {} ===".format(choice))
                print(subparser.format_help())

        parser.exit()

class CLIParser:
    def __init__(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument ('-h', '--help', action=_HelpAction)
        #parser.add_argument('--cpu_arch')
        #parser.add_argument('--gpu', '-g')
        #parser.add_argument('--gpu-type')
        #parser.add_argument('--nnodes', '-N')
        parser.add_argument('site', type=str, nargs=1, choices=['Chameleon', 'TACC'])
        parser.add_argument('--user-name', '-u', type=str)
        subparsers = parser.add_subparsers(dest='subcommand')

        register_subparser = subparsers.add_parser('register')
        register_subparser.add_argument('--config-file', '-c', type=file_path)
        register_subparser.add_argument('--key-name', '-k', type=str)
        register_subparser.add_argument('--private-key', '-i', type=str)

        provision_subparser = subparsers.add_parser('provision', help='Provision hardware')
        provision_subparser.add_argument('--cpu-type', type=str)
        provision_subparser.add_argument('--node_type', '-n', type=str)
        provision_subparser.add_argument('--gpu', '-g', type=bool, default=False)
        provision_subparser.add_argument('--nodes', '-N', type=int, default=1)
        provision_subparser.add_argument('--provision-id', '-p', type=str, help='provision identifier to run job')

        run_subparser = subparsers.add_parser('run', help='run on reserved hardware')
        run_subparser.add_argument('--job-id', '-j', type=str, help='unique job identifier')
        run_subparser.add_argument('--provision-id', '-p', type=str, help='provision identifier to run job')
        run_subparser.add_argument('--ct-version', '-V', type=str, help='version of camera traps to run', default='0.3.3')
        run_subparser.add_argument('--branch', '-b', type=str, help='branch of camera traps', default='main')

        kill_subparser = subparsers.add_parser('kill')
        kill_subparser.add_argument('--job-id', '-j', type=str, help='job identifier to kill')
        kill_subparser.add_argument('--provision-id', '-p', type=str, help='provision identifier to delete')

        check_subparser = subparsers.add_parser('check')
        check_subparser.add_argument('check_type', type=str, choices=subcommand_map.keys())
        
        self.parser = parser

    def parse_args(self, args):
        return self.parser.parse_args(args)

def parse_args(args):
    parser = CLIParser()
    parsed_args = parser.parse_args(args)
    parsed_args.site = parsed_args.site[0]
    if parsed_args.user_name is None and parsed_args.subcommand != 'register':
        print('error: user name must be specified')
        parser.parser.print_help()
        sys.exit(1)
    return parsed_args