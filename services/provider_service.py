"""
ProviderService: manages payment provider adapters
"""

from typing import Optional
from decimal import Decimal
from flask import current_app
from services.providers.base import ProviderAdapter
from services.providers.mpesa import MpesaAdapter
from services.providers.airtel import AirtelAdapter
from services.providers.tkash import TKashAdapter


class ProviderService:
    """Service for managing payment provider adapters"""

    def __init__(self):
        self._adapters = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register default provider adapters"""
        self._adapters["MPESA"] = MpesaAdapter()
        self._adapters["AIRTEL"] = AirtelAdapter()
        self._adapters["AIRTE"] = AirtelAdapter()  # Alternative name
        self._adapters["TKASH"] = TKashAdapter()
        # TODO: Add Flutterwave, DPO, Cellulant card aggregators

    def get_adapter(self, provider: str) -> Optional[ProviderAdapter]:
        """Get provider adapter by name"""
        return self._adapters.get(provider.upper())

    def register_adapter(self, name: str, adapter: ProviderAdapter):
        """Register a custom adapter"""
        self._adapters[name.upper()] = adapter

    def list_providers(self) -> list:
        """List available provider names"""
        return list(self._adapters.keys())

