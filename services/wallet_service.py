"""
Wallet Service: Helper methods for wallet operations including system wallets
"""

from decimal import Decimal
from typing import Optional
from flask import current_app
from extensions import db
from models.wallet import Wallet


class WalletService:
    """Service for wallet operations"""

    @staticmethod
    def get_or_create_platform_wallet() -> Wallet:
        """Get or create platform wallet"""
        wallet = Wallet.query.filter_by(
            owner_type="PLATFORM",
            owner_id=0,
        ).first()

        if not wallet:
            wallet = Wallet(
                owner_type="PLATFORM",
                owner_id=0,
                user_id=None,
                currency="KES",
                balance=Decimal("0"),
                display_number="PLATFORM001",
            )
            db.session.add(wallet)
            db.session.commit()
            current_app.logger.info("Created platform wallet")

        return wallet

    @staticmethod
    def get_or_create_federal_wallet() -> Wallet:
        """Get or create federal reserve wallet"""
        wallet = Wallet.query.filter_by(
            owner_type="FEDERAL",
            owner_id=0,
        ).first()

        if not wallet:
            wallet = Wallet(
                owner_type="FEDERAL",
                owner_id=0,
                user_id=None,
                currency="KES",
                balance=Decimal("0"),
                display_number="FEDERAL001",
            )
            db.session.add(wallet)
            db.session.commit()
            current_app.logger.info("Created federal wallet")

        return wallet

    @staticmethod
    def get_or_create_community_wallet(community_id: int) -> Optional[Wallet]:
        """Get or create community wallet"""
        wallet = Wallet.query.filter_by(
            owner_type="COMMUNITY",
            owner_id=community_id,
        ).first()

        if not wallet:
            wallet = Wallet(
                owner_type="COMMUNITY",
                owner_id=community_id,
                user_id=None,
                currency="KES",
                balance=Decimal("0"),
                display_number=f"COMM-{community_id:09d}",
            )
            db.session.add(wallet)
            db.session.commit()
            current_app.logger.info(
                f"Created community wallet for community {community_id}"
            )

        return wallet

    @staticmethod
    def initialize_system_wallets():
        """Initialize platform and federal wallets on startup"""
        WalletService.get_or_create_platform_wallet()
        WalletService.get_or_create_federal_wallet()
