"""Service object for building a vectorized document."""
import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from features_pipeline.datalake import Datalake
from features_pipeline.error import RAGError
from features_pipeline.rag.documents.documents_collection import DocumentsCollection
from features_pipeline.utils import create_random_uuid_hex

logging.basicConfig(level='DEBUG')

_LOGGER = logging.getLogger(__name__)

# Two minutes. Since this flag is set *only* if
# no value is present, we want it to be as small
# as possible. In a production cloud environment,
# this can be bumped up much higher.
DEFAULT_DOC_PROCESSING_TIMEOUT_SECONDS = 180


# The max number of RAG documents to store in memory
# for any given python process.
PROCESS_MAX_RAG_DOCUMENTS = 100

@dataclass
class RagCollection:
    """
    Encapsulates RAG documents for a set of collections.
    """
    # Python process ID.
    pid: int
    documents:list[Document]
    _max_size = PROCESS_MAX_RAG_DOCUMENTS
    _start_ts: float

    def __add__(self, other):
        """
        Add a new langchain `Document` to the list in an instantiated `RAGCollection`.

        :param other: langchain `Document` to add.
        :return:
        """
        if len(other) > PROCESS_MAX_RAG_DOCUMENTS:
            raise ValueError(f'`PROCESS_MAX_RAG_DOCUMENTS` limit reached')
        else:
            self.documents.append(other)

    def vectorize(self) -> None:
        """
        Vectorize and persist the documents in the vectorStore.
        """
        collection_name = 'test-collection'
        embeddings = OpenAIEmbeddings()
        # Initialize Chroma, specifying a collection name and persistence directory if needed
        vector_store = Chroma(
            # Todo: move to constants
            collection_name="my_document_collection",
            embedding_function=embeddings,
            persist_directory="./chroma_db"  # Optional: for persistent storage
        )

        _LOGGER.debug(f'Vectoring documents for `RAGCollection`. PID: {self.pid}')
        vector_store.add_documents(documents=self.documents)

        _LOGGER.debug(f'Finished vectoring documents for `RAGCollection`. PID: {self.pid}')



class DocumentsManager(ABC):
    """Abstract parent class for Building and returning parsed documents from the data lake."""
    def __init__(self, doc_processing_timeout_seconds: int):
        """
        Constructor.

        :param doc_processing_timeout_seconds: The number of seconds which can elapse
                                               while an instance of this DocumentManager
                                               is processing documents.
        """
        self._timeout_seconds = doc_processing_timeout_seconds

    @abstractmethod
    def build_documents(self) -> list[Document]:
        """
        Builds and returns parsed documents from the data lake.
        """

