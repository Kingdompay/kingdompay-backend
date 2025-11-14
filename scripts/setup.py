"""
Setup script for KingdomPay Flask application
Run this to initialize the database and start the application
"""

import os
import sys
from flask import Flask
from flask_migrate import init, migrate, upgrade
from app import create_app
from extensions import db


def setup_database():
    """Initialize database with tables"""
    print("🗄️  Setting up database...")

    app = create_app()

    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created")

        # Initialize Flask-Migrate (if not already done)
        try:
            init()
            print("✅ Flask-Migrate initialized")
        except Exception as e:
            print(f"ℹ️  Flask-Migrate already initialized: {e}")

        # Create initial migration
        try:
            migrate(message="Initial migration")
            print("✅ Initial migration created")
        except Exception as e:
            print(f"ℹ️  Migration already exists: {e}")

        # Apply migrations
        try:
            upgrade()
            print("✅ Migrations applied")
        except Exception as e:
            print(f"ℹ️  Migrations already applied: {e}")


def run_otp_cleanup():
    """Run OTP cleanup task"""
    print("🧹 Running OTP cleanup...")

    app = create_app()

    with app.app_context():
        from services.auth_service import AuthService

        auth_service = AuthService()
        result = auth_service.cleanup_expired_otps()
        print(f"✅ Cleaned up {result['cleaned_count']} expired OTPs")


def main():
    """Main setup function"""
    print("🚀 KingdomPay Setup")
    print("=" * 30)

    # Check if we're in the right directory
    if not os.path.exists("app.py"):
        print("❌ Please run this script from the kingdompay-backend directory")
        sys.exit(1)

    # Setup database
    setup_database()

    # Run cleanup
    run_otp_cleanup()

    print("\n✅ Setup completed!")
    print("\nNext steps:")
    print("1. Start the database: cd db && docker-compose up -d")
    print("2. Start the application: python run.py")
    print("3. Test authentication: python test_auth.py")
    print("\nAPI will be available at: http://localhost:5000")


if __name__ == "__main__":
    main()
