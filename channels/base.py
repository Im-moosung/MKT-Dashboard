from dataclasses import dataclass
from datetime import date
from typing import Protocol

from New_Data_flow.common.settings import Settings


@dataclass(frozen=True)
class IngestContext:
    settings: Settings
    start_date: date
    end_date: date
    dry_run: bool
    api_test_only: bool = False
    api_sample_size: int = 1
    max_ads: int = 500
    replace_range: bool = True
    source_id: str | None = None
    branch_id: str | None = None
    channel_key: str | None = None
    provider_key: str | None = None
    account_id_norm: str | None = None
    secret_ref: str | None = None
    secret_version: str | None = None
    tier: str | None = None


@dataclass(frozen=True)
class IngestResult:
    channel: str
    status: str
    message: str


class ChannelIngestor(Protocol):
    name: str

    def run(self, ctx: IngestContext) -> IngestResult:
        ...
