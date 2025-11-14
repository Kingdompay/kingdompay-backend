#!/usr/bin/env python3
"""Create a test payment for webhook simulation"""
import sys
import os

# Add project root to path
sys.path.insert(0, '/app')

from app import create_app
from extensions import db
from models.payment import Payment

def main():
    if len(sys.argv) < 4:
        print("ERROR: Usage: create_test_payment.py <wallet_id> <amount> <checkout_id>")
        sys.exit(1)
    
    wallet_id = int(sys.argv[1])
    amount = float(sys.argv[2])
    checkout_id = sys.argv[3]
    
    app = create_app()
    with app.app_context():
        try:
            payment = Payment(
                payer_wallet_id=wallet_id,
                amount=amount,
                currency="KES",
                status="PENDING",
                method="MOMO",
                provider="MPESA",
                provider_ref=checkout_id
            )
            db.session.add(payment)
            db.session.commit()
            print(f"SUCCESS:{payment.id}:{checkout_id}", flush=True)
        except Exception as e:
            import traceback
            print(f"ERROR:{str(e)}", flush=True)
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    main()


