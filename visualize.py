"""
Data visualization tools.
"""
from enum import StrEnum

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray
from sklearn.manifold import TSNE
import plotly.graph_objects as go
from sympy.strategies.core import switch

from features_pipeline.logger import get_logger
from features_pipeline.rag.vectorstore import ChromaVectorStore


_LOGGER = get_logger()

DEFAULT_EMBEDDING_MODEL = 'BAAI/bge-small-en-v1.5'
DEFAULT_CHROMA_SQLITE_DIR = './chromadb'
DEFAULT_EMBEDDINGS_COLLECTION_CHROMA = 'babylon_vector_collection'

# DEFAULT_METADATA_KEYS = {
#     "source_collection": collection,
#     "source_document_id": source_id,
#     "transaction_date": source.get("PostingDate"),
#     "amount": source.get("Amount"),
#     "type": source.get("Type"),
# }

class ChartType(StrEnum):
    """
    Type of chart to produce.
    """
    SCATTER_PLOT_2D = 'SCATTER_PLOT_2D'
    SCATTER_PLOT_3D = 'SCATTER_PLOT_3D'


def visualize_vector_store(
    vector_store: ChromaVectorStore,
    chart_type: ChartType
):
    """
    Produce a visualization of the chroma vector store.

    :param vector_store: Vector Store.
    :param chart_type: Type of chart to render.
    """
    # Access the underlying Chroma collection object from the vector store instance
    collection = vector_store.db_client._collection # Access the internal Chroma object
    count = collection.count()
    _LOGGER.info(f'Found {count} items in the collection')

    # Fetch all embeddings, documents, and metadatas
    sample_embeddings = get_all_embeddings(collection) # Corrected function call to get all

    # Get the list of embeddings
    embeddings_list = sample_embeddings.get('embeddings')

    # Check for embeddings: Ensure the key exists and the collection is not empty.
    # We use 'is None' and explicit length check to avoid ambiguous truthiness on array-like objects.
    if embeddings_list is None or len(embeddings_list) == 0:
        _LOGGER.warning("No embeddings found in the collection. Cannot visualize.")
        return

    # The returned structure contains lists of embeddings, documents, and metadatas
    vectors = np.array(embeddings_list) # Convert the list of embeddings to a NumPy array
    documents = sample_embeddings['documents']
    metadatas = sample_embeddings['metadatas']

    # Get the dimensionality from the first vector's size (assuming all are consistent)
    dimensions = vectors.shape[1]
    # Use the actual number of fetched vectors for the count
    num_vectors = vectors.shape[0]

    print(f"There are {num_vectors:,} vectors with {dimensions:,} dimensions in the vector store")


    # Process metadatas to get doc types and colors
    # Ensure metadatas are available and not None/empty
    if metadatas:
        doc_types = [metadata.get('type', 'unknown') for metadata in metadatas] # Use .get for safety
        # Mapping doc_types to colors (Ensure the categories match the actual data/intent)
        category_map = {'amount': 0, 'transaction_date': 1, 'type': 2}
        colors_list = ['blue', 'green', 'red']

        # Assign a color based on the doc_type, defaulting to the last color if not in map
        colors = [colors_list[category_map.get(t, len(colors_list) - 1)] for t in doc_types]
    else:
        doc_types = ['unknown'] * num_vectors
        colors = ['gray'] * num_vectors # Default to gray if no metadata


    if any(
            [chart_type == ChartType.SCATTER_PLOT_2D,
             chart_type == ChartType.SCATTER_PLOT_3D]
    ):
        scatter_plot = create_scatter_plot(
            vectors=vectors,
            chart_type=chart_type,
            doc_types=doc_types,
            documents=documents,
            colors=colors
        )
        _LOGGER.info("Displaying scatter plot")
        scatter_plot.show()
    else:
        _LOGGER.info(f'Unsupported chart type: {chart_type}')

# Renamed function and updated logic to fetch all data
def get_all_embeddings(collection):
    """
    Fetch all data (embeddings, documents, metadatas) from the collection.
    """
    _LOGGER.info(f'Fetching ALL data from collection {collection.name}')
    # Fetches all data (limit=None) and includes all necessary fields
    # We remove the pdb.set_trace() as it halts execution
    results = collection.get(
        ids=collection.get()['ids'], # A way to get all IDs
        include=["embeddings", "documents", "metadatas"]
    )
    # The Chroma 'get' results dictionary already contains:
    # 'ids', 'embeddings', 'documents', 'metadatas'
    return results

