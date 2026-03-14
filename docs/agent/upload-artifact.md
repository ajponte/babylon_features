We are building a way to deploy `babylon_features` as an artifact, which is a Zip module.

## Task
Your task is to design and implement a Github CI workflow to build this python project with `tox`, and push the built artifact to Github.
- The workflow should be implemented in a Python script, named `artifact_upload.py`.
- There should be a CD flow in `.github` to deploy to Github artifacts.

## Credentials
The Guthub PAT should exist at `$BABYLON_API_GITHUB_PAT_TOKEN`.
If there are issues with credentials for pushing to Github, check with the user for instructions.

## TOX
Tox should be the source of truth for building the zip module.

## README and Documentation.
Update the README.md with any changes. Ensure the flow is well-documented and commented.

