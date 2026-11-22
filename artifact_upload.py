"""Babylon Features artifact release and upload automation script."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import requests


def run_tox_build() -> None:
    """
    Executes tox to build the artifact using the dist environment.
    """
    print("Building artifact with tox -e dist...")
    try:
        subprocess.run(["tox", "-e", "dist"], check=True)
        print("Tox build successful.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Tox build failed with exit code {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'tox' command not found. Ensure tox is installed.")
        sys.exit(1)


def sanitize_tag(raw_tag: str | None) -> str:
    """
    Sanitizes tag from Git refs or raw input:
    - None or empty -> 'latest'
    - refs/tags/v1.0.0 -> 'v1.0.0'
    - refs/heads/... or other ref names containing '/' -> 'latest'
    - simple tag (e.g. 'v1.0.0') -> preserved as-is
    """
    if not raw_tag:
        return "latest"
    if raw_tag.startswith("refs/tags/"):
        return raw_tag.replace("refs/tags/", "")
    if "/" in raw_tag:
        return "latest"
    return raw_tag


def resolve_token(
    cli_token: str | None = None, cli_pat_token: str | None = None
) -> str | None:
    """
    Resolves the GitHub authentication token with the following fallback precedence:
    1. Explicit --token CLI option
    2. Legacy --pat-token CLI option
    3. GITHUB_TOKEN environment variable
    4. BABYLON_API_GITHUB_PAT_TOKEN environment variable
    """
    if cli_token:
        return cli_token
    if cli_pat_token:
        return cli_pat_token
    return os.environ.get("GITHUB_TOKEN") or os.environ.get(
        "BABYLON_API_GITHUB_PAT_TOKEN"
    )


def get_release_by_tag(repo: str, tag: str, token: str) -> dict | None:
    """Fetches a release by its tag. Returns None only on 404; raises on other non-200s."""
    api_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return None


def create_release(repo: str, tag: str, token: str) -> dict:
    """
    Creates a new release on GitHub.
    """
    print(f"Creating new release for tag: {tag}")
    api_url = f"https://api.github.com/repos/{repo}/releases"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }
    data = {
        "tag_name": tag,
        "name": f"Babylon Features Artifact {tag}",
        "body": "Automatically generated Babylon features artifact.",
        "draft": False,
        "prerelease": False,
    }
    response = requests.post(api_url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()


def upload_artifact_to_release(
    repo: str, release_id: int, artifact_path: str, token: str
) -> None:
    """
    Uploads a file as a release asset, replacing any existing asset with the same name.
    """
    artifact_name = os.path.basename(artifact_path)
    print(f"Uploading {artifact_name} to release {release_id}...")

    base_headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }

    # First, check if asset already exists and delete it if so (to allow overwrite)
    api_url = f"https://api.github.com/repos/{repo}/releases/{release_id}/assets"
    response = requests.get(api_url, headers=base_headers)
    response.raise_for_status()
    assets = response.json()
    for asset in assets:
        if asset["name"] == artifact_name:
            print(f"Deleting existing asset: {artifact_name}")
            delete_url = asset["url"]
            requests.delete(delete_url, headers=base_headers).raise_for_status()

    # Upload the new asset
    upload_url = (
        f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets"
        f"?name={artifact_name}"
    )
    upload_headers = {
        **base_headers,
        "Content-Type": "application/zip",
    }

    with open(artifact_path, "rb") as f:
        response = requests.post(upload_url, headers=upload_headers, data=f)
        response.raise_for_status()

    print(f"Successfully uploaded {artifact_name} to GitHub Releases.")


def main() -> None:
    """
    Main entry point for building and uploading Babylon Features artifacts to GitHub Releases.
    The script:
    1. Parses command-line arguments for repo, tag, and GitHub token.
    2. Determines the tag to use (defaults to 'latest').
    3. Runs 'tox -e dist' to generate 'babylon-features.zip' unless --skip-build is set.
    4. Fetches or creates a GitHub Release for the specified tag.
    5. Uploads 'babylon-features.zip' as a release asset (overwriting if it already exists).
    """
    parser = argparse.ArgumentParser(
        description="Build and upload Babylon Features artifact to GitHub."
    )
    parser.add_argument(
        "--repo", required=True, help="GitHub repository (e.g., owner/repo)"
    )
    parser.add_argument(
        "--tag", help="Release tag to upload to (defaults to 'latest' if not provided)"
    )
    parser.add_argument(
        "--token",
        dest="token",
        default=None,
        help=(
            "GitHub authentication token "
            "(defaults to GITHUB_TOKEN or BABYLON_API_GITHUB_PAT_TOKEN)"
        ),
    )
    parser.add_argument(
        "--pat-token",
        dest="pat_token",
        default=None,
        help="Legacy alias for --token",
    )
    parser.add_argument(
        "--skip-build", action="store_true", help="Skip the tox build step"
    )

    args = parser.parse_args()

    tag = sanitize_tag(args.tag)
    token = resolve_token(args.token, args.pat_token)

    if not token:
        print(
            "Error: GitHub token not provided. "
            "Set GITHUB_TOKEN or BABYLON_API_GITHUB_PAT_TOKEN, or use --token."
        )
        sys.exit(1)

    artifact_path = "babylon-features.zip"

    # Step 1: Build the artifact using tox as the source of truth
    if not args.skip_build:
        run_tox_build()

    # Step 2: Ensure the artifact was actually built
    if not os.path.exists(artifact_path):
        print(f"Error: Artifact not found at {artifact_path}")
        sys.exit(1)

    try:
        # Step 3: Find or create the GitHub Release
        release = get_release_by_tag(args.repo, tag, token)
        if not release:
            release = create_release(args.repo, tag, token)

        # Step 4: Upload the artifact as a release asset
        upload_artifact_to_release(args.repo, release["id"], artifact_path, token)
    except requests.exceptions.RequestException as e:
        print(f"GitHub API Error: {e}")
        if e.response is not None:
            print(f"Response: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
