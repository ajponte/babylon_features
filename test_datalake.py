from datalake.mongo_factory import MongoClientFactory
from datalake.repository import TransactionRepository
from datalake.uow import UnitOfWork

DATALAKE_DB_NAME = "babylonDataLake"

DATALAKE_HOST = 'localhost'
DATALAKE_PORT = 27017
DALAKE_USER = ''
DATALAKE_PASS = ''
DEFAULT_TIMEOUT_SECONDS = 30

def main():
    test_collection = "chase-data-2023-01-03"
    test_record_id = '68f44e752630f0ae2a18a1fe'
    print('Creating DB client')
    dl_config = {
        'config': {
            'MONGO_DB_HOST': DATALAKE_HOST,
            'MONGO_DB_PORT': DATALAKE_PORT,
            'MONGO_DB_USER': DALAKE_USER,
            'MONGO_DB_PASSWORD': DATALAKE_PASS,
            'MONGO_CONNECTION_TIMEOUT_SECONDS': DEFAULT_TIMEOUT_SECONDS,
        }

    }
    client = MongoClientFactory.get_client(**dl_config)
    print('Successfully connected to datalake')

    # Open the UOW context manager object.
    with UnitOfWork(client) as session:
        coll = MongoClientFactory.get_collection(
            db_name=DATALAKE_DB_NAME, coll_name=test_collection)
        transaction_repo = TransactionRepository(
            collection=coll
        )

        print(f'Fetching transaction {test_record_id} from {test_collection}')
        transaction = transaction_repo.get_by_id(test_record_id)
        print(f'transaction: {transaction}')

if __name__ == '__main__':
    main()
