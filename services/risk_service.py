"""
Risk Service: Velocity limits, blacklist checks, AML rules
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List
from flask import current_app
from extensions import db
from models.risk import Blacklist, AMLCase
from models.payment import Payment
from models.wallet import Wallet


class RiskService:
    """Service for risk management and AML checks"""

    def check_blacklist(self, entity_type: str, entity_value: str) -> bool:
        """
        Check if entity is blacklisted
        
        Args:
            entity_type: PHONE|EMAIL|WALLET|USER
            entity_value: The value to check
        Returns:
            True if blacklisted, False otherwise
        """
        blacklist = Blacklist.query.filter_by(
            entity_type=entity_type.upper(),
            entity_value=entity_value,
            status="ACTIVE",
        ).first()
        return blacklist is not None

    def check_velocity_limits(
        self,
        user_id: Optional[int],
        wallet_id: Optional[int],
        amount: Decimal,
        window_minutes: int = 60,
    ) -> Dict[str, Any]:
        """
        Check velocity limits for transactions
        
        Args:
            user_id: User ID (optional)
            wallet_id: Wallet ID (optional)
            amount: Transaction amount
            window_minutes: Time window in minutes (default 60)
        Returns:
            Dict with allowed (bool) and reason (str if not allowed)
        """
        window_start = datetime.utcnow() - timedelta(minutes=window_minutes)

        # Check wallet velocity
        if wallet_id:
            wallet_total = db.session.query(
                db.func.sum(Payment.amount)
            ).filter(
                Payment.payer_wallet_id == wallet_id,
                Payment.created_at >= window_start,
                Payment.status == "SUCCESS",
            ).scalar() or Decimal("0")

            # Limit: 100,000 KES per hour per wallet
            hourly_limit = Decimal("100000")
            if wallet_total + amount > hourly_limit:
                return {
                    "allowed": False,
                    "reason": f"Wallet velocity limit exceeded: {wallet_total} + {amount} > {hourly_limit}",
                    "current_total": float(wallet_total),
                    "limit": float(hourly_limit),
                }

            # Daily limit: 500,000 KES
            daily_start = datetime.utcnow() - timedelta(days=1)
            daily_total = db.session.query(
                db.func.sum(Payment.amount)
            ).filter(
                Payment.payer_wallet_id == wallet_id,
                Payment.created_at >= daily_start,
                Payment.status == "SUCCESS",
            ).scalar() or Decimal("0")

            daily_limit = Decimal("500000")
            if daily_total + amount > daily_limit:
                return {
                    "allowed": False,
                    "reason": f"Daily wallet limit exceeded: {daily_total} + {amount} > {daily_limit}",
                    "current_total": float(daily_total),
                    "limit": float(daily_limit),
                }

        # Check user velocity
        if user_id:
            # Get user's wallets
            wallets = Wallet.query.filter_by(user_id=user_id).all()
            wallet_ids = [w.id for w in wallets]

            if wallet_ids:
                user_hourly_total = db.session.query(
                    db.func.sum(Payment.amount)
                ).filter(
                    Payment.payer_wallet_id.in_(wallet_ids),
                    Payment.created_at >= window_start,
                    Payment.status == "SUCCESS",
                ).scalar() or Decimal("0")

                user_hourly_limit = Decimal("200000")
                if user_hourly_total + amount > user_hourly_limit:
                    return {
                        "allowed": False,
                        "reason": f"User velocity limit exceeded: {user_hourly_total} + {amount} > {user_hourly_limit}",
                        "current_total": float(user_hourly_total),
                        "limit": float(user_hourly_limit),
                    }

        return {"allowed": True}

    def check_transaction_risk(
        self,
        user_id: Optional[int],
        wallet_id: Optional[int],
        amount: Decimal,
        destination: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive risk check before transaction
        
        Returns:
            Dict with allowed (bool), risk_score (0-100), and warnings (list)
        """
        warnings = []
        risk_score = 0

        # Check blacklist
        if wallet_id:
            wallet = Wallet.query.get(wallet_id)
            if wallet and wallet.user_id:
                # Check user phone/email blacklist (if available)
                pass

        if destination:
            # Check destination blacklist
            if self.check_blacklist("PHONE", destination):
                return {
                    "allowed": False,
                    "risk_score": 100,
                    "reason": "Destination is blacklisted",
                    "warnings": ["Blacklisted destination"],
                }

        # Check velocity limits
        velocity_check = self.check_velocity_limits(user_id, wallet_id, amount)
        if not velocity_check.get("allowed"):
            return {
                "allowed": False,
                "risk_score": 80,
                "reason": velocity_check.get("reason"),
                "warnings": ["Velocity limit exceeded"],
            }

        # Check amount thresholds
        high_amount_threshold = Decimal("50000")
        if amount > high_amount_threshold:
            risk_score += 20
            warnings.append(f"High amount transaction: {amount}")

        # Check structuring patterns (multiple transactions just under thresholds)
        if wallet_id:
            recent_count = Payment.query.filter(
                Payment.payer_wallet_id == wallet_id,
                Payment.created_at >= datetime.utcnow() - timedelta(hours=1),
                Payment.status == "SUCCESS",
                Payment.amount < high_amount_threshold,
            ).count()

            if recent_count >= 5:
                risk_score += 30
                warnings.append("Multiple small transactions detected (potential structuring)")

        # Return result
        return {
            "allowed": True,
            "risk_score": min(risk_score, 100),
            "warnings": warnings,
            "requires_review": risk_score >= 50,
        }

    def create_aml_case(
        self,
        user_id: Optional[int],
        case_type: str,
        details: Dict[str, Any],
    ) -> AMLCase:
        """Create an AML case for review"""
        case = AMLCase(
            user_id=user_id,
            case_type=case_type,
            status="OPEN",
            details_json=details,
        )
        db.session.add(case)
        db.session.commit()
        return case

    def get_aml_cases(
        self,
        status: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get AML cases for review"""
        query = AMLCase.query

        if status:
            query = query.filter(AMLCase.status == status.upper())

        if user_id:
            query = query.filter(AMLCase.user_id == user_id)

        cases = query.order_by(AMLCase.created_at.desc()).all()

        return [
            {
                "id": c.id,
                "user_id": c.user_id,
                "case_type": c.case_type,
                "status": c.status,
                "details": c.details_json,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
            }
            for c in cases
        ]

