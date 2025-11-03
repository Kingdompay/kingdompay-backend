"""
Migration: Add owner_type and owner_id fields to wallets table
Run: flask db migrate -m "Add wallet owner_type and owner_id"
"""

from flask import current_app
from extensions import db


def upgrade_wallet_table():
    """Add owner_type and owner_id columns to wallets table"""
    try:
        # Check if columns exist
        inspector = db.inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("wallets")]

        if "owner_type" not in columns:
            db.session.execute(
                db.text("ALTER TABLE wallets ADD COLUMN owner_type VARCHAR(20) DEFAULT 'USER' NOT NULL")
            )
            current_app.logger.info("Added owner_type column")

        if "owner_id" not in columns:
            db.session.execute(
                db.text("ALTER TABLE wallets ADD COLUMN owner_id INTEGER DEFAULT 0 NOT NULL")
            )
            current_app.logger.info("Added owner_id column")

            # Update existing wallets to set owner_id = user_id
            db.session.execute(
                db.text("UPDATE wallets SET owner_id = user_id WHERE user_id IS NOT NULL")
            )
            current_app.logger.info("Updated existing wallet owner_id values")

        # Make user_id nullable (for system/community wallets)
        # sqlite doesn't support ALTER COLUMN DROP NOT NULL; ignore if fails
        try:
            db.session.execute(db.text("ALTER TABLE wallets ALTER COLUMN user_id DROP NOT NULL"))
        except Exception:
            pass
        current_app.logger.info("Made user_id nullable")

        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        upgrade_wallet_table()
