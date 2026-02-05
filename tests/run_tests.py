#!/usr/bin/env python3
"""
Test runner for KingdomPay backend
"""

import os
import sys
import subprocess
import argparse


def run_tests(test_path=None, verbose=False, coverage=False):
    """Run tests with pytest"""

    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["FLASK_ENV"] = "testing"

    # Build pytest command
    cmd = ["python3", "-m", "pytest"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(
            [
                "--cov=app",
                "--cov=api",
                "--cov=models",
                "--cov=services",
                "--cov-report=html",
            ]
        )

    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")

    # Add additional options
    cmd.extend(
        [
            "--tb=short",  # Shorter traceback format
            "--strict-markers",  # Strict marker checking
            "--disable-warnings",  # Disable warnings for cleaner output
        ]
    )

    print(f"Running command: {' '.join(cmd)}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 50)
        print("All tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 50)
        print("Tests failed!")
        return False
    except FileNotFoundError:
        print("pytest not found. Please install it with: pip install pytest pytest-cov")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run KingdomPay backend tests")
    parser.add_argument("--path", "-p", help="Specific test file or directory to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--coverage", "-c", action="store_true", help="Run with coverage report"
    )
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument(
        "--integration", action="store_true", help="Run only integration tests"
    )

    args = parser.parse_args()

    test_path = args.path

    if args.unit:
        test_path = "tests/test_models.py tests/test_auth.py tests/test_wallet.py tests/test_ledger_service.py"
    elif args.integration:
        test_path = "tests/test_integration.py"

    success = run_tests(test_path, args.verbose, args.coverage)

    if success:
        print("\n🎉 Test run completed successfully!")
        if args.coverage:
            print("Coverage report generated in htmlcov/index.html")
    else:
        print("\n💥 Test run failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
