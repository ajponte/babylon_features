import sys
import argparse
from dotenv import load_dotenv

from features_pipeline.config.config import update_config_from_environment
from features_pipeline.processor import Processor

_parser = argparse.ArgumentParser(description='Generate Babylon Features')
# todo: Obviously in a production environment this would all be a helm chart
_parser.add_argument('--env-source', help='Target env source. This might be a .env file.')
_parser.add_argument('--collection', help='The data source collection')

def main():
    args = _parser.parse_known_args()[0]
    env_source = args.env_source
    _load_env_from_file(env_source)

    collection = args.collection
    config = {}
    update_config_from_environment(config)
    try:
        print(f'Invoking processor for collection {collection}')
        Processor(config).process_collection(collection)
        print(f'Finished processing collection {collection}')
    except Exception as e:
        print(f'Unable to to process target collection. {e}')
        sys.exit(1)

def _load_env_from_file(env_file: str | None):
    if env_file:
        load_dotenv(dotenv_path=env_file)
        print(f'loaded {env_file}')
    else:
        load_dotenv()
        print(f'loaded from internal env file')

if __name__ == '__main__':
    main()
