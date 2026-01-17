"""
Notification Service for KingdomPay
Handles push notifications, in-app notifications, and email alerts
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from extensions import db, redis_client

logger = logging.getLogger(__name__)


class NotificationType:
    """Notification types"""
    TRANSACTION = "transaction"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER_SENT = "transfer_sent"
    TRANSFER_RECEIVED = "transfer_received"
    KYC_APPROVED = "kyc_approved"
    KYC_REJECTED = "kyc_rejected"
    COMMUNITY_INVITE = "community_invite"
    CAMPAIGN_CONTRIBUTION = "campaign_contribution"
    SYSTEM = "system"


class Notification(db.Model):
    """In-app notification model"""
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    data = db.Column(db.JSON)  # Additional data (transaction_id, etc.)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    read_at = db.Column(db.DateTime(timezone=True))

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }


class NotificationService:
    """Service for managing notifications"""

    def __init__(self):
        self.fcm_server_key = os.environ.get("FCM_SERVER_KEY")
        self.push_enabled = bool(self.fcm_server_key)

    def create_notification(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        send_push: bool = True
    ) -> Dict[str, Any]:
        """
        Create an in-app notification and optionally send push notification
        """
        try:
            # Create in-app notification
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                title=title,
                message=message,
                data=data
            )
            db.session.add(notification)
            db.session.commit()

            # Send push notification if enabled
            if send_push and self.push_enabled:
                self._send_push_notification(user_id, title, message, data)

            # Publish to Redis for real-time updates
            self._publish_notification(user_id, notification.to_dict())

            return {"success": True, "notification": notification.to_dict()}
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            db.session.rollback()
            return {"success": False, "error": str(e)}

    def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        query = Notification.query.filter_by(user_id=user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        notifications = query.order_by(Notification.created_at.desc())\
            .offset(offset).limit(limit).all()
        
        return [n.to_dict() for n in notifications]

    def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications"""
        return Notification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).count()

    def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """Mark a notification as read"""
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=user_id
        ).first()
        
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user"""
        count = Notification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow()
        })
        db.session.commit()
        return count

    def _send_push_notification(
        self,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """Send push notification via FCM"""
        if not self.fcm_server_key:
            logger.warning("FCM not configured, skipping push notification")
            return

        try:
            # Get user's FCM token from Redis or database
            fcm_token = self._get_user_fcm_token(user_id)
            if not fcm_token:
                logger.debug(f"No FCM token for user {user_id}")
                return

            import requests
            
            headers = {
                "Authorization": f"key={self.fcm_server_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "to": fcm_token,
                "notification": {
                    "title": title,
                    "body": body,
                    "sound": "default"
                },
                "data": data or {}
            }
            
            response = requests.post(
                "https://fcm.googleapis.com/fcm/send",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Push notification sent to user {user_id}")
            else:
                logger.error(f"FCM error: {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")

    def _get_user_fcm_token(self, user_id: int) -> Optional[str]:
        """Get user's FCM token"""
        try:
            token = redis_client.get(f"fcm_token:{user_id}")
            return token.decode() if token else None
        except Exception:
            return None

    def register_fcm_token(self, user_id: int, fcm_token: str) -> bool:
        """Register user's FCM token for push notifications"""
        try:
            redis_client.set(f"fcm_token:{user_id}", fcm_token)
            return True
        except Exception as e:
            logger.error(f"Failed to register FCM token: {e}")
            return False

    def _publish_notification(self, user_id: int, notification: Dict[str, Any]):
        """Publish notification to Redis for real-time updates"""
        try:
            redis_client.publish(
                f"notifications:{user_id}",
                json.dumps(notification)
            )
        except Exception as e:
            logger.debug(f"Failed to publish notification: {e}")

    # ═══════════════════════════════════════════════════════════════════════
    #                    TRANSACTION NOTIFICATION HELPERS
    # ═══════════════════════════════════════════════════════════════════════

    def notify_deposit(self, user_id: int, amount: float, balance: float, reference: str = None):
        """Notify user of successful deposit"""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.DEPOSIT,
            title="Deposit Received",
            message=f"KES {amount:,.2f} has been deposited to your wallet. New balance: KES {balance:,.2f}",
            data={"amount": amount, "balance": balance, "reference": reference}
        )

    def notify_withdrawal(self, user_id: int, amount: float, balance: float, phone: str = None):
        """Notify user of successful withdrawal"""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.WITHDRAWAL,
            title="Withdrawal Successful",
            message=f"KES {amount:,.2f} has been sent to {phone or 'your M-Pesa'}. New balance: KES {balance:,.2f}",
            data={"amount": amount, "balance": balance, "phone": phone}
        )

    def notify_transfer_sent(self, user_id: int, amount: float, recipient_name: str, balance: float):
        """Notify sender of successful transfer"""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.TRANSFER_SENT,
            title="Transfer Sent",
            message=f"KES {amount:,.2f} sent to {recipient_name}. New balance: KES {balance:,.2f}",
            data={"amount": amount, "recipient": recipient_name, "balance": balance}
        )

    def notify_transfer_received(self, user_id: int, amount: float, sender_name: str, balance: float):
        """Notify recipient of received transfer"""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.TRANSFER_RECEIVED,
            title="Money Received",
            message=f"You received KES {amount:,.2f} from {sender_name}. New balance: KES {balance:,.2f}",
            data={"amount": amount, "sender": sender_name, "balance": balance}
        )

    def notify_kyc_status(self, user_id: int, status: str, tier: str = None, reason: str = None):
        """Notify user of KYC status change"""
        if status == "approved":
            return self.create_notification(
                user_id=user_id,
                notification_type=NotificationType.KYC_APPROVED,
                title="KYC Approved",
                message=f"Your KYC verification has been approved. You are now at {tier or 'Tier 1'}.",
                data={"status": status, "tier": tier}
            )
        else:
            return self.create_notification(
                user_id=user_id,
                notification_type=NotificationType.KYC_REJECTED,
                title="KYC Requires Attention",
                message=f"Your KYC verification requires attention: {reason or 'Please review your documents.'}",
                data={"status": status, "reason": reason}
            )
