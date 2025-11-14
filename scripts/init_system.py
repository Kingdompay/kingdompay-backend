"""
Initialize system wallets and create an initial admin (optional).

Usage:
  FLASK_APP=app.py python3 scripts/init_system.py --admin-phone +2547xxxxxxx --admin-name "Staging Admin"
"""

import argparse
from app import create_app
from extensions import db
from services.wallet_service import WalletService
from models import User, Wallet


def main(admin_phone: str | None, admin_name: str | None):
  app = create_app()
  with app.app_context():
    # Ensure tables
    db.create_all()
    # Init system wallets
    WalletService.initialize_system_wallets()
    # Optionally create admin
    if admin_phone and admin_name:
      existing = User.find_by_phone(admin_phone)
      if not existing:
        user = User(full_name=admin_name, phone_number=admin_phone, is_phone_verified=True, is_active=True)
        db.session.add(user)
        db.session.flush()
        w = Wallet(user_id=user.id)
        db.session.add(w)
        db.session.commit()
        print(f"Created admin {admin_name} with wallet {w.display_number}")
      else:
        print("Admin already exists")
    print("System initialization complete")


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--admin-phone", type=str, default=None)
  parser.add_argument("--admin-name", type=str, default=None)
  args = parser.parse_args()
  main(args.admin_phone, args.admin_name)