def tsne_reduce(vectors: NDArray) -> NDArray:
    """
    Reduce the dimensionality of the vectors to 2D using t-SNE
    (t-distributed stochastic neighbor embedding).

    :param vectors: High-dimensional vectors.
    :return: 2D reduced vectors.
    """
    # Safety check: t-SNE requires at least 2 samples
    if vectors.shape[0] < 2:
        _LOGGER.warning("Not enough samples for t-SNE reduction (need at least 2).")
        return np.empty((0, 2))

    tsne = TSNE(n_components=2, random_state=42)
    # The fit_transform method expects a 2D array: (n_samples, n_features)
    reduced_vectors = tsne.fit_transform(vectors)
    return reduced_vectors

def create_scatter_plot(
        vectors: NDArray,
        chart_type: ChartType,
        doc_types: list,
        documents: list, # Changed from NDArray to list as documents is list of strings
        colors: list | None = None
):
    """
    Create and return a 2d scatter plot.

    :param chart_type: Type of chart to render.
    :param vectors: 2d reduced vectors.
    :param doc_types: Doctype data points categories.
    :param documents: Document texts.
    :param colors: Data point colors
    :return: Scatter plat Figure
    """
    match chart_type:
        case ChartType.SCATTER_PLOT_2D:
            return _generate_scatter_plot_2d(
                vectors=vectors,
                documents=documents,
                doc_types=doc_types,
                colors=colors
            )
        case ChartType.SCATTER_PLOT_3D:
            return _generate_scatter_plot_3d(
                vectors=vectors,
                documents=documents,
                doc_types=doc_types,
                colors=colors
            )

def _generate_scatter_plot_3d(
        vectors: NDArray,
        doc_types: list,
        documents: list,  # Changed from NDArray to list as documents is list of strings
        colors: list | None = None
):
    tsne = TSNE(n_components=3, random_state=42)
    reduced_vectors = tsne.fit_transform(vectors)

    # Create the 3D scatter plot
    fig = go.Figure(data=[go.Scatter3d(
        x=reduced_vectors[:, 0],
        y=reduced_vectors[:, 1],
        z=reduced_vectors[:, 2],
        mode='markers',
        marker=dict(size=5, color=colors, opacity=0.8),
        text=[f"Type: {t}<br>Text: {d[:100]}..." for t, d in zip(doc_types, documents)],
        hoverinfo='text'
    )])

    fig.update_layout(
        title='3D Chroma Vector Store Visualization',
        scene=dict(xaxis_title='x', yaxis_title='y', zaxis_title='z'),
        width=900,
        height=700,
        margin=dict(r=20, b=10, l=10, t=40)
    )

    return fig


def _generate_scatter_plot_2d(
        vectors: NDArray,
        doc_types: list,
        documents: list,  # Changed from NDArray to list as documents is list of strings
        colors: list | None = None
):
    # Reduce vectors to 2d
    reduced_vectors = tsne_reduce(vectors)
    if reduced_vectors.shape[0] == 0:
        _LOGGER.warning("No data points to plot.")
        return go.Figure()

    # Create the 2D scatter plot
    fig = go.Figure(data=[go.Scatter(
        x=reduced_vectors[:, 0],
        y=reduced_vectors[:, 1],
        mode='markers',
        # Use a list of colors
        marker=dict(size=5, color=colors if colors else 'blue', opacity=0.8),
        # Use documents as a list of strings
        text=[f"Type: {t}<br>Text: {d[:100]}..." for t, d in zip(doc_types, documents)],
        hoverinfo='text'
    )])

    fig.update_layout(
        title='2D Chroma Vector Store Visualization (t-SNE)',
        # Changed 'scene' to 'xaxis' and 'yaxis' for a 2D plot
        xaxis_title='t-SNE Dimension 1',
        yaxis_title='t-SNE Dimension 2',
        width=800,
        height=600,
        margin=dict(r=20, b=10, l=10, t=40)
    )
    return fig


def main():
    """
    Main entry point to initialize and visualize vector store.
    """
    config = {
        'EMBEDDINGS_MODEL': DEFAULT_EMBEDDING_MODEL,
        'CHROMA_SQLITE_DIR': DEFAULT_CHROMA_SQLITE_DIR,
        'EMBEDDINGS_COLLECTION_CHROMA': DEFAULT_EMBEDDINGS_COLLECTION_CHROMA
    }

    # Create 2d scatter plot
    visualize_vector_store(
        ChromaVectorStore(
            model=DEFAULT_EMBEDDING_MODEL,
            config=config
        ),
        chart_type=ChartType.SCATTER_PLOT_3D
    )

if __name__ == '__main__':
    main()
