"""Settings from the environment, or from .env written by `make env` (terraform output).

There are no secrets here: authentication is Entra ID via DefaultAzureCredential
(az login locally, managed identity in Azure)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_env_file(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    fqdn: str
    eventhub: str
    consumer_group: str
    checkpoint_account_url: str
    checkpoint_container: str
    namespace_id: str
    throughput_units: int


def load() -> Settings:
    _load_env_file()
    try:
        return Settings(
            fqdn=os.environ["EVENTHUB_FQDN"],
            eventhub=os.environ["EVENTHUB_NAME"],
            consumer_group=os.environ["CONSUMER_GROUP"],
            checkpoint_account_url=os.environ["CHECKPOINT_ACCOUNT_URL"],
            checkpoint_container=os.environ["CHECKPOINT_CONTAINER"],
            namespace_id=os.environ.get("EVENTHUB_NAMESPACE_ID", ""),
            throughput_units=int(os.environ.get("EVENTHUB_TU", "1")),
        )
    except KeyError as missing:
        raise SystemExit(f"Missing setting {missing}. Run `make up` (or `make env`) first.") from None
