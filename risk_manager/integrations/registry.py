from __future__ import annotations

from typing import Any
from risk_manager.integrations.base import IntegrationProvider, MerchantConnection, DeduplicationCache


class IntegrationRegistry:
    """Central registry for managing integration providers and active merchant connections."""

    def __init__(self):
        self._providers: dict[str, IntegrationProvider] = {}
        self._connections: dict[str, MerchantConnection] = {}
        self._dedup_cache = DeduplicationCache()

    def register(self, provider: IntegrationProvider) -> None:
        """Register a provider implementation."""
        self._providers[provider.provider_id] = provider

    def get_provider(self, provider_id: str) -> IntegrationProvider | None:
        """Retrieve registered provider by ID."""
        return self._providers.get(provider_id.lower())

    def list_providers(self) -> list[dict[str, str]]:
        """List all available provider metadata."""
        return [
            {
                "provider_id": p.provider_id,
                "provider_name": p.provider_name,
            }
            for p in self._providers.values()
        ]

    def add_connection(self, connection: MerchantConnection) -> None:
        """Store an active merchant connection."""
        self._connections[connection.connection_id] = connection

    def get_connection(self, connection_id: str) -> MerchantConnection | None:
        """Retrieve connection by connection_id."""
        return self._connections.get(connection_id)

    def list_connections(self, merchant_id: str | None = None) -> list[MerchantConnection]:
        """List active connections, optionally filtered by merchant_id."""
        if merchant_id:
            return [c for c in self._connections.values() if c.merchant_id == merchant_id]
        return list(self._connections.values())

    @property
    def dedup_cache(self) -> DeduplicationCache:
        return self._dedup_cache


registry = IntegrationRegistry()
