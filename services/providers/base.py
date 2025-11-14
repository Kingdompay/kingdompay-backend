"""
Base ProviderAdapter interface for Phase 2
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal


class ProviderInitResponse:
    def __init__(self, success: bool, provider_ref: Optional[str] = None, message: Optional[str] = None):
        self.success = success
        self.provider_ref = provider_ref
        self.message = message


class PayoutResponse:
    def __init__(self, success: bool, provider_ref: Optional[str] = None, message: Optional[str] = None):
        self.success = success
        self.provider_ref = provider_ref
        self.message = message


class ProviderAdapter(ABC):
    """Abstract interface for payment providers"""

    @abstractmethod
    def initiate_debit(
        self, *, phone: str, amount: Decimal, currency: str, reference: str
    ) -> ProviderInitResponse:
        """Initiate a debit (e.g., STK Push) to collect funds"""
        pass

    @abstractmethod
    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate provider webhook payload"""
        pass

    @abstractmethod
    def payout(
        self, *, phone: str, amount: Decimal, currency: str, reference: str
    ) -> PayoutResponse:
        """Initiate a payout to recipient"""
        pass

    @abstractmethod
    def refund(
        self, *, provider_ref: str, amount: Decimal, reason: str
    ) -> PayoutResponse:
        """Refund a transaction"""
        pass

