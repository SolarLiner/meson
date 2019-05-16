import argparse
import logging
import sys


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument(
        '--debug',
        action='store_true',
        default=False,
        help='Increase verbosity')
    parser.add_argument(
        '--tcp',
        help='Specify listening TCP host and port (default: use stdin/out)')


def run(options: argparse.Namespace):
    # Import dynamically as the LSP uses jsonrpc and python-jsonrpc-server
    from . import server

    logger = logging.getLogger()
    sh = logging.StreamHandler(sys.stderr)
    logger.addHandler(sh)
    if options.debug:
        logger.setLevel(logging.DEBUG)
        sh.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
        sh.setLevel(logging.WARNING)

    server = server.new_with_stdio(options)
