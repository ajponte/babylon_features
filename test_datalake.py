from datalake.mongo_factory import MongoClientFactory
from datalake.repository import TransactionRepository
from datalake.uow import UnitOfWork

DATALAKE_DB_NAME = "babylonDataLake"

def main():
    test_collection = "chase-data-2023-01-03"
    client = MongoClientFactory.get_client()
    coll = MongoClientFactory.get_collection(db_name=DATALAKE_DB_NAME, coll_name=test_collection)
    transaction_repo = TransactionRepository(
        collection=coll
    )

if __name__ == '__name__':
    main()
