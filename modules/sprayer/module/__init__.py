import os

from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from multiprocessing import Queue

from .consumer import start_consumer


MODULE_NAME = os.getenv('MODULE_NAME')

def main():
    print(f'[DEBUG] {MODULE_NAME} started...')

    parser = ArgumentParser()
    parser.add_argument('config_file', type=FileType('r'))
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    config_parser = ConfigParser()
    config_parser.read_file(args.config_file)
    config = dict(config_parser['default'])
    config.update(config_parser[MODULE_NAME])

    print(f'Running {MODULE_NAME}_consumer...')
    start_consumer(args, config)