#!/usr/bin/env python3
"""
PostgreSQL Connection Test Script
Tests database connectivity and configuration
"""

import sys
import os
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from config import Config
from sqlalchemy import text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")


def check_environment():
    """Check environment variables"""
    print_info("\n=== Checking Environment Configuration ===")

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        print_warning("DATABASE_URL not set - will default to SQLite")
        print_info("To use PostgreSQL, set DATABASE_URL environment variable")
        print_info(
            "Example: export DATABASE_URL='postgresql://user:pass@host:5432/dbname'"
        )
        return None

    print_success(f"DATABASE_URL is set")

    # Parse the URL
    try:
        parsed = urlparse(database_url)
        print_info(f"Database Type: {parsed.scheme}")
        print_info(f"Host: {parsed.hostname}")
        print_info(f"Port: {parsed.port or 'default'}")
        print_info(f"Database: {parsed.path.lstrip('/')}")
        print_info(f"User: {parsed.username}")

        if parsed.scheme in ["postgres", "postgresql"]:
            print_success("PostgreSQL URL detected")
            return database_url
        elif parsed.scheme == "sqlite":
            print_warning("SQLite URL detected (not PostgreSQL)")
            return None
        else:
            print_warning(f"Unknown database type: {parsed.scheme}")
            return None
    except Exception as e:
        print_error(f"Error parsing DATABASE_URL: {e}")
        return None


def test_connection(app):
    """Test database connection"""
    print_info("\n=== Testing Database Connection ===")

    with app.app_context():
        try:
            # Get database URI
            db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
            print_info(
                f"Database URI: {db_uri.split('@')[-1] if '@' in db_uri else db_uri}"
            )

            # Test basic connection
            print_info("Attempting to connect...")
            db.engine.connect()
            print_success("Connection successful!")

            # Test query
            print_info("Testing query execution...")
            result = db.session.execute(text("SELECT version()"))
            version = result.scalar()
            print_success(f"PostgreSQL version: {version}")

            # Get database name
            result = db.session.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print_success(f"Connected to database: {db_name}")

            # Get current user
            result = db.session.execute(text("SELECT current_user"))
            user = result.scalar()
            print_success(f"Connected as user: {user}")

            return True

        except OperationalError as e:
            print_error(f"Connection failed: {e}")
            print_info("\nTroubleshooting tips:")
            print_info("1. Check if PostgreSQL is running")
            print_info("2. Verify DATABASE_URL is correct")
            print_info("3. Check network connectivity")
            print_info("4. Verify user credentials")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            return False


def check_database_info(app):
    """Get database information"""
    print_info("\n=== Database Information ===")

    with app.app_context():
        try:
            # Get connection info
            inspector = inspect(db.engine)

            # Check if we can list tables
            tables = inspector.get_table_names()
            print_success(f"Database has {len(tables)} tables")

            if tables:
                print_info("Sample tables:")
                for table in tables[:10]:
                    print_info(f"  - {table}")
                if len(tables) > 10:
                    print_info(f"  ... and {len(tables) - 10} more")

            # Get database size
            try:
                result = db.session.execute(
                    text(
                        """
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """
                    )
                )
                size = result.scalar()
                print_success(f"Database size: {size}")
            except Exception as e:
                print_warning(f"Could not get database size: {e}")

            # Get connection count
            try:
                result = db.session.execute(
                    text(
                        """
                    SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()
                """
                    )
                )
                connections = result.scalar()
                print_success(f"Active connections: {connections}")
            except Exception as e:
                print_warning(f"Could not get connection count: {e}")

            return True

        except Exception as e:
            print_error(f"Error getting database info: {e}")
            return False


def test_queries(app):
    """Test various database operations"""
    print_info("\n=== Testing Database Operations ===")

    with app.app_context():
        try:
            # Test 1: Simple SELECT
            print_info("Test 1: Simple SELECT query...")
            result = db.session.execute(text("SELECT 1 as test"))
            value = result.scalar()
            if value == 1:
                print_success("SELECT query works")
            else:
                print_error("SELECT query returned unexpected value")
                return False

            # Test 2: Transaction
            print_info("Test 2: Transaction support...")
            # Use a savepoint for nested transaction test
            db.session.execute(text("SAVEPOINT test_sp"))
            db.session.execute(text("SELECT 1"))
            db.session.execute(text("ROLLBACK TO SAVEPOINT test_sp"))
            print_success("Transactions work")

            # Test 3: Check PostgreSQL extensions
            print_info("Test 3: Checking PostgreSQL extensions...")
            result = db.session.execute(
                text(
                    """
                SELECT extname, extversion 
                FROM pg_extension 
                ORDER BY extname
            """
                )
            )
            extensions = result.fetchall()
            if extensions:
                print_success(f"Found {len(extensions)} extensions:")
                for ext_name, ext_version in extensions:
                    print_info(f"  - {ext_name} (v{ext_version})")
            else:
                print_warning("No extensions found")

            return True

        except Exception as e:
            print_error(f"Error testing queries: {e}")
            import traceback

            traceback.print_exc()
            return False


def check_pool_settings(app):
    """Check connection pool settings"""
    print_info("\n=== Connection Pool Settings ===")

    with app.app_context():
        try:
            pool = db.engine.pool
            print_info(f"Pool size: {pool.size()}")
            print_info(f"Checked out: {pool.checkedout()}")
            print_info(f"Checked in: {pool.checkedin()}")
            print_info(f"Overflow: {pool.overflow()}")
            print_info(f"Invalid: {pool.invalid()}")

            # Get pool settings from config
            engine_options = app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {})
            if engine_options:
                print_info("Pool configuration:")
                if "pool_size" in engine_options:
                    print_info(f"  pool_size: {engine_options['pool_size']}")
                if "max_overflow" in engine_options:
                    print_info(f"  max_overflow: {engine_options['max_overflow']}")
                if "pool_recycle" in engine_options:
                    print_info(
                        f"  pool_recycle: {engine_options['pool_recycle']} seconds"
                    )

            return True

        except Exception as e:
            print_warning(f"Could not get pool info: {e}")
            return False


def main():
    """Run PostgreSQL connection tests"""
    print_info("=" * 60)
    print_info("PostgreSQL Connection Test")
    print_info("=" * 60)

    # Check environment
    db_url = check_environment()

    if not db_url:
        print_warning("\nNo PostgreSQL DATABASE_URL found")
        print_info("Current configuration will use SQLite")
        print_info("\nTo test PostgreSQL, set DATABASE_URL:")
        print_info(
            "  export DATABASE_URL='postgresql://user:password@localhost:5432/kingdompay'"
        )
        return 1

    # Create app
    app = create_app()

    # Test connection
    if not test_connection(app):
        return 1

    # Get database info
    check_database_info(app)

    # Test queries
    if not test_queries(app):
        return 1

    # Check pool settings
    check_pool_settings(app)

    print_info("\n" + "=" * 60)
    print_success("All PostgreSQL connection tests passed!")
    print_info("=" * 60)

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_error("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
