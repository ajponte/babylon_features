We are updating `tools/run.py` so that `features` generation can be invoked.

## Python Application Configuration Settings
- Python Application Configuration settings should exist in `.env` for local runs.

## ZenML Pipeline Infrastructure Configuration
- zenml infrastructure configuration exists in `./zenml/pipeline/config`.

### ZenML Docker Image.
- The pipeline configuration should point to the image created by `Dockerfile`. For now it's only a locally built image.

## Task
Your task is to ensure that `poetry run run.py` correctly invokes `generate_features` via Zenml.
Note that some implementation details are still in progress. Create mock data where appropriate.

## Validation
To validate your changes, build a `tests/test_run.py` pytest suite.

## Open Questions
Write any open questions to a file `QUESTIONS.md`. Wait for the user to respond before executing.
