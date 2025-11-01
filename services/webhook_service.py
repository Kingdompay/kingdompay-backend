"""
WebhookService: enqueue and deliver signed webhook events (stub)
"""

import hmac
import hashlib
import json
import time
import requests
from typing import Dict, Any
from flask import current_app
from extensions import db
from models.webhook import Webhook, WebhookEvent


class WebhookService:
    def _sign(self, secret: str, payload: Dict[str, Any]) -> str:
        body = json.dumps(payload, separators=(",", ":")).encode()
        return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    def emit(self, event_type: str, payload: Dict[str, Any]):
        evt = WebhookEvent(event_type=event_type, payload=payload)
        db.session.add(evt)
        db.session.commit()
        return evt.id

    def deliver(self, event_id: int):
        evt = WebhookEvent.query.get(event_id)
        if not evt or evt.delivered:
            return
        hooks = Webhook.query.filter_by(status="ACTIVE").all()
        for hook in hooks:
            signature = self._sign(hook.secret, evt.payload)
            try:
                requests.post(
                    hook.url,
                    json=evt.payload,
                    headers={
                        "X-KingdomPay-Event": evt.event_type,
                        "X-KingdomPay-Signature": signature,
                    },
                    timeout=5,
                )
                # Best-effort; mark delivered if any succeed
                evt.delivered = True
            except Exception:
                current_app.logger.exception("Webhook delivery failed")
        db.session.commit()
