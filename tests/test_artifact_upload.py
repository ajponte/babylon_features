"""Unit tests for artifact_upload module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
import requests

from artifact_upload import (
    create_release,
    get_release_by_tag,
    resolve_token,
    sanitize_tag,
    upload_artifact_to_release,
)

# ==============================================================================
# Tests for get_release_by_tag
# ==============================================================================


def test_get_release_by_tag_returns_json_on_200():
    """Verify that get_release_by_tag returns parsed json payload on HTTP 200."""
    expected_release = {"id": 101, "tag_name": "v1.0.0", "name": "Release v1.0.0"}
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = expected_release

    with patch("requests.get", return_value=mock_resp) as mock_get:
        result = get_release_by_tag("owner/repo", "v1.0.0", "test-token")

        assert result == expected_release
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/releases/tags/v1.0.0",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer test-token",
            },
        )


def test_get_release_by_tag_returns_none_on_404():
    """Verify that get_release_by_tag returns None when release is not found (HTTP 404)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with patch("requests.get", return_value=mock_resp):
        result = get_release_by_tag("owner/repo", "v1.0.0", "test-token")
        assert result is None


@pytest.mark.parametrize("status_code", [401, 403, 500, 502])
def test_get_release_by_tag_raises_http_error_on_non_200_non_404(status_code: int):
    """Verify that get_release_by_tag raises HTTPError on non-200, non-404 status codes."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        f"{status_code} Error", response=mock_resp
    )

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(requests.exceptions.HTTPError):
            get_release_by_tag("owner/repo", "v1.0.0", "test-token")


# ==============================================================================
# Tests for create_release
# ==============================================================================


def test_create_release_posts_and_returns_json():
    """Verify that create_release issues a POST request with correct payload and returns JSON."""
    expected_payload = {
        "tag_name": "v1.0.0",
        "name": "Babylon Features Artifact v1.0.0",
        "body": "Automatically generated Babylon features artifact.",
        "draft": False,
        "prerelease": False,
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": 202, "tag_name": "v1.0.0"}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = create_release("owner/repo", "v1.0.0", "test-token")

        assert result == {"id": 202, "tag_name": "v1.0.0"}
        mock_post.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/releases",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer test-token",
            },
            json=expected_payload,
        )
        mock_resp.raise_for_status.assert_called_once()


# ==============================================================================
# Tests for upload_artifact_to_release
# ==============================================================================


def test_upload_artifact_to_release_deletes_duplicate_and_uploads(tmp_path):
    """Verify that existing duplicate asset is deleted before uploading the new asset."""
    artifact_file = tmp_path / "babylon-features.zip"
    artifact_file.write_bytes(b"PK\x03\x04fake-zip-data")

    # Mock release assets query returning an existing asset with the same name
    mock_assets_resp = MagicMock()
    mock_assets_resp.json.return_value = [
        {"name": "babylon-features.zip", "url": "https://api.github.com/assets/456"}
    ]

    mock_delete_resp = MagicMock()
    mock_upload_resp = MagicMock()

    with (
        patch("requests.get", return_value=mock_assets_resp) as mock_get,
        patch("requests.delete", return_value=mock_delete_resp) as mock_delete,
        patch("requests.post", return_value=mock_upload_resp) as mock_post,
    ):
        upload_artifact_to_release("owner/repo", 202, str(artifact_file), "test-token")

        # Verify query for assets
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/releases/202/assets",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer test-token",
            },
        )
        # Verify deletion of duplicate asset
        mock_delete.assert_called_once_with(
            "https://api.github.com/assets/456",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer test-token",
            },
        )
        mock_delete_resp.raise_for_status.assert_called_once()

        # Verify upload POST
        mock_post.assert_called_once()
        post_args, post_kwargs = mock_post.call_args
        expected_upload_url = (
            "https://uploads.github.com/repos/owner/repo/releases/202/assets"
            "?name=babylon-features.zip"
        )
        assert post_args[0] == expected_upload_url
        assert post_kwargs["headers"]["Authorization"] == "Bearer test-token"
        assert post_kwargs["headers"]["Content-Type"] == "application/zip"
        mock_upload_resp.raise_for_status.assert_called_once()


def test_upload_artifact_to_release_no_duplicate(tmp_path):
    """Verify that asset is directly uploaded when no duplicate exists."""
    artifact_file = tmp_path / "babylon-features.zip"
    artifact_file.write_bytes(b"PK\x03\x04fake-zip-data")

    # Mock release assets query returning empty list
    mock_assets_resp = MagicMock()
    mock_assets_resp.json.return_value = []

    mock_upload_resp = MagicMock()

    with (
        patch("requests.get", return_value=mock_assets_resp),
        patch("requests.delete") as mock_delete,
        patch("requests.post", return_value=mock_upload_resp),
    ):
        upload_artifact_to_release("owner/repo", 202, str(artifact_file), "test-token")

        mock_delete.assert_not_called()


# ==============================================================================
# Tests for resolve_token fallback precedence
# ==============================================================================


@pytest.mark.parametrize(
    "cli_token,cli_pat,env_gh,env_pat,expected",
    [
        # 1. --token takes highest precedence
        ("token-cli", "pat-cli", "env-gh", "env-pat", "token-cli"),
        ("token-cli", None, None, None, "token-cli"),
        # 2. --pat-token is second precedence
        (None, "pat-cli", "env-gh", "env-pat", "pat-cli"),
        (None, "pat-cli", None, None, "pat-cli"),
        # 3. GITHUB_TOKEN environment variable is third precedence
        (None, None, "env-gh", "env-pat", "env-gh"),
        (None, None, "env-gh", None, "env-gh"),
        # 4. BABYLON_API_GITHUB_PAT_TOKEN environment variable is fourth precedence
        (None, None, None, "env-pat", "env-pat"),
        # 5. None when all sources empty
        (None, None, None, None, None),
    ],
)
def test_resolve_token_fallback_precedence(
    monkeypatch,
    cli_token: str | None,
    cli_pat: str | None,
    env_gh: str | None,
    env_pat: str | None,
    expected: str | None,
):
    """Verify token resolution order: --token -> --pat-token -> GITHUB_TOKEN -> BABYLON_PAT."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("BABYLON_API_GITHUB_PAT_TOKEN", raising=False)

    if env_gh:
        monkeypatch.setenv("GITHUB_TOKEN", env_gh)
    if env_pat:
        monkeypatch.setenv("BABYLON_API_GITHUB_PAT_TOKEN", env_pat)

    result = resolve_token(cli_token, cli_pat)
    assert result == expected


# ==============================================================================
# Tests for sanitize_tag
# ==============================================================================


@pytest.mark.parametrize(
    "input_tag,expected_output",
    [
        (None, "latest"),
        ("", "latest"),
        ("refs/tags/v1.0.0", "v1.0.0"),
        ("refs/tags/v2.1.0-rc1", "v2.1.0-rc1"),
        ("refs/heads/main", "latest"),
        ("refs/heads/feature/branch", "latest"),
        ("refs/pull/42/merge", "latest"),
        ("features/new-thing", "latest"),
        ("v1.0.0", "v1.0.0"),
        ("release-2026.01", "release-2026.01"),
    ],
)
def test_sanitize_tag(input_tag: str | None, expected_output: str):
    """Verify git ref sanitization into clean release tags or fallback to 'latest'."""
    assert sanitize_tag(input_tag) == expected_output
