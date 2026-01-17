"""
Scheduled/Recurring Payment Service for KingdomPay
Handles automated recurring payments and transfers
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from enum import Enum
from extensions import db

logger = logging.getLogger(__name__)


class ScheduleFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ScheduledPayment(db.Model):
    """Scheduled/recurring payment model"""
    __tablename__ = "scheduled_payments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    recipient_wallet_id = db.Column(db.Integer, db.ForeignKey("wallets.id"))
    recipient_phone = db.Column(db.String(20))  # For external payments
    
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(3), default="KES")
    description = db.Column(db.String(255))
    
    frequency = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, etc.
    next_run = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    last_run = db.Column(db.DateTime(timezone=True))
    end_date = db.Column(db.DateTime(timezone=True))  # Optional end date
    
    is_active = db.Column(db.Boolean, default=True)
    run_count = db.Column(db.Integer, default=0)
    max_runs = db.Column(db.Integer)  # Optional max number of runs
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "recipient_wallet_id": self.recipient_wallet_id,
            "recipient_phone": self.recipient_phone,
            "amount": float(self.amount),
            "currency": self.currency,
            "description": self.description,
            "frequency": self.frequency,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_active": self.is_active,
            "run_count": self.run_count,
            "max_runs": self.max_runs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScheduledPaymentService:
    """Service for managing scheduled payments"""

    def create_scheduled_payment(
        self,
        user_id: int,
        amount: Decimal,
        frequency: str,
        recipient_wallet_id: int = None,
        recipient_phone: str = None,
        description: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        max_runs: int = None
    ) -> Dict[str, Any]:
        """Create a new scheduled payment"""
        try:
            # Validate frequency
            try:
                freq = ScheduleFrequency(frequency.lower())
            except ValueError:
                return {"error": f"Invalid frequency. Must be one of: {[f.value for f in ScheduleFrequency]}"}

            # Validate recipient
            if not recipient_wallet_id and not recipient_phone:
                return {"error": "Either recipient_wallet_id or recipient_phone is required"}

            # Calculate first run date
            first_run = start_date or datetime.utcnow()
            
            scheduled = ScheduledPayment(
                user_id=user_id,
                recipient_wallet_id=recipient_wallet_id,
                recipient_phone=recipient_phone,
                amount=amount,
                description=description,
                frequency=freq.value,
                next_run=first_run,
                end_date=end_date,
                max_runs=max_runs
            )
            
            db.session.add(scheduled)
            db.session.commit()

            return {"success": True, "scheduled_payment": scheduled.to_dict()}
        except Exception as e:
            logger.error(f"Failed to create scheduled payment: {e}")
            db.session.rollback()
            return {"error": str(e)}

    def get_user_scheduled_payments(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get scheduled payments for a user"""
        query = ScheduledPayment.query.filter_by(user_id=user_id)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        payments = query.order_by(ScheduledPayment.next_run).all()
        return [p.to_dict() for p in payments]

    def cancel_scheduled_payment(self, payment_id: int, user_id: int) -> bool:
        """Cancel a scheduled payment"""
        payment = ScheduledPayment.query.filter_by(
            id=payment_id,
            user_id=user_id
        ).first()
        
        if payment:
            payment.is_active = False
            db.session.commit()
            return True
        return False

    def update_scheduled_payment(
        self,
        payment_id: int,
        user_id: int,
        **updates
    ) -> Dict[str, Any]:
        """Update a scheduled payment"""
        payment = ScheduledPayment.query.filter_by(
            id=payment_id,
            user_id=user_id
        ).first()
        
        if not payment:
            return {"error": "Scheduled payment not found"}

        allowed_updates = ["amount", "description", "frequency", "end_date", "max_runs", "is_active"]
        
        for key, value in updates.items():
            if key in allowed_updates and value is not None:
                setattr(payment, key, value)

        db.session.commit()
        return {"success": True, "scheduled_payment": payment.to_dict()}

    def get_due_payments(self) -> List[ScheduledPayment]:
        """Get all payments due for processing"""
        now = datetime.utcnow()
        return ScheduledPayment.query.filter(
            ScheduledPayment.is_active == True,
            ScheduledPayment.next_run <= now
        ).all()

    def process_payment(self, payment: ScheduledPayment) -> Dict[str, Any]:
        """Process a scheduled payment"""
        try:
            from models.wallet import Wallet
            from services.transfer_service import TransferService
            
            transfer_service = TransferService()
            
            # Get source wallet
            source_wallet = Wallet.query.filter_by(user_id=payment.user_id).first()
            if not source_wallet:
                return {"error": "Source wallet not found"}

            # Check balance
            if source_wallet.balance < payment.amount:
                return {"error": "Insufficient balance"}

            # Perform transfer
            if payment.recipient_wallet_id:
                result = transfer_service.transfer(
                    source_wallet_id=source_wallet.id,
                    destination_wallet_id=payment.recipient_wallet_id,
                    amount=payment.amount,
                    description=f"Scheduled: {payment.description or 'Recurring payment'}"
                )
            else:
                # External payment (M-Pesa)
                from services.providers.mpesa.b2c import MpesaB2C
                b2c = MpesaB2C()
                result = b2c.initiate_payout(
                    phone=payment.recipient_phone,
                    amount=payment.amount,
                    remarks=payment.description or "Scheduled payment"
                )

            # Update payment record
            payment.last_run = datetime.utcnow()
            payment.run_count += 1
            payment.next_run = self._calculate_next_run(payment)
            
            # Check if should be deactivated
            if payment.max_runs and payment.run_count >= payment.max_runs:
                payment.is_active = False
            if payment.end_date and payment.next_run > payment.end_date:
                payment.is_active = False

            db.session.commit()
            return result

        except Exception as e:
            logger.error(f"Failed to process scheduled payment {payment.id}: {e}")
            return {"error": str(e)}

    def _calculate_next_run(self, payment: ScheduledPayment) -> datetime:
        """Calculate the next run date based on frequency"""
        current = payment.next_run or datetime.utcnow()
        
        frequency_deltas = {
            ScheduleFrequency.DAILY.value: timedelta(days=1),
            ScheduleFrequency.WEEKLY.value: timedelta(weeks=1),
            ScheduleFrequency.BIWEEKLY.value: timedelta(weeks=2),
            ScheduleFrequency.MONTHLY.value: timedelta(days=30),  # Approximate
            ScheduleFrequency.QUARTERLY.value: timedelta(days=90),
            ScheduleFrequency.YEARLY.value: timedelta(days=365),
        }
        
        delta = frequency_deltas.get(payment.frequency, timedelta(days=30))
        return current + delta
