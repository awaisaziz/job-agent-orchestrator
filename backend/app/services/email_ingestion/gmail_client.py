"""Connector interface for retrieving Gmail messages via MCP or direct integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.email_ingestion.types import ConnectorTokens, EmailMessage


class GmailMessageSource(Protocol):
    """Protocol to support both MCP and direct Gmail readers."""

    def list_messages(
        self,
        tokens: ConnectorTokens,
        *,
        since_message_id: str | None,
        max_results: int,
        read_only_scopes: tuple[str, ...],
    ) -> list[EmailMessage]:
        """Return ordered messages after since_message_id using read-only scopes only."""


@dataclass(slots=True)
class GmailConnector:
    """Thin wrapper around an injected Gmail source implementation."""

    source: GmailMessageSource

    def fetch_messages(
        self,
        tokens: ConnectorTokens,
        *,
        since_message_id: str | None,
        max_results: int,
        read_only_scopes: tuple[str, ...],
    ) -> list[EmailMessage]:
        return self.source.list_messages(
            tokens,
            since_message_id=since_message_id,
            max_results=max_results,
            read_only_scopes=read_only_scopes,
        )
