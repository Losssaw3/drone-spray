import os

from .main import start_web

MODULE_NAME = os.getenv('MODULE_NAME')
    
def main():
    print(f'[{MODULE_NAME}] started...')
    start_web()