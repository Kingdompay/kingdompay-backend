#!/usr/bin/env python3
"""
Simplified KingdomPay Simulation Test
Tests core functionality and identifies key issues
"""

import os
import time
import json
import random
import statistics
from datetime import datetime
from decimal import Decimal
from app import create_app
from extensions import db
from models import User, Wallet, Transaction, OTPVerification


class SimpleKingdomPaySimulator:
    """Simplified simulation test for KingdomPay"""

    def __init__(self):
        self.app = None
        self.results = {
            "test_summary": {},
            "performance_metrics": {},
            "error_analysis": {},
            "recommendations": [],
        }
        self.setup_app()

    def setup_app(self):
        """Setup test application"""
        os.environ["TESTING"] = "true"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"
        os.environ["ENCRYPTION_KEY"] = "test-encryption-key-32-bytes-long"

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["JWT_SECRET_KEY"] = "test-jwt-secret-key"
        self.app.config["SECRET_KEY"] = "test-secret-key"

        with self.app.app_context():
            db.create_all()

    def test_basic_functionality(self):
        """Test basic application functionality"""
        print("... Testing basic functionality...")

        start_time = time.time()
        tests_passed = 0
        tests_failed = 0
        test_results = []

        with self.app.app_context():
            # Test 1: User Creation
            try:
                user = User(
                    full_name="Test User",
                    phone_number="+254712345678",
                    email="test@example.com",
                    is_phone_verified=True,
                    is_active=True,
                )
                db.session.add(user)
                db.session.flush()

                wallet = Wallet(user_id=user.id)
                db.session.add(wallet)
                db.session.commit()

                test_results.append(
                    {
                        "test": "User Creation",
                        "status": "PASS",
                        "time": time.time() - start_time,
                    }
                )
                tests_passed += 1
                print("[OK] User creation test passed")

            except Exception as e:
                test_results.append(
                    {"test": "User Creation", "status": "FAIL", "error": str(e)}
                )
                tests_failed += 1
                print(f"[FAIL] User creation test failed: {str(e)}")
                db.session.rollback()

            # Test 2: Transaction Creation
            try:
                transaction = Transaction(
                    destination_wallet_id=wallet.id,
                    transaction_type="DEPOSIT",
                    amount=Decimal("100.00"),
                    destination_balance_after=Decimal("100.00"),
                    status="SUCCESS",
                    description="Test deposit",
                )
                db.session.add(transaction)
                db.session.commit()

                test_results.append(
                    {
                        "test": "Transaction Creation",
                        "status": "PASS",
                        "time": time.time() - start_time,
                    }
                )
                tests_passed += 1
                print("[OK] Transaction creation test passed")

            except Exception as e:
                test_results.append(
                    {"test": "Transaction Creation", "status": "FAIL", "error": str(e)}
                )
                tests_failed += 1
                print(f"[FAIL] Transaction creation test failed: {str(e)}")
                db.session.rollback()

            # Test 3: OTP Generation
            try:
                otp = OTPVerification.generate_otp("+254712345679")
                db.session.commit()

                test_results.append(
                    {
                        "test": "OTP Generation",
                        "status": "PASS",
                        "time": time.time() - start_time,
                    }
                )
                tests_passed += 1
                print("[OK] OTP generation test passed")

            except Exception as e:
                test_results.append(
                    {"test": "OTP Generation", "status": "FAIL", "error": str(e)}
                )
                tests_failed += 1
                print(f"[FAIL] OTP generation test failed: {str(e)}")
                db.session.rollback()

        end_time = time.time()
        total_time = end_time - start_time

        self.results["test_summary"] = {
            "total_tests": tests_passed + tests_failed,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "success_rate": (
                (tests_passed / (tests_passed + tests_failed)) * 100
                if (tests_passed + tests_failed) > 0
                else 0
            ),
            "total_time": total_time,
            "test_results": test_results,
        }

        return tests_passed, tests_failed

    def test_api_endpoints(self):
        """Test API endpoints"""
        print("... Testing API endpoints...")

        start_time = time.time()
        success_count = 0
        error_count = 0
        response_times = []

        with self.app.test_client() as client:
            with self.app.app_context():
                # Create test user
                user = User(
                    full_name="API Test User",
                    phone_number="+254712345680",
                    is_phone_verified=True,
                    is_active=True,
                )
                db.session.add(user)
                db.session.flush()

                wallet = Wallet(user_id=user.id, balance=1000.0)
                db.session.add(wallet)
                db.session.commit()

                # Generate auth token
                from flask_jwt_extended import create_access_token

                access_token = create_access_token(identity=str(user.id))
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }

                # Test endpoints
                endpoints = [
                    ("/health", "GET", None),
                    ("/api/v1/auth/me", "GET", None),
                    ("/api/v1/wallets/balance", "GET", None),
                    ("/api/v1/wallets/transactions", "GET", None),
                    (
                        "/api/v1/wallets/deposit",
                        "POST",
                        {"amount": 100.0, "description": "Test deposit"},
                    ),
                ]

                for endpoint, method, data in endpoints:
                    try:
                        req_start = time.time()

                        if method == "GET":
                            response = client.get(endpoint, headers=headers)
                        elif method == "POST":
                            response = client.post(endpoint, headers=headers, json=data)

                        req_end = time.time()
                        response_times.append(req_end - req_start)

                        if response.status_code in [200, 201]:
                            success_count += 1
                            print(f"[OK] {endpoint} - {response.status_code}")
                        else:
                            error_count += 1
                            print(f"[FAIL] {endpoint} - {response.status_code}")

                    except Exception as e:
                        error_count += 1
                        print(f"[FAIL] {endpoint} - Error: {str(e)}")

        end_time = time.time()
        total_time = end_time - start_time

        self.results["performance_metrics"]["api_endpoints"] = {
            "total_requests": success_count + error_count,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": (
                (success_count / (success_count + error_count)) * 100
                if (success_count + error_count) > 0
                else 0
            ),
            "total_time": total_time,
            "avg_response_time": (
                statistics.mean(response_times) if response_times else 0
            ),
            "response_times": response_times,
        }

        return success_count, error_count

    def test_database_performance(self):
        """Test database performance"""
        print("... Testing database performance...")

        start_time = time.time()
        operations_count = 0
        error_count = 0

        with self.app.app_context():
            # Test bulk operations
            users = []
            wallets = []
            transactions = []

            try:
                # Create multiple users
                for i in range(50):
                    user = User(
                        full_name=f"Perf Test User {i}",
                        phone_number=f"+2547{random.randint(10000000, 99999999)}",
                        email=f"perf{i}@test.com",
                        is_phone_verified=True,
                        is_active=True,
                    )
                    users.append(user)
                    db.session.add(user)

                db.session.flush()
                operations_count += 50

                # Create wallets
                for user in users:
                    wallet = Wallet(user_id=user.id, balance=random.uniform(100, 1000))
                    wallets.append(wallet)
                    db.session.add(wallet)

                db.session.flush()
                operations_count += 50

                # Create transactions
                for i in range(100):
                    wallet = random.choice(wallets)
                    amount = Decimal(str(random.uniform(10, 100)))
                    wallet.balance += amount

                    transaction = Transaction(
                        destination_wallet_id=wallet.id,
                        transaction_type="DEPOSIT",
                        amount=amount,
                        destination_balance_after=wallet.balance,
                        status="SUCCESS",
                        description=f"Perf test transaction {i}",
                    )
                    transactions.append(transaction)
                    db.session.add(transaction)

                db.session.commit()
                operations_count += 100

                # Test queries
                user_count = User.query.count()
                wallet_count = Wallet.query.count()
                transaction_count = Transaction.query.count()

                operations_count += 3

                print(
                    f"[OK] Database performance test completed: {operations_count} operations"
                )

            except Exception as e:
                error_count += 1
                print(f"[FAIL] Database performance test failed: {str(e)}")
                db.session.rollback()

        end_time = time.time()
        total_time = end_time - start_time

        self.results["performance_metrics"]["database_performance"] = {
            "total_operations": operations_count,
            "error_count": error_count,
            "total_time": total_time,
            "operations_per_second": (
                operations_count / total_time if total_time > 0 else 0
            ),
            "success_rate": (
                ((operations_count - error_count) / operations_count) * 100
                if operations_count > 0
                else 0
            ),
        }

        return operations_count, error_count

    def test_error_scenarios(self):
        """Test error scenarios"""
        print("... Testing error scenarios...")

        error_tests = []

        with self.app.app_context():
            # Test 1: Invalid phone number
            try:
                from services.auth_service import AuthService

                auth_service = AuthService()
                result = auth_service.send_otp("invalid_phone")
                if not result["success"]:
                    error_tests.append(
                        {
                            "test": "Invalid Phone Number",
                            "status": "PASS",
                            "expected": "Should fail",
                        }
                    )
                else:
                    error_tests.append(
                        {
                            "test": "Invalid Phone Number",
                            "status": "FAIL",
                            "expected": "Should fail",
                        }
                    )
            except Exception as e:
                error_tests.append(
                    {"test": "Invalid Phone Number", "status": "ERROR", "error": str(e)}
                )

            # Test 2: Insufficient funds
            try:
                user = User(
                    full_name="Error Test User",
                    phone_number="+254712345681",
                    is_phone_verified=True,
                    is_active=True,
                )
                db.session.add(user)
                db.session.flush()

                wallet = Wallet(user_id=user.id, balance=50.0)
                db.session.add(wallet)
                db.session.commit()

                # Try to withdraw more than balance
                try:
                    wallet.deduct_funds(100.0, "Test withdrawal")
                    error_tests.append(
                        {
                            "test": "Insufficient Funds",
                            "status": "FAIL",
                            "expected": "Should fail",
                        }
                    )
                except ValueError as e:
                    if "Insufficient funds" in str(e):
                        error_tests.append(
                            {
                                "test": "Insufficient Funds",
                                "status": "PASS",
                                "expected": "Should fail",
                            }
                        )
                    else:
                        error_tests.append(
                            {
                                "test": "Insufficient Funds",
                                "status": "FAIL",
                                "expected": "Should fail",
                            }
                        )

            except Exception as e:
                error_tests.append(
                    {"test": "Insufficient Funds", "status": "ERROR", "error": str(e)}
                )
                db.session.rollback()

        self.results["error_analysis"] = {
            "error_tests": error_tests,
            "total_tests": len(error_tests),
            "passed_tests": len([t for t in error_tests if t["status"] == "PASS"]),
            "failed_tests": len([t for t in error_tests if t["status"] == "FAIL"]),
            "error_tests": len([t for t in error_tests if t["status"] == "ERROR"]),
        }

        return len(error_tests)

    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        recommendations = []

        # Check basic functionality
        if self.results["test_summary"]["success_rate"] < 100:
            recommendations.append("Fix failing basic functionality tests")

        # Check API performance
        if "api_endpoints" in self.results["performance_metrics"]:
            api_success_rate = self.results["performance_metrics"]["api_endpoints"][
                "success_rate"
            ]
            if api_success_rate < 100:
                recommendations.append("Investigate API endpoint failures")

            avg_response_time = self.results["performance_metrics"]["api_endpoints"][
                "avg_response_time"
            ]
            if avg_response_time > 0.1:  # 100ms
                recommendations.append(
                    "Optimize API response times - currently above 100ms"
                )

        # Check database performance
        if "database_performance" in self.results["performance_metrics"]:
            db_success_rate = self.results["performance_metrics"][
                "database_performance"
            ]["success_rate"]
            if db_success_rate < 100:
                recommendations.append("Review database operations for errors")

        # Check error handling
        if self.results["error_analysis"]["failed_tests"] > 0:
            recommendations.append("Improve error handling and validation")

        if not recommendations:
            recommendations.append("Overall system performance looks good!")

        self.results["recommendations"] = recommendations

    def run_simulation(self):
        """Run the complete simulation"""
        print("🚀 Starting KingdomPay Simulation...")
        print("=" * 60)

        # Run all tests
        self.test_basic_functionality()
        self.test_api_endpoints()
        self.test_database_performance()
        self.test_error_scenarios()

        # Generate recommendations
        self.generate_recommendations()

        # Generate report
        self.generate_report()

        print("=" * 60)
        print("[OK] Simulation completed!")

    def generate_report(self):
        """Generate simulation report"""
        print("\n SIMULATION REPORT")
        print("=" * 60)

        # Test Summary
        print("\n TEST SUMMARY:")
        summary = self.results["test_summary"]
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed: {summary['tests_passed']}")
        print(f"  Failed: {summary['tests_failed']}")
        print(f"  Success Rate: {summary['success_rate']:.1f}%")
        print(f"  Total Time: {summary['total_time']:.2f}s")

        # Performance Metrics
        print("\n PERFORMANCE METRICS:")
        for test_name, metrics in self.results["performance_metrics"].items():
            print(f"\n{test_name.upper()}:")
            if "success_rate" in metrics:
                print(f"  Success Rate: {metrics['success_rate']:.1f}%")
            if "avg_response_time" in metrics:
                print(f"  Avg Response Time: {metrics['avg_response_time']:.4f}s")
            if "operations_per_second" in metrics:
                print(f"  Operations/sec: {metrics['operations_per_second']:.2f}")

        # Error Analysis
        print("\n🔍 ERROR ANALYSIS:")
        error_analysis = self.results["error_analysis"]
        print(f"  Error Tests: {error_analysis['total_tests']}")
        print(f"  Passed: {error_analysis['passed_tests']}")
        print(f"  Failed: {error_analysis['failed_tests']}")

        # Recommendations
        print("\n RECOMMENDATIONS:")
        for i, rec in enumerate(self.results["recommendations"], 1):
            print(f"  {i}. {rec}")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"simulation_results_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\n📁 Detailed results saved to: {filename}")


def main():
    """Main simulation function"""
    simulator = SimpleKingdomPaySimulator()
    simulator.run_simulation()


if __name__ == "__main__":
    main()
