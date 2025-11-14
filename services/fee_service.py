"""
Fee Service: Calculate and allocate transaction fees and community contributions
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from flask import current_app
from extensions import db
from models.fee import TransactionFee, CommunityContribution, CommunityDevelopmentFund
from models.community import Community
from models.wallet import Wallet


class FeeService:
    """Service for calculating and processing fees and contributions"""

    # Fee rates (configurable)
    TRANSACTION_FEE_RATE = Decimal("0.015")  # 1.5% total
    PLATFORM_FEE_RATE = Decimal("0.005")  # 0.5%
    COMMUNITY_FEE_RATE = Decimal("0.005")  # 0.5%
    FEDERAL_FEE_RATE = Decimal("0.005")  # 0.5%
    
    # Community contribution rate (default 1%, configurable per community)
    DEFAULT_CONTRIBUTION_RATE = Decimal("0.01")  # 1%

    # Transaction limits
    MIN_TRANSACTION = Decimal("10")  # KSh 10
    MAX_TRANSACTION = Decimal("500000")  # KSh 500,000
    MAX_DAILY_LIMIT_TIER0 = Decimal("50000")  # Tier 0 (phone verified)
    MAX_DAILY_LIMIT_TIER1 = Decimal("500000")  # Tier 1 (ID verified)
    MAX_DAILY_LIMIT_TIER2 = Decimal("1000000")  # Tier 2 (enhanced)

    def calculate_fees(self, amount: Decimal, community_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate transaction fees (1.5% split three ways)
        
        Returns:
            Dict with fee breakdown
        """
        platform_fee = amount * self.PLATFORM_FEE_RATE
        community_fee = amount * self.COMMUNITY_FEE_RATE if community_id else Decimal("0")
        federal_fee = amount * self.FEDERAL_FEE_RATE
        total_fee = platform_fee + community_fee + federal_fee

        return {
            "transaction_amount": float(amount),
            "fee_amount": float(total_fee),
            "platform_fee": float(platform_fee),
            "community_fee": float(community_fee),
            "federal_fee": float(federal_fee),
            "net_amount": float(amount - total_fee),
        }

    def calculate_contribution(self, amount: Decimal, community_id: int) -> Dict[str, Any]:
        """
        Calculate community contribution (1% default, configurable)
        
        Returns:
            Dict with contribution amount and rate
        """
        # Get community contribution rate
        cdf = CommunityDevelopmentFund.query.filter_by(community_id=community_id).first()
        rate = cdf.contribution_rate if cdf else self.DEFAULT_CONTRIBUTION_RATE
        
        contribution_amount = amount * rate

        return {
            "transaction_amount": float(amount),
            "contribution_amount": float(contribution_amount),
            "contribution_rate": float(rate),
            "net_amount": float(amount - contribution_amount),
        }

    def validate_transaction_limits(self, amount: Decimal, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Validate transaction against limits
        
        Returns:
            Dict with allowed (bool) and message if not allowed
        """
        if amount < self.MIN_TRANSACTION:
            return {
                "allowed": False,
                "message": f"Minimum transaction amount is KSh {self.MIN_TRANSACTION}",
            }

        if amount > self.MAX_TRANSACTION:
            return {
                "allowed": False,
                "message": f"Maximum transaction amount is KSh {self.MAX_TRANSACTION}",
            }

        # Daily limit check (if user_id provided)
        if user_id:
            from models.kyc import KYCVerification
            from models.payment import Payment
            from datetime import datetime, timedelta

            # Get user's KYC tier
            kyc = KYCVerification.query.filter_by(user_id=user_id).order_by(
                KYCVerification.created_at.desc()
            ).first()
            
            tier = kyc.tier if kyc else "TIER0"
            
            # Determine daily limit based on tier
            daily_limit_map = {
                "TIER0": self.MAX_DAILY_LIMIT_TIER0,
                "TIER1": self.MAX_DAILY_LIMIT_TIER1,
                "TIER2": self.MAX_DAILY_LIMIT_TIER2,
            }
            daily_limit = daily_limit_map.get(tier, self.MAX_DAILY_LIMIT_TIER0)

            # Check today's transactions
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            wallets = Wallet.query.filter_by(user_id=user_id).all()
            wallet_ids = [w.id for w in wallets]

            if wallet_ids:
                daily_total = db.session.query(
                    db.func.sum(Payment.amount)
                ).filter(
                    Payment.payer_wallet_id.in_(wallet_ids),
                    Payment.created_at >= today_start,
                    Payment.status == "SUCCESS",
                ).scalar() or Decimal("0")

                if daily_total + amount > daily_limit:
                    return {
                        "allowed": False,
                        "message": f"Daily limit exceeded. Current: {daily_total}, Limit: {daily_limit}",
                        "current_total": float(daily_total),
                        "limit": float(daily_limit),
                    }

        return {"allowed": True}

    def allocate_fees(
        self,
        journal_id: int,
        payment_id: Optional[int],
        amount: Decimal,
        community_id: Optional[int] = None,
    ) -> TransactionFee:
        """
        Allocate transaction fees and create fee record
        """
        fee_breakdown = self.calculate_fees(amount, community_id)

        # Get or create platform wallet (federal reserve)
        platform_wallet = Wallet.query.filter_by(
            owner_type="PLATFORM",
            owner_id=0,  # Platform wallet
        ).first()

        if not platform_wallet:
            # Create platform wallet if doesn't exist
            platform_wallet = Wallet(
                owner_type="PLATFORM",
                owner_id=0,
                currency="KES",
                balance=Decimal("0"),
            )
            db.session.add(platform_wallet)
            db.session.flush()

        # Create fee record
        fee = TransactionFee(
            journal_id=journal_id,
            payment_id=payment_id,
            transaction_amount=amount,
            fee_amount=Decimal(str(fee_breakdown["fee_amount"])),
            platform_fee=Decimal(str(fee_breakdown["platform_fee"])),
            community_fee=Decimal(str(fee_breakdown["community_fee"])),
            federal_fee=Decimal(str(fee_breakdown["federal_fee"])),
            community_id=community_id,
        )
        db.session.add(fee)

        # Allocate fees to wallets (ledger entries handled separately)
        return fee

    def allocate_contribution(
        self,
        journal_id: int,
        payment_id: Optional[int],
        amount: Decimal,
        community_id: int,
        allocated_to: str = "GENERAL",
    ) -> CommunityContribution:
        """
        Allocate community contribution to CDF
        """
        contrib_breakdown = self.calculate_contribution(amount, community_id)

        # Get or create CDF for community
        cdf = CommunityDevelopmentFund.query.filter_by(community_id=community_id).first()
        if not cdf:
            cdf = CommunityDevelopmentFund(
                community_id=community_id,
                contribution_rate=self.DEFAULT_CONTRIBUTION_RATE,
            )
            db.session.add(cdf)
            db.session.flush()

        # Update CDF balance based on allocation
        contrib_amount = Decimal(str(contrib_breakdown["contribution_amount"]))
        cdf.total_contributed += contrib_amount

        if allocated_to == "EDUCATION":
            cdf.education_balance += contrib_amount
        elif allocated_to == "HEALTH":
            cdf.health_balance += contrib_amount
        elif allocated_to == "WELFARE":
            cdf.welfare_balance += contrib_amount
        else:
            cdf.general_balance += contrib_amount

        # Create contribution record
        contribution = CommunityContribution(
            journal_id=journal_id,
            payment_id=payment_id,
            community_id=community_id,
            transaction_amount=amount,
            contribution_amount=contrib_amount,
            contribution_rate=cdf.contribution_rate,
            allocated_to=allocated_to,
        )
        db.session.add(contribution)

        return contribution

