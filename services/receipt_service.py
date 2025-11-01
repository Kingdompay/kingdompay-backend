"""
ReceiptService: generate simple receipt payloads and trigger delivery via email/SMS
"""

from datetime import datetime
from typing import Optional, Dict, Any
from flask import current_app
from models.ledger_journal import LedgerJournal
from models.campaign import Campaign
from models.wallet import Wallet
from extensions import db
from services.sms_service import SMSService
from flask_mail import Message
from extensions import mail


class ReceiptService:
    def __init__(self):
        self.sms = SMSService()

    def build_receipt(
        self, *, journal_id: int, campaign: Optional[Campaign] = None
    ) -> Dict[str, Any]:
        journal = LedgerJournal.query.get(journal_id)
        if not journal:
            raise ValueError("Journal not found")
        # Minimal receipt content
        return {
            "journal_id": journal.id,
            "description": journal.description,
            "external_ref": journal.external_ref,
            "created_at": (
                journal.created_at.isoformat() if journal.created_at else None
            ),
            "campaign_id": campaign.id if campaign else None,
        }

    def send_email_receipt(self, to_email: str, subject: str, body: str):
        try:
            msg = Message(subject=subject, recipients=[to_email], body=body)
            mail.send(msg)
        except Exception:
            current_app.logger.exception("Failed sending email receipt")

    def send_sms_receipt(self, phone: str, body: str):
        try:
            self.sms.send_sms(phone, body)
        except Exception:
            current_app.logger.exception("Failed sending SMS receipt")
