import json
import os
import tempfile

from google.cloud import bigquery
from google.oauth2 import service_account

_client: bigquery.Client | None = None


def _init_credentials_from_env() -> None:
    """Write inline JSON credentials to a temp file when deployed on Railway."""
    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w")
        tmp.write(creds_json)
        tmp.flush()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name


def get_bq_client() -> bigquery.Client:
    global _client
    if _client is None:
        _init_credentials_from_env()
        credentials = service_account.Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
            scopes=["https://www.googleapis.com/auth/bigquery.readonly"],
        )
        _client = bigquery.Client(
            credentials=credentials,
            project=os.getenv("GCP_PROJECT_ID"),
        )
    return _client
