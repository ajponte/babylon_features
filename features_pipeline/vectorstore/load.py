"""Load partitioned documents into the vector store."""
import pymongo

from features_pipeline.error import RAGError
from features_pipeline.vectorstore.partition import load_and_partition_mongo_transactions
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_huggingface import HuggingFaceEmbeddings

DEFAULT_EMBEDDING_MODEL = 'all-MiniLM-L6-v2'

DATALAKE = 'babylonDataLake'

def load_documents() -> None:
    # Load your documents
    try:
        docs = load_and_partition_mongo_transactions(
            mongo_uri="mongodb://localhost:27017/",
            db_name=DATALAKE
        )
        print(f'completed loading {len(docs)} documents')
        initialize(docs)
    except Exception as e:
        message = f'Error loading documents. Error: {e}'
        raise RAGError(message=message, cause=e) from e

def initialize(docs) -> None:
    """Initialize the vector store"""
    # 1. Define the local embedding model
    embeddings = HuggingFaceEmbeddings(model_name=DEFAULT_EMBEDDING_MODEL)

    # 2. Connect to the MongoDB collection
    client = pymongo.MongoClient("mongodb://localhost:27017/", username='admin', password='password')
    collection = client[DATALAKE]["vector_collection"]

    # 3. Create/update the vector store
    # todo: implement MongoDB vector option
    # vector_store = MongoDBAtlasVectorSearch.from_documents(
    #     documents=docs,               # Your loaded and partitioned documents
    #     embedding=embeddings,
    #     collection=collection,
    #     index_name="vector_index",    # Name of the Vector Search Index to be created
    # )

    vector_store = VectorStore(
        documents,
    )


    print(f'Closing vector store collection for index {vector_store._index_name}')
    vector_store.close()

def configure_vector_store(
    uri: str,
    db_name: str,
    collection_name: str,
    index_name: str
) -> MongoDBAtlasVectorSearch:
    """Return a configured vector store."""
    embeddings = HuggingFaceEmbeddings(model_name=DEFAULT_EMBEDDING_MODEL)
    return MongoDBAtlasVectorSearch(
        collection=pymongo.MongoClient(uri, username='admin', password='password')[db_name][collection_name],
        embedding=embeddings,
        index_name=index_name
    )
