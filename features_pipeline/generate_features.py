# pylint: disable=unused-argument
"""Pipeline step for generating features."""

from zenml import pipeline

from features_pipeline.steps import feature_generation as fg_steps


@pipeline
def generate_features(wait_for: str | list[str] | None = None) -> list[str]:
    """Entry point to the zenml pipeline for generating Babylon features."""
    raw_documents = fg_steps.query_data_lake(after=wait_for)
    clean_documents = fg_steps.clean_documents(raw_documents)

    # Load cleaned docs to vector db.
    last_step_1 = fg_steps.load_to_vector_db(clean_documents)

    embedded_documents = fg_steps.chunk_and_embed(clean_documents)

    # Load embedded chunks to vector db.
    last_step_2 = fg_steps.load_to_vector_db(embedded_documents)

    # pylint: disable=no-member
    return [last_step_1.invocation_id, last_step_2.invocation_id]
