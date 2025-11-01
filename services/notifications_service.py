"""
Notifications service: push and SMS stubs for key events
"""

from services.sms_service import SMSService


class NotificationsService:
    def __init__(self):
        self.sms = SMSService()

    def notify_contribution_success(self, phone: str, amount: str):
        if not phone:
            return
        self.sms.send_sms(phone, f"Contribution successful: {amount}")

    def notify_contribution_failed(self, phone: str, reason: str):
        if not phone:
            return
        self.sms.send_sms(phone, f"Contribution failed: {reason}")
