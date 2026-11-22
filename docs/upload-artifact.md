# Babylon Features Artifact Deployment

`babylon_features` distributes its deployable package as a compressed Zip module artifact attached to GitHub Releases.

## Architecture & Workflow

The artifact release workflow operates across two primary components:

1. **GitHub Actions Workflow (`.github/workflows/artifact-cd.yml`)**:
   - Triggers on push to `main`, version tags (`v*`), or manual execution (`workflow_dispatch`).
   - Uses GitHub's automatic `${{ secrets.GITHUB_TOKEN }}` with write permissions.
   - Invokes `artifact_upload.py` to build and publish the release asset.

2. **Upload Automation Script (`artifact_upload.py`)**:
   - Builds the distribution package via `tox -e dist` (`babylon-features.zip`).
   - Resolves or creates the corresponding GitHub Release based on git tags or commit refs.
   - Uploads the zip asset (replacing duplicate assets if one exists for the tag).

## Authentication & Credentials

GitHub API authentication supports multiple providers with the following resolution precedence:

1. `--token <TOKEN>`: Explicit CLI option.
2. `--pat-token <TOKEN>`: Legacy CLI option alias for backward compatibility.
3. `GITHUB_TOKEN`: Canonical environment variable automatically provided by GitHub Actions runner.
4. `BABYLON_API_GITHUB_PAT_TOKEN`: Optional legacy environment variable for local runs or external PAT setups.

In GitHub Actions CI/CD workflows, `${{ secrets.GITHUB_TOKEN }}` is the canonical token provider.

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  BABYLON_API_GITHUB_PAT_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## CLI Usage

Run manually:

```bash
python artifact_upload.py --repo owner/babylon_features --tag v1.0.0 --token "$GITHUB_TOKEN"
```

Options:
- `--repo`: Target GitHub repository in `owner/repo` format (required).
- `--tag`: Release tag name. If omitted or a branch ref, defaults to `latest`.
- `--token`: GitHub authentication token (defaults to `GITHUB_TOKEN` or `BABYLON_API_GITHUB_PAT_TOKEN`).
- `--pat-token`: Legacy alias for `--token`.
- `--skip-build`: Skips running `tox -e dist` if the zip artifact is already built.

## Packaging Source of Truth

Tox is the single source of truth for generating distribution bundles:
```bash
tox -e dist
```
This generates `babylon-features.zip` in the repository root.
