from __future__ import annotations

import json
from pathlib import Path

from google.oauth2 import service_account

try:
    from google.cloud import secretmanager
except ImportError:  # pragma: no cover - exercised in env-only smoke tests
    secretmanager = None  # type: ignore[assignment]


def _require_secretmanager() -> None:
    if secretmanager is None:
        raise ModuleNotFoundError(
            "google-cloud-secret-manager is not installed. "
            "Use env-only credentials for V1, or install google-cloud-secret-manager "
            "before enabling secret_ref access."
        )


def build_secret_manager_client(credentials_path: str | None = None) -> secretmanager.SecretManagerServiceClient:
    _require_secretmanager()
    if credentials_path:
        path = Path(credentials_path)
        if path.exists():
            creds = service_account.Credentials.from_service_account_file(str(path))
            return secretmanager.SecretManagerServiceClient(credentials=creds)
    return secretmanager.SecretManagerServiceClient()


def normalize_secret_ref(project_id: str, secret_ref: str) -> str:
    ref = (secret_ref or "").strip()
    if not ref:
        raise ValueError("secret_ref is empty")
    if ref.startswith("projects/"):
        return ref
    if "/" in ref:
        raise ValueError("secret_ref must be secret name or full projects/.../secrets/... path")
    return f"projects/{project_id}/secrets/{ref}"


def access_secret_text(
    project_id: str,
    secret_ref: str,
    version: str = "latest",
    credentials_path: str | None = None,
) -> str:
    client = build_secret_manager_client(credentials_path=credentials_path)
    base_ref = normalize_secret_ref(project_id=project_id, secret_ref=secret_ref)
    name = f"{base_ref}/versions/{version or 'latest'}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")


def _parse_key_value_text(secret_text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in secret_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in data:
            data[key] = value
    return data


def access_secret_dict(
    project_id: str,
    secret_ref: str,
    version: str = "latest",
    credentials_path: str | None = None,
) -> dict:
    text = access_secret_text(
        project_id=project_id,
        secret_ref=secret_ref,
        version=version,
        credentials_path=credentials_path,
    )
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return _parse_key_value_text(text)
