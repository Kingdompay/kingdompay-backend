"""
Reconciliation Service: Match provider statements with internal payments
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from flask import current_app
from extensions import db
from models.payment import Payment
from models.settlement_batch import SettlementBatch


class ReconciliationService:
    """Service for reconciling payments with provider statements"""

    def reconcile_provider(
        self,
        provider: str,
        statement_date: date,
        provider_transactions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Reconcile provider statement with internal payments
        
        Args:
            provider: Provider name (MPESA, AIRTEL, etc.)
            statement_date: Date of the statement
            provider_transactions: List of transactions from provider statement
                Each should have: transaction_id, amount, status, timestamp
        """
        # Get all payments for this provider on this date
        payments = Payment.query.filter(
            Payment.provider == provider.upper(),
            db.func.date(Payment.created_at) == statement_date,
            Payment.status.in_(["SUCCESS", "PENDING"]),
        ).all()

        # Calculate expected amount from internal records
        expected_amount = sum(float(p.amount) for p in payments if p.status == "SUCCESS")
        expected_count = len([p for p in payments if p.status == "SUCCESS"])

        # Calculate actual amount from provider statement
        actual_amount = sum(float(t.get("amount", 0)) for t in provider_transactions if t.get("status") == "SUCCESS")
        actual_count = len([t for t in provider_transactions if t.get("status") == "SUCCESS"])

        # Match transactions
        matched = []
        unmatched_internal = []
        unmatched_provider = []

        # Build lookup maps
        provider_map = {t.get("transaction_id"): t for t in provider_transactions}
        payment_map = {p.provider_ref: p for p in payments if p.provider_ref}

        # Match by provider_ref
        for payment in payments:
            if payment.provider_ref:
                provider_txn = provider_map.get(payment.provider_ref)
                if provider_txn:
                    matched.append({
                        "payment_id": payment.id,
                        "provider_ref": payment.provider_ref,
                        "amount": float(payment.amount),
                        "provider_amount": float(provider_txn.get("amount", 0)),
                        "variance": float(payment.amount) - float(provider_txn.get("amount", 0)),
                    })
                else:
                    unmatched_internal.append({
                        "payment_id": payment.id,
                        "provider_ref": payment.provider_ref,
                        "amount": float(payment.amount),
                        "status": payment.status,
                    })

        # Find provider transactions not in our system
        for txn_id, txn in provider_map.items():
            if txn_id not in payment_map:
                unmatched_provider.append({
                    "transaction_id": txn_id,
                    "amount": float(txn.get("amount", 0)),
                    "timestamp": txn.get("timestamp"),
                })

        # Calculate variance
        variance = expected_amount - actual_amount
        variance_percent = (variance / expected_amount * 100) if expected_amount > 0 else 0

        # Create or update settlement batch
        batch = SettlementBatch.query.filter_by(
            provider=provider.upper(),
            settlement_date=statement_date,
        ).first()

        variance_details = {
            "matched_count": len(matched),
            "unmatched_internal_count": len(unmatched_internal),
            "unmatched_provider_count": len(unmatched_provider),
            "unmatched_internal": unmatched_internal[:50],  # Limit for storage
            "unmatched_provider": unmatched_provider[:50],
            "matched": matched[:100],
        }

        if not batch:
            batch = SettlementBatch(
                provider=provider.upper(),
                settlement_date=statement_date,
                expected_amount=Decimal(str(expected_amount)),
                actual_amount=Decimal(str(actual_amount)),
                variance_json=variance_details,
                status="VARIANCE" if abs(variance) > 0.01 else "RECONCILED",
            )
            db.session.add(batch)
        else:
            batch.expected_amount = Decimal(str(expected_amount))
            batch.actual_amount = Decimal(str(actual_amount))
            batch.variance_json = variance_details
            batch.status = "VARIANCE" if abs(variance) > 0.01 else "RECONCILED"
            batch.updated_at = datetime.utcnow()

        db.session.commit()

        return {
            "success": True,
            "batch_id": batch.id,
            "provider": provider,
            "date": statement_date.isoformat(),
            "expected_amount": expected_amount,
            "actual_amount": actual_amount,
            "variance": float(variance),
            "variance_percent": variance_percent,
            "expected_count": expected_count,
            "actual_count": actual_count,
            "matched_count": len(matched),
            "unmatched_internal_count": len(unmatched_internal),
            "unmatched_provider_count": len(unmatched_provider),
            "status": batch.status,
            "details": variance_details,
        }

    def get_reconciliation_report(
        self, provider: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get reconciliation reports"""
        query = SettlementBatch.query

        if provider:
            query = query.filter(SettlementBatch.provider == provider.upper())

        if start_date:
            query = query.filter(SettlementBatch.settlement_date >= start_date)

        if end_date:
            query = query.filter(SettlementBatch.settlement_date <= end_date)

        batches = query.order_by(SettlementBatch.settlement_date.desc()).all()

        return {
            "success": True,
            "batches": [b.to_dict() for b in batches],
            "total_count": len(batches),
            "variance_count": len([b for b in batches if b.status == "VARIANCE"]),
        }

