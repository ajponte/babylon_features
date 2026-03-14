"""
Driver script for invoking the Zenml RAG pipeline.
This script will be updated accordingly as more steps are built.
"""
from datetime import datetime as dt
from pathlib import Path

import click
import dotenv
from loguru import logger

from features.config import config

from features.pipeline import (
    generate_features,
)

_HELP_PROMPT = """
Babylon RAG Pipeline.

Main entry point for pipeline execution.

Run the Run the ZenML project pipelines with various options.

Run a pipeline with the required parameters. This executes
all steps in the pipeline in the correct order using the orchestrator
stack component that is configured in your active ZenML stack.

Examples:
    \b
    # Run the pipeline with default options
    python run.py
    
    \b
    # Run the pipeline without cache
    python run.py --no-cache
    
    \b
    # Run only the ETL pipeline
    python run.py --only-etl
"""
@click.command(
    help=_HELP_PROMPT
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching for the pipeline run.",
)
@click.option(
    "--run-end-to-end-data",
    is_flag=True,
    default=False,
    help="Whether to run all the data pipelines in one go.",
)
@click.option(
    "--run-etl",
    is_flag=True,
    default=False,
    help="Whether to run the ETL pipeline.",
)
@click.option(
    "--run-export-artifact-to-json",
    is_flag=True,
    default=False,
    help="Whether to run the Artifact -> JSON pipeline",
)
@click.option(
    "--etl-config-filename",
    default="digital_data_etl_paul_iusztin.yaml",
    help="Filename of the ETL config file.",
)
@click.option(
    "--run-feature-engineering",
    is_flag=True,
    default=False,
    help="Whether to run the FE pipeline.",
)
@click.option(
    "--run-generate-instruct-datasets",
    is_flag=True,
    default=False,
    help="Whether to run the instruct dataset generation pipeline.",
)
@click.option(
    "--run-generate-preference-datasets",
    is_flag=True,
    default=False,
    help="Whether to run the preference dataset generation pipeline.",
)
@click.option(
    "--run-training",
    is_flag=True,
    default=False,
    help="Whether to run the training pipeline.",
)
@click.option(
    "--run-evaluation",
    is_flag=True,
    default=False,
    help="Whether to run the evaluation pipeline.",
)
@click.option(
    "--export-settings",
    is_flag=True,
    default=False,
    help="Whether to export your settings to ZenML or not.",
)
def main(
    no_cache: bool = False,
    run_end_to_end_data: bool = False,
    run_etl: bool = False,
    run_export_artifact_to_json: bool = False,
    etl_config_filename: str = "digital_data_etl_paul_iusztin.yaml",
    run_feature_engineering: bool = False,
    run_generate_instruct_datasets: bool = False,
    run_generate_preference_datasets: bool = False,
    run_training: bool = False,
    run_evaluation: bool = False,
    export_settings: bool = False,
):
    if not any(
        [
            run_feature_engineering,
            run_end_to_end_data,
            run_etl,
            run_generate_instruct_datasets,
            run_generate_preference_datasets,
            run_training,
            run_evaluation,
        ]
    ):
        click.echo("Please specify an action to run.")
        return

    pipeline_args = {
        "enable_cache": not no_cache,
    }
    # root_dir is two levels up from features/tools/run.py
    root_dir = Path(__file__).resolve().parent.parent.parent
    logger.debug(f"Project root directory: {root_dir}")

    if run_feature_engineering:
        # Features pipeline config.
        run_args_fe = {}
        # Update environment with any `.env` (for local runs only)
        env_path = root_dir / ".env"
        if env_path.exists():
            logger.info(f"Update environment with `{env_path}`")
            dotenv.load_dotenv(env_path)
        else:
            logger.warning(f"No .env found at {env_path}")

        # Update config with existing environment variables.
        logger.debug("Loading features config with environment variables.")
        config.update_config_from_environment(run_args_fe)
        logger.info("Environment loaded.")

        pipeline_args["config_path"] = (
            root_dir / "zenml" / "pipeline" / "config" / "feature_engineering.yaml"
        )
        pipeline_args["run_name"] = (
            f"feature_engineering_run_{dt.now().strftime('%Y_%m_%d_%H_%M_%S')}"
        )

        logger.info(f"Invoking generate_features with config {pipeline_args['config_path']}")
        generate_features.with_options(**pipeline_args)(**run_args_fe)

    else:
        logger.warning("Selected action is not yet implemented in run.py.")


if __name__ == '__main__':
    main()
