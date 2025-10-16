import os
import argparse
from dotenv import load_dotenv

from features_pipeline.config.config import update_config_from_environment, update_config_from_secrets
from features_pipeline.processor import Processor

_parser = argparse.ArgumentParser(description='Generate Babylon Features')
_parser.add_argument('--env', help='Target environment e.g. `local`.')
_parser.add_argument('--env-source', help='Target env source. This might be a .env file.')
_parser.add_argument('--collection', help='The data source collection')

def main():
    args = _parser.parse_known_args()[0]
    env = args.env
    env_source = args.env_source
    if env_source:
        _load_env_from_file(env_source)
    collection = args.collection
    config = {}
    update_config_from_environment(config)
    update_config_from_secrets(config)
    print(f'Invoking processor for collection {collection}')
    Processor(config).process_collection(collection)
    print(f'Finished processing collection {collection}')

def _load_env_from_file(env_file: str):
    load_dotenv(dotenv_path=env_file)
    print(f'loaded {env_file}')

if __name__ == '__main__':
    main()
