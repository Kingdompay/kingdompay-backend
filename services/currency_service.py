"""
Multi-Currency Service for KingdomPay
Handles currency conversion and exchange rates
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from extensions import redis_client

logger = logging.getLogger(__name__)


class SupportedCurrency:
    """Supported currencies"""
    KES = "KES"  # Kenyan Shilling (base)
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    UGX = "UGX"  # Ugandan Shilling
    TZS = "TZS"  # Tanzanian Shilling
    RWF = "RWF"  # Rwandan Franc
    ZAR = "ZAR"  # South African Rand


# Default exchange rates (relative to KES)
DEFAULT_RATES = {
    "KES": Decimal("1.0"),
    "USD": Decimal("0.0078"),      # 1 KES = 0.0078 USD (approx 128 KES per USD)
    "EUR": Decimal("0.0072"),      # 1 KES = 0.0072 EUR
    "GBP": Decimal("0.0062"),      # 1 KES = 0.0062 GBP
    "UGX": Decimal("29.0"),        # 1 KES = 29 UGX
    "TZS": Decimal("19.5"),        # 1 KES = 19.5 TZS
    "RWF": Decimal("9.5"),         # 1 KES = 9.5 RWF
    "ZAR": Decimal("0.14"),        # 1 KES = 0.14 ZAR
}


class CurrencyService:
    """Service for currency conversion and exchange rates"""

    def __init__(self):
        self.api_key = os.environ.get("EXCHANGE_RATE_API_KEY")
        self.base_currency = "KES"
        self.cache_ttl = 3600  # 1 hour cache

    def get_supported_currencies(self) -> List[Dict[str, str]]:
        """Get list of supported currencies"""
        currencies = [
            {"code": "KES", "name": "Kenyan Shilling", "symbol": "KSh"},
            {"code": "USD", "name": "US Dollar", "symbol": "$"},
            {"code": "EUR", "name": "Euro", "symbol": "€"},
            {"code": "GBP", "name": "British Pound", "symbol": "£"},
            {"code": "UGX", "name": "Ugandan Shilling", "symbol": "USh"},
            {"code": "TZS", "name": "Tanzanian Shilling", "symbol": "TSh"},
            {"code": "RWF", "name": "Rwandan Franc", "symbol": "FRw"},
            {"code": "ZAR", "name": "South African Rand", "symbol": "R"},
        ]
        return currencies

    def get_exchange_rates(self, base_currency: str = "KES") -> Dict[str, Any]:
        """Get current exchange rates"""
        try:
            # Try to get from cache
            cache_key = f"exchange_rates:{base_currency}"
            cached = self._get_cached_rates(cache_key)
            if cached:
                return cached

            # Fetch from API if available
            if self.api_key:
                rates = self._fetch_live_rates(base_currency)
                if rates:
                    self._cache_rates(cache_key, rates)
                    return rates

            # Use default rates
            rates = self._get_default_rates(base_currency)
            return rates

        except Exception as e:
            logger.error(f"Failed to get exchange rates: {e}")
            return self._get_default_rates(base_currency)

    def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str
    ) -> Dict[str, Any]:
        """Convert amount between currencies"""
        try:
            if from_currency == to_currency:
                return {
                    "success": True,
                    "amount": float(amount),
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "converted_amount": float(amount),
                    "rate": 1.0
                }

            rates = self.get_exchange_rates("KES")
            
            # Convert from source to KES
            if from_currency == "KES":
                kes_amount = amount
            else:
                from_rate = Decimal(str(rates["rates"].get(from_currency, 1)))
                kes_amount = amount / from_rate

            # Convert from KES to target
            if to_currency == "KES":
                converted = kes_amount
                rate = Decimal("1") / Decimal(str(rates["rates"].get(from_currency, 1)))
            else:
                to_rate = Decimal(str(rates["rates"].get(to_currency, 1)))
                converted = kes_amount * to_rate
                rate = to_rate / Decimal(str(rates["rates"].get(from_currency, 1))) if from_currency != "KES" else to_rate

            return {
                "success": True,
                "amount": float(amount),
                "from_currency": from_currency,
                "to_currency": to_currency,
                "converted_amount": float(round(converted, 2)),
                "rate": float(round(rate, 6)),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Currency conversion failed: {e}")
            return {"success": False, "error": str(e)}

    def format_currency(
        self,
        amount: Decimal,
        currency: str,
        include_symbol: bool = True
    ) -> str:
        """Format amount with currency symbol"""
        symbols = {
            "KES": "KSh",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "UGX": "USh",
            "TZS": "TSh",
            "RWF": "FRw",
            "ZAR": "R"
        }
        
        symbol = symbols.get(currency, currency)
        formatted = f"{float(amount):,.2f}"
        
        if include_symbol:
            return f"{symbol} {formatted}"
        return formatted

    def _fetch_live_rates(self, base_currency: str) -> Optional[Dict[str, Any]]:
        """Fetch live rates from external API"""
        try:
            # Example using exchangerate-api.com (free tier)
            url = f"https://v6.exchangerate-api.com/v6/{self.api_key}/latest/{base_currency}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "base": base_currency,
                    "rates": data.get("conversion_rates", {}),
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "live"
                }
            return None
        except Exception as e:
            logger.error(f"Failed to fetch live rates: {e}")
            return None

    def _get_default_rates(self, base_currency: str) -> Dict[str, Any]:
        """Get default exchange rates"""
        if base_currency == "KES":
            rates = {k: float(v) for k, v in DEFAULT_RATES.items()}
        else:
            # Convert rates to new base
            base_rate = DEFAULT_RATES.get(base_currency, Decimal("1"))
            rates = {k: float(v / base_rate) for k, v in DEFAULT_RATES.items()}
        
        return {
            "base": base_currency,
            "rates": rates,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "default"
        }

    def _get_cached_rates(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get rates from cache"""
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached.decode())
            return None
        except Exception:
            return None

    def _cache_rates(self, cache_key: str, rates: Dict[str, Any]):
        """Cache exchange rates"""
        try:
            redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(rates)
            )
        except Exception as e:
            logger.debug(f"Failed to cache rates: {e}")
