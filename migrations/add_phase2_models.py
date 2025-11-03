"""
Manual migration script for Phase 2 models
Run this after: flask db migrate -m "Phase 2 models"
"""

from extensions import db
from models import (
    TransactionFee,
    CommunityContribution,
    CommunityDevelopmentFund,
    MultiSigApproval,
    MultiSigSignature,
    Blacklist,
    AMLCase,
)

def create_tables():
    """Create all Phase 2 tables"""
    print("Creating Phase 2 tables...")
    
    try:
        db.create_all()
        print("✅ All tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

def verify_tables():
    """Verify Phase 2 tables exist"""
    from sqlalchemy import inspect
    
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    
    required_tables = [
        "transaction_fees",
        "community_contributions",
        "community_development_funds",
        "multisig_approvals",
        "multisig_signatures",
        "blacklists",
        "aml_cases",
    ]
    
    missing = [t for t in required_tables if t not in existing_tables]
    
    if missing:
        print(f"❌ Missing tables: {', '.join(missing)}")
        return False
    else:
        print("✅ All required tables exist")
        return True

if __name__ == "__main__":
    from app import create_app
    
    app = create_app()
    with app.app_context():
        create_tables()
        verify_tables()

