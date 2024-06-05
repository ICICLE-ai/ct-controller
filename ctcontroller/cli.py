import argparse
import os
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
        subparsers = parser.add_subparsers(dest='subcommand')

        register_subparser = subparsers.add_parser('register')
        register_subparser.add_argument('-config-file', '-c', type=file_path)

        provision_subparser = subparsers.add_parser('provision')
        provision_subparser.add_argument('--cpu-type', type=str) # choices?
        provision_subparser.add_argument('--node_type', '-n', type=str)
        provision_subparser.add_argument('--gpu', '-g', type=bool, default=False)
        provision_subparser.add_argument('--nodes', '-N', type=int, default=1)

        #run_subparser = subparsers.add_parser('run')

        check_subparser = subparsers.add_parser('check')
        check_subparser.add_argument('check_type', type=str, choices=subcommand_map.keys())
        
        self.parser = parser

    def parse_args(self, args):
        return self.parser.parse_args(args)

def parse_args(args):
    parser = CLIParser()
    parsed_args = parser.parse_args(args)
    return parsed_args