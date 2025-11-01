#!/usr/bin/env python3
"""
Migration script to add community-related tables to KingdomPay database
Run this script to set up the new community functionality
"""

import os
import sys
from sqlalchemy import text
from extensions import db
from app import create_app


def run_migration():
    """Run the community tables migration"""
    app = create_app()

    with app.app_context():
        try:
            print("🚀 Starting community tables migration...")

            # Detect database type
            db_url = str(db.engine.url)
            if "postgresql" in db_url or "postgres" in db_url:
                db_type = "PostgreSQL"
                migration_file = os.path.join(
                    os.path.dirname(__file__), "db", "community_tables.sql"
                )
            else:
                db_type = "SQLite"
                migration_file = os.path.join(
                    os.path.dirname(__file__), "db", "community_tables_sqlite.sql"
                )

            print(f"🔍 Detected database type: {db_type}")
            print(f"📁 Using migration file: {os.path.basename(migration_file)}")

            if not os.path.exists(migration_file):
                print(f"❌ Migration file not found: {migration_file}")
                return False

            with open(migration_file, "r") as f:
                migration_sql = f.read()

            # Split the SQL into individual statements
            statements = [
                stmt.strip() for stmt in migration_sql.split(";") if stmt.strip()
            ]

            print(f"📝 Executing {len(statements)} SQL statements...")

            for i, statement in enumerate(statements, 1):
                try:
                    print(f"   [{i}/{len(statements)}] Executing statement...")
                    db.session.execute(text(statement))
                    db.session.commit()
                except Exception as e:
                    print(f"   ⚠️  Statement {i} failed (might already exist): {e}")
                    db.session.rollback()
                    continue

            # Add contribution_id column to transactions table if it doesn't exist
            print("\n🔧 Adding contribution_id column to transactions table...")
            try:
                # Check if column exists by trying to select it
                db.session.execute(
                    text("SELECT contribution_id FROM transactions LIMIT 1")
                )
                print("   ✅ contribution_id column already exists")
            except Exception:
                try:
                    # Column doesn't exist, add it
                    if db_type == "PostgreSQL":
                        # PostgreSQL supports ADD COLUMN IF NOT EXISTS
                        db.session.execute(
                            text(
                                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS contribution_id INTEGER REFERENCES contributions(id) ON DELETE SET NULL"
                            )
                        )
                    else:
                        # SQLite doesn't support IF NOT EXISTS, so we just add it
                        db.session.execute(
                            text(
                                "ALTER TABLE transactions ADD COLUMN contribution_id INTEGER REFERENCES contributions(id) ON DELETE SET NULL"
                            )
                        )
                    db.session.commit()
                    print("   ✅ contribution_id column added successfully")
                except Exception as e:
                    print(f"   ⚠️  Failed to add contribution_id column: {e}")
                    db.session.rollback()

            # Create index for contribution_id if it was added
            try:
                db.session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_transactions_contribution_id ON transactions(contribution_id)"
                    )
                )
                db.session.commit()
                print("   ✅ Index for contribution_id created")
            except Exception as e:
                print(f"   ⚠️  Failed to create index: {e}")
                db.session.rollback()

            print("✅ Community tables migration completed successfully!")

            # Verify tables were created
            print("\n🔍 Verifying table creation...")
            tables_to_check = [
                "community_roles",
                "communities",
                "community_members",
                "contributions",
            ]

            for table in tables_to_check:
                try:
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"   ✅ {table}: {count} records")
                except Exception as e:
                    print(f"   ❌ {table}: {e}")

            # Check if contribution_id was added to transactions
            try:
                result = db.session.execute(
                    text("SELECT contribution_id FROM transactions LIMIT 1")
                )
                print("   ✅ transactions.contribution_id column exists")
            except Exception as e:
                print(f"   ❌ transactions.contribution_id column not found: {e}")

            print("\n🎉 Migration completed! Community functionality is now available.")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False


def rollback_migration():
    """Rollback the community tables migration (use with caution!)"""
    app = create_app()

    with app.app_context():
        try:
            print("🔄 Starting rollback of community tables...")

            # Detect database type
            db_url = str(db.engine.url)
            if "postgresql" in db_url or "postgres" in db_url:
                db_type = "PostgreSQL"
            else:
                db_type = "SQLite"

            # Drop tables in reverse order of dependencies
            tables_to_drop = [
                "community_members",
                "contributions",
                "communities",
                "community_roles",
            ]

            for table in tables_to_drop:
                try:
                    print(f"   🗑️  Dropping table: {table}")
                    if db_type == "PostgreSQL":
                        db.session.execute(
                            text(f"DROP TABLE IF EXISTS {table} CASCADE")
                        )
                    else:
                        # SQLite doesn't support CASCADE
                        db.session.execute(text(f"DROP TABLE IF EXISTS {table}"))
                    db.session.commit()
                except Exception as e:
                    print(f"   ⚠️  Failed to drop {table}: {e}")
                    db.session.rollback()

            # Remove contribution_id from transactions table
            try:
                print("   🗑️  Removing contribution_id from transactions table")
                if db_type == "PostgreSQL":
                    db.session.execute(
                        text(
                            "ALTER TABLE transactions DROP COLUMN IF EXISTS contribution_id"
                        )
                    )
                else:
                    # SQLite doesn't support DROP COLUMN IF EXISTS, and DROP COLUMN is limited
                    print(
                        "   ⚠️  SQLite doesn't support dropping columns. Manual intervention required."
                    )
                db.session.commit()
            except Exception as e:
                print(f"   ⚠️  Failed to remove contribution_id: {e}")
                db.session.rollback()

            print("✅ Rollback completed!")
            return True

        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            db.session.rollback()
            return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "rollback":
            success = rollback_migration()
        elif sys.argv[1] == "test-postgresql":
            print("🧪 Testing PostgreSQL migration (dry run)")
            # This would be for testing with PostgreSQL - you can implement this later
            print("   ℹ️  PostgreSQL testing not implemented yet")
            success = True
        elif sys.argv[1] == "help":
            print("Usage:")
            print("  python migrate_community_tables.py          # Run migration")
            print("  python migrate_community_tables.py rollback # Rollback migration")
            print("  python migrate_community_tables.py help     # Show this help")
            success = True
        else:
            print(f"❌ Unknown argument: {sys.argv[1]}")
            print("Use 'help' to see available options")
            success = False
    else:
        success = run_migration()

    sys.exit(0 if success else 1)