class BabylonDocumentsManager(DocumentsManager):
    _timeout_seconds: int = DEFAULT_DOC_PROCESSING_TIMEOUT_SECONDS

    _instance: Datalake | None = None

    _collection: str | None = None


    # pylint: disable=unused-argument
    def __new__(cls, config: dict[str, Any]):
        if cls._instance is None:
            # Cache this instance.
            cls._instance = super(BabylonDocumentsManager, cls).__new__(cls)  # type: ignore
            # Cache a MongoDB API client for the datalake.
            try:
                cls._instance.datalake_client = cls.__configure_datalake(config)
            except Exception as e:
                message = 'Unexpected exception while instantiating MongoDB client.'
                _LOGGER.exception(message, exc_info=e)
                raise RAGError(message=message, cause=e) from e

        else:
            _LOGGER.info("Instance already exists. Returning cached.")
        return cls._instance

    @classmethod
    def __configure_datalake(cls, config: dict) -> Datalake:
        try:
            return Datalake(
                host=config['MONGO_DB_HOST'],
                port=config['MONGO_DB_PORT'],
                username=config['MONGO_DB_USER'],
                password=config['MONGO_DB_PASSWORD'],
                connection_timeout_seconds=config['MONGO_CONNECTION_TIMEOUT_SECONDS']
            )
        except Exception as e:
            message = 'Unexpected exception while instantiating MongoDB client.'
            _LOGGER.exception(message, exc_info=e)
            raise RAGError(message=message, cause=e) from e


    @property
    def data_lake(self) -> Datalake:
        return self._instance.datalake_client

    def build_documents(self) -> None:
        """Build Documents from the mongo data lake collections."""
        self._build_collection_documents()

    def _build_collection_documents(self) -> None:
        """
        Build a list of RAG documents from a mongo datalake collection.

        :return: The documents. The return type of this method is a `RAGCollection`.
        """
        _LOGGER.info(f'Fetching documents from collection {self._collection}')
        collections = self.data_lake.list_collections()

        # Set PID, start_ts, etc for current rag/python process.
        # rag_documents_collection.set_rag_process()
        rag_collection = self.__build_rag_collection()
        for datalake_collection in collections:
            _LOGGER.info(f'Adding new RAG document to RagCollection {rag_collection.pid}')
            rag_collection.__add__(self.build_documents_for_collection(datalake_collection))

        _LOGGER.info('Persisting vectorized documents to the vector store')
        rag_collection.vectorize()

    def __build_rag_collection(self) -> RagCollection:
        """
        Return a new `RagCollection` object. This method should be called when a new
        document parsing process is needed. The intention of this interface is to manage
        the start of a new document parsing process, which is compute-intensive. As such,
        The PID and start time as a UTC int is recorded in the instantiation of the object.

        :return: A new `RagCollection`.
        """
        def set_rag_process(pid: int, start_ts: float, docments: list) -> RagCollection:
            """
            Set the start time and current PID for a RAG process.


            :param pid: Current python PID.
            :param start_ts: PID ts start.
            """
            if len(docments) > 0:
                raise ValueError(f'Documents must be empty to create a new RAGCollection: {len(docments)}')

            _LOGGER.debug(f'Starting RAG process: {pid} at {now}')
            return RagCollection(pid=pid, _start_ts=start_ts, documents=docments)

        # Create new `RagCollection` for this python process.
        now = datetime.now().astimezone(timezone.utc)
        return set_rag_process(
            pid=os.getpid(),
            start_ts=now.timestamp(),
            docments=[]
        )

    def build_documents_for_collection(self, datalake_collection: str) -> list[Document]:
        """
        Build and return a list langchain documents, which were parsed from a MongoDB collection.

        :param datalake_collection: Collection name.
        :return: List of `langchain` ADT `Document`. Todo: Generalize `Document`.
        """
        _LOGGER.debug(f'Fetching documents from collection {datalake_collection}')
        langchain_collection = DocumentsCollection(
            # todo: Move this fetch to Collection instantiation.
            records=self.datalake_client.find({}, collection=datalake_collection)
        )
        return list(langchain_collection)


    def build_langchain_document(self, source) -> Document:
        """
        Build and return a langchain document.

        :return: The document.
        """
        try:
            return Document(
                page_content=self.build_document_content(source),
                metadata=self.build_document_metadata(source),
                id=create_random_uuid_hex()
            )
        except Exception as e:
            message = f'Error building langchain doc. Err: {e}'
            raise RAGError(message=message, cause=e) from e

    def build_document_content(self) -> str:
        """
        Convert transaction data into a concise, readable text chunk.
        The structure of the text content is crucial for RAG performance.

        :return: Formatted content for RAG.
        """
        _LOGGER.info(f'Building RAG document for collection {self._collection}')
        content = (
            f"On {self._datalake_document.get('PostingDate', 'N/A')}, a transaction occurred with details: "
            f"Description: {self._datalake_document.get('Description', 'N/A')}. "
            f"Amount: ${self._datalake_document.get('Amount', 0.0):.2f}. "
            f"Type: {self._datalake_document.get('Type', 'N/A')}."
        )

        return content

    def build_document_metadata(self, source: dict) -> dict[str, str]:
        """
        Build metadata for a LangChain document.

        :param source: Data source mapping.
        :return: Metadata as a dict.
        """
        # The metadata retains useful filtering info (like the source collection/date)
        _LOGGER.info(f'Building RAG metadata for collection {self._collection}')
        metadata = {
            "source_collection": self._collection,
            "transaction_date": source.get("PostingDate"),
            "amount": source.get("Amount"),
            "type": source.get("Type"),
            # Add all other fields as metadata for advanced filtering
            **source
        }
        return metadata
