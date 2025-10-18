import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray
from sklearn.manifold import TSNE
import plotly.graph_objects as go

from features_pipeline.logger import get_logger
from features_pipeline.rag.vectorstore import ChromaVectorStore


_LOGGER = get_logger()

DEFAULT_EMBEDDING_MODEL = 'BAAI/bge-small-en-v1.5'
DEFAULT_CHROMA_SQLITE_DIR = './chromadb'
DEFAULT_EMBEDDINGS_COLLECTION_CHROMA = 'babylon_vector_collection'

def visualize_vector_store(vector_store: ChromaVectorStore):
    """
    Produce a visualization of the chroma vector store.

    :param vector_store: Vector Store.
    """
    collection = vector_store.db_client._collection
    count = collection.count()
    _LOGGER.info(f'Found {count} items in the collection')

    sample_embeddings = get_sample_embeddings(collection)

    dimensions = len(sample_embeddings)
    print(f"There are {count:,} vectors with {dimensions:,} dimensions in the vector store")


    vectors = np.array(sample_embeddings['embeddings'])
    documents = sample_embeddings['documents']
    metadatas = sample_embeddings['metadatas']
    doc_types = [metadata['doc_type'] for metadata in metadatas]
    colors = [['blue', 'green', 'red', 'orange'][['products', 'employees', 'contracts', 'company'].index(t)] for t in
              doc_types]

    # Reduce vectors to 2d
    reduced_vectors = tsne_reduce(vectors)

    scatter_plot = create_scatter_plot(
        reduced_vectors=reduced_vectors,
        doc_types=doc_types,
        documents=documents,
        colors=colors
    )

    _LOGGER.info("Displaying scatter plot")
    scatter_plot.show()

def get_sample_embeddings(collection):
    _LOGGER.info(f'Fetching embeddings from collection {collection.name}')
    import pdb; pdb.set_trace()
    sample_embedding = collection.get(limit=1, include=["embeddings"])["embeddings"][0]
    vectors = np.array(sample_embedding)
    return vectors

def tsne_reduce(vectors):
    """
    Reduce the dimensionality of the vectors to 2D using t-SNE
    (t-distributed stochastic neighbor embedding)
    :return:
    """
    tsne = TSNE(n_components=2, random_state=42)
    reduced_vectors = tsne.fit_transform(vectors)
    return reduced_vectors

def create_scatter_plot(
        reduced_vectors,
        doc_types: list,
        documents: NDArray,
        colors: list | None = None
):
    """
    Create and return a 2d scatter plot.

    :param reduced_vectors: 2d reduced vectors.
    :param doc_types: Doctype data points categories.
    :param documents: Document vectors as np array.
    :param colors: Data point colors
    :return: Scatter plat Figure
    """
    # Create the 2D scatter plot
    fig = go.Figure(data=[go.Scatter(
        x=reduced_vectors[:, 0],
        y=reduced_vectors[:, 1],
        mode='markers',
        marker=dict(size=5, color=colors, opacity=0.8),
        text=[f"Type: {t}<br>Text: {d[:100]}..." for t, d in zip(doc_types, documents)],
        hoverinfo='text'
    )])

    fig.update_layout(
        title='2D Chroma Vector Store Visualization',
        scene=dict(xaxis_title='x', yaxis_title='y'),
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
        )
    )

if __name__ == '__main__':
    main()
