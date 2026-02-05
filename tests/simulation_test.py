#!/usr/bin/env python3
"""
Comprehensive simulation test for KingdomPay application
Tests efficiency, performance, and identifies potential issues
"""

import os
import time
import json
import random
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from decimal import Decimal
import requests
from app import create_app
from extensions import db
from models import (
    User,
    Wallet,
    Transaction,
    OTPVerification,
    Community,
    CommunityMember,
    Contribution,
)


class KingdomPaySimulator:
    """Comprehensive simulation test for KingdomPay"""

    def __init__(self):
        self.app = None
        self.results = {
            "performance_metrics": {},
            "error_analysis": {},
            "efficiency_tests": {},
            "load_test_results": {},
            "database_performance": {},
            "api_response_times": {},
            "memory_usage": {},
            "concurrent_operations": {},
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

    def simulate_user_registration_flow(self, num_users=100):
        """Simulate user registration and wallet creation"""
        print(f"... Simulating {num_users} user registrations...")

        start_time = time.time()
        success_count = 0
        error_count = 0
        response_times = []

        with self.app.app_context():
            for i in range(num_users):
                try:
                    user_start = time.time()

                    # Create user
                    phone_number = f"+2547{random.randint(10000000, 99999999)}"
                    user = User(
                        full_name=f"Test User {i}",
                        phone_number=phone_number,
                        email=f"user{i}@test.com",
                        is_phone_verified=True,
                        is_active=True,
                    )
                    db.session.add(user)
                    db.session.flush()

                    # Create wallet
                    wallet = Wallet(user_id=user.id)
                    db.session.add(wallet)
                    db.session.commit()

                    user_end = time.time()
                    response_times.append(user_end - user_start)
                    success_count += 1

                except Exception as e:
                    error_count += 1
                    print(f"[FAIL] Error creating user {i}: {str(e)}")

        end_time = time.time()
        total_time = end_time - start_time

        self.results["performance_metrics"]["user_registration"] = {
            "total_users": num_users,
            "success_count": success_count,
            "error_count": error_count,
            "total_time": total_time,
            "avg_time_per_user": total_time / num_users,
            "users_per_second": num_users / total_time,
            "response_times": {
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "avg": statistics.mean(response_times) if response_times else 0,
                "median": statistics.median(response_times) if response_times else 0,
            },
        }

        print(
            f"[OK] User registration simulation completed: {success_count}/{num_users} successful"
        )
        return success_count, error_count

    def simulate_transaction_operations(self, num_transactions=500):
        """Simulate various transaction operations"""
        print(f"... Simulating {num_transactions} transaction operations...")

        start_time = time.time()
        success_count = 0
        error_count = 0
        response_times = []

        with self.app.app_context():
            # Get existing users and wallets
            users = User.query.limit(50).all()
            wallets = Wallet.query.limit(50).all()

            if not wallets:
                print("[FAIL] No wallets found for transaction simulation")
                return 0, 0

            for i in range(num_transactions):
                try:
                    tx_start = time.time()

                    # Random transaction type
                    tx_type = random.choice(["DEPOSIT", "WITHDRAWAL", "TRANSFER"])
                    amount = Decimal(str(random.uniform(10, 1000)))

                    if tx_type == "DEPOSIT":
                        wallet = random.choice(wallets)
                        wallet.balance += amount

                        transaction = Transaction(
                            destination_wallet_id=wallet.id,
                            transaction_type=tx_type,
                            amount=amount,
                            destination_balance_after=wallet.balance,
                            status="SUCCESS",
                            description=f"Test deposit {i}",
                        )
                        db.session.add(transaction)

                    elif tx_type == "WITHDRAWAL":
                        eligible_wallets = [w for w in wallets if w.balance >= amount]
                        if eligible_wallets:
                            wallet = random.choice(eligible_wallets)
                            wallet.balance -= amount

                            transaction = Transaction(
                                source_wallet_id=wallet.id,
                                transaction_type=tx_type,
                                amount=amount,
                                source_balance_after=wallet.balance,
                                status="SUCCESS",
                                description=f"Test withdrawal {i}",
                            )
                            db.session.add(transaction)
                        else:
                            # Skip withdrawal if no eligible wallets
                            continue

                    elif tx_type == "TRANSFER":
                        eligible_source_wallets = [
                            w for w in wallets if w.balance >= amount
                        ]
                        if eligible_source_wallets:
                            source_wallet = random.choice(eligible_source_wallets)
                            dest_wallet = random.choice(
                                [w for w in wallets if w.id != source_wallet.id]
                            )

                            if dest_wallet:
                                source_wallet.balance -= amount
                                dest_wallet.balance += amount

                                transaction = Transaction(
                                    source_wallet_id=source_wallet.id,
                                    destination_wallet_id=dest_wallet.id,
                                    transaction_type=tx_type,
                                    amount=amount,
                                    source_balance_after=source_wallet.balance,
                                    destination_balance_after=dest_wallet.balance,
                                    status="SUCCESS",
                                    description=f"Test transfer {i}",
                                )
                                db.session.add(transaction)
                            else:
                                continue
                        else:
                            # Skip transfer if no eligible source wallets
                            continue

                    db.session.commit()

                    tx_end = time.time()
                    response_times.append(tx_end - tx_start)
                    success_count += 1

                except Exception as e:
                    error_count += 1
                    db.session.rollback()
                    print(f"[FAIL] Error in transaction {i}: {str(e)}")

        end_time = time.time()
        total_time = end_time - start_time

        self.results["performance_metrics"]["transaction_operations"] = {
            "total_transactions": num_transactions,
            "success_count": success_count,
            "error_count": error_count,
            "total_time": total_time,
            "avg_time_per_transaction": total_time / num_transactions,
            "transactions_per_second": num_transactions / total_time,
            "response_times": {
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "avg": statistics.mean(response_times) if response_times else 0,
                "median": statistics.median(response_times) if response_times else 0,
            },
        }

        print(
            f"[OK] Transaction simulation completed: {success_count}/{num_transactions} successful"
        )
        return success_count, error_count

    def simulate_api_endpoints(self, num_requests=200):
        """Simulate API endpoint calls"""
        print(f"... Simulating {num_requests} API endpoint calls...")

        start_time = time.time()
        success_count = 0
        error_count = 0
        response_times = []

        with self.app.test_client() as client:
            with self.app.app_context():
                # Create test user and get auth token
                user = User(
                    full_name="API Test User",
                    phone_number="+254712345678",
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

                # Test different endpoints
                endpoints = [
                    ("/api/v1/auth/me", "GET", None),
                    ("/api/v1/wallets/balance", "GET", None),
                    ("/api/v1/wallets/transactions", "GET", None),
                    (
                        "/api/v1/wallets/deposit",
                        "POST",
                        {"amount": 100.0, "description": "Test deposit"},
                    ),
                    (
                        "/api/v1/wallets/withdraw",
                        "POST",
                        {"amount": 50.0, "description": "Test withdrawal"},
                    ),
                    ("/health", "GET", None),
                ]

                for i in range(num_requests):
                    try:
                        req_start = time.time()

                        endpoint, method, data = random.choice(endpoints)

                        if method == "GET":
                            response = client.get(endpoint, headers=headers)
                        elif method == "POST":
                            response = client.post(endpoint, headers=headers, json=data)

                        req_end = time.time()
                        response_times.append(req_end - req_start)

                        if response.status_code in [200, 201]:
                            success_count += 1
                        else:
                            error_count += 1
                            print(
                                f"[FAIL] API error: {endpoint} returned {response.status_code}"
                            )

                    except Exception as e:
                        error_count += 1
                        print(f"[FAIL] API request error: {str(e)}")

        end_time = time.time()
        total_time = end_time - start_time

        self.results["api_response_times"] = {
            "total_requests": num_requests,
            "success_count": success_count,
            "error_count": error_count,
            "total_time": total_time,
            "avg_time_per_request": total_time / num_requests,
            "requests_per_second": num_requests / total_time,
            "response_times": {
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "avg": statistics.mean(response_times) if response_times else 0,
                "median": statistics.median(response_times) if response_times else 0,
            },
        }

        print(
            f"[OK] API simulation completed: {success_count}/{num_requests} successful"
        )
        return success_count, error_count

    def simulate_concurrent_operations(self, num_threads=10, operations_per_thread=50):
        """Simulate concurrent operations"""
        print(f"... Simulating concurrent operations with {num_threads} threads...")

        start_time = time.time()
        results = []

        def worker_thread(thread_id):
            thread_results = {"success": 0, "errors": 0, "operations": []}

            with self.app.app_context():
                for i in range(operations_per_thread):
                    try:
                        op_start = time.time()

                        # Random operation
                        operation = random.choice(
                            ["create_user", "create_transaction", "query_wallet"]
                        )

                        if operation == "create_user":
                            phone_number = f"+2547{random.randint(10000000, 99999999)}"
                            user = User(
                                full_name=f"Concurrent User {thread_id}-{i}",
                                phone_number=phone_number,
                                is_phone_verified=True,
                                is_active=True,
                            )
                            db.session.add(user)
                            db.session.flush()

                            wallet = Wallet(user_id=user.id)
                            db.session.add(wallet)
                            db.session.commit()

                        elif operation == "create_transaction":
                            wallets = Wallet.query.limit(10).all()
                            if wallets:
                                wallet = random.choice(wallets)
                                amount = Decimal(str(random.uniform(10, 100)))
                                wallet.balance += amount

                                transaction = Transaction(
                                    destination_wallet_id=wallet.id,
                                    transaction_type="DEPOSIT",
                                    amount=amount,
                                    destination_balance_after=wallet.balance,
                                    status="SUCCESS",
                                    description=f"Concurrent deposit {thread_id}-{i}",
                                )
                                db.session.add(transaction)
                                db.session.commit()

                        elif operation == "query_wallet":
                            wallets = Wallet.query.limit(10).all()
                            if wallets:
                                wallet = random.choice(wallets)
                                # Simulate query operation
                                balance = wallet.balance

                        op_end = time.time()
                        thread_results["operations"].append(op_end - op_start)
                        thread_results["success"] += 1

                    except Exception as e:
                        thread_results["errors"] += 1
                        db.session.rollback()

            return thread_results

        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(num_threads)]

            for future in as_completed(futures):
                results.append(future.result())

        end_time = time.time()
        total_time = end_time - start_time

        total_success = sum(r["success"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        all_operations = [op for r in results for op in r["operations"]]

        self.results["concurrent_operations"] = {
            "num_threads": num_threads,
            "operations_per_thread": operations_per_thread,
            "total_operations": num_threads * operations_per_thread,
            "total_success": total_success,
            "total_errors": total_errors,
            "total_time": total_time,
            "operations_per_second": (num_threads * operations_per_thread) / total_time,
            "avg_operation_time": (
                statistics.mean(all_operations) if all_operations else 0
            ),
            "thread_results": results,
        }

        print(
            f"[OK] Concurrent operations completed: {total_success}/{num_threads * operations_per_thread} successful"
        )
        return total_success, total_errors

    def simulate_database_stress_test(self, num_operations=1000):
        """Simulate database stress test"""
        print(f"... Running database stress test with {num_operations} operations...")

        start_time = time.time()
        success_count = 0
        error_count = 0

        with self.app.app_context():
            for i in range(num_operations):
                try:
                    # Create complex queries
                    users_count = User.query.count()
                    wallets_count = Wallet.query.count()
                    transactions_count = Transaction.query.count()

                    # Complex join query
                    complex_query = (
                        db.session.query(User, Wallet).join(Wallet).limit(10).all()
                    )

                    # Aggregation query
                    total_balance = (
                        db.session.query(db.func.sum(Wallet.balance)).scalar() or 0
                    )

                    # Transaction with rollback (stress test)
                    if i % 10 == 0:
                        db.session.begin()
                        try:
                            # Create temporary data
                            temp_user = User(
                                full_name=f"Temp User {i}",
                                phone_number=f"+2547{random.randint(10000000, 99999999)}",
                                is_phone_verified=True,
                                is_active=True,
                            )
                            db.session.add(temp_user)
                            db.session.flush()

                            temp_wallet = Wallet(user_id=temp_user.id)
                            db.session.add(temp_wallet)

                            # Rollback to test transaction handling
                            db.session.rollback()
                        except:
                            db.session.rollback()

                    success_count += 1

                except Exception as e:
                    error_count += 1
                    db.session.rollback()

        end_time = time.time()
        total_time = end_time - start_time

        self.results["database_performance"] = {
            "total_operations": num_operations,
            "success_count": success_count,
            "error_count": error_count,
            "total_time": total_time,
            "operations_per_second": num_operations / total_time,
            "avg_time_per_operation": total_time / num_operations,
        }

        print(
            f"[OK] Database stress test completed: {success_count}/{num_operations} successful"
        )
        return success_count, error_count

    def analyze_memory_usage(self):
        """Analyze memory usage patterns"""
        print("... Analyzing memory usage...")

        import psutil
        import gc

        process = psutil.Process()

        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        with self.app.app_context():
            # Create some data
            users = []
            wallets = []
            transactions = []

            for i in range(100):
                user = User(
                    full_name=f"Memory Test User {i}",
                    phone_number=f"+2547{random.randint(10000000, 99999999)}",
                    is_phone_verified=True,
                    is_active=True,
                )
                users.append(user)
                db.session.add(user)
                db.session.flush()

                wallet = Wallet(user_id=user.id, balance=random.uniform(100, 1000))
                wallets.append(wallet)
                db.session.add(wallet)

                for j in range(5):  # 5 transactions per user
                    transaction = Transaction(
                        source_wallet_id=wallet.id,
                        transaction_type="DEPOSIT",
                        amount=Decimal(str(random.uniform(10, 100))),
                        status="SUCCESS",
                        description=f"Memory test transaction {i}-{j}",
                    )
                    transactions.append(transaction)
                    db.session.add(transaction)

            db.session.commit()

            # Get memory after data creation
            after_creation_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Clear references and force garbage collection
            del users, wallets, transactions
            gc.collect()

            # Get memory after cleanup
            after_cleanup_memory = process.memory_info().rss / 1024 / 1024  # MB

        self.results["memory_usage"] = {
            "initial_memory_mb": initial_memory,
            "after_creation_memory_mb": after_creation_memory,
            "after_cleanup_memory_mb": after_cleanup_memory,
            "memory_increase_mb": after_creation_memory - initial_memory,
            "memory_cleanup_mb": after_creation_memory - after_cleanup_memory,
            "memory_efficiency": (
                (after_creation_memory - after_cleanup_memory)
                / (after_creation_memory - initial_memory)
                if (after_creation_memory - initial_memory) > 0
                else 0
            ),
        }

        print(f"[OK] Memory analysis completed")
        print(f"   Initial: {initial_memory:.2f} MB")
        print(f"   After creation: {after_creation_memory:.2f} MB")
        print(f"   After cleanup: {after_cleanup_memory:.2f} MB")

    def run_comprehensive_simulation(self):
        """Run comprehensive simulation"""
        print("🚀 Starting comprehensive KingdomPay simulation...")
        print("=" * 60)

        # Run all simulation tests
        self.simulate_user_registration_flow(100)
        self.simulate_transaction_operations(500)
        self.simulate_api_endpoints(200)
        self.simulate_concurrent_operations(10, 50)
        self.simulate_database_stress_test(1000)
        self.analyze_memory_usage()

        # Generate summary report
        self.generate_simulation_report()

        print("=" * 60)
        print("[OK] Comprehensive simulation completed!")

    def generate_simulation_report(self):
        """Generate comprehensive simulation report"""
        print("\n SIMULATION REPORT")
        print("=" * 60)

        # Performance Summary
        print("\n PERFORMANCE SUMMARY:")
        for test_name, metrics in self.results["performance_metrics"].items():
            print(f"\n{test_name.upper()}:")
            print(
                f"  Success Rate: {(metrics['success_count'] / metrics['total_users'] * 100):.1f}%"
                if "total_users" in metrics
                else f"  Success Rate: {(metrics['success_count'] / metrics['total_transactions'] * 100):.1f}%"
            )
            print(
                f"  Operations/sec: {metrics['users_per_second']:.2f}"
                if "users_per_second" in metrics
                else f"  Operations/sec: {metrics['transactions_per_second']:.2f}"
            )
            print(f"  Avg Response Time: {metrics['response_times']['avg']:.4f}s")

        # API Performance
        if self.results["api_response_times"]:
            print(f"\n API PERFORMANCE:")
            api_metrics = self.results["api_response_times"]
            print(
                f"  Success Rate: {(api_metrics['success_count'] / api_metrics['total_requests'] * 100):.1f}%"
            )
            print(f"  Requests/sec: {api_metrics['requests_per_second']:.2f}")
            print(f"  Avg Response Time: {api_metrics['response_times']['avg']:.4f}s")

        # Concurrent Operations
        if self.results["concurrent_operations"]:
            print(f"\n CONCURRENT OPERATIONS:")
            concurrent_metrics = self.results["concurrent_operations"]
            print(
                f"  Success Rate: {(concurrent_metrics['total_success'] / concurrent_metrics['total_operations'] * 100):.1f}%"
            )
            print(
                f"  Operations/sec: {concurrent_metrics['operations_per_second']:.2f}"
            )
            print(
                f"  Avg Operation Time: {concurrent_metrics['avg_operation_time']:.4f}s"
            )

        # Database Performance
        if self.results["database_performance"]:
            print(f"\n DATABASE PERFORMANCE:")
            db_metrics = self.results["database_performance"]
            print(
                f"  Success Rate: {(db_metrics['success_count'] / db_metrics['total_operations'] * 100):.1f}%"
            )
            print(f"  Operations/sec: {db_metrics['operations_per_second']:.2f}")

        # Memory Usage
        if self.results["memory_usage"]:
            print(f"\n💾 MEMORY USAGE:")
            memory_metrics = self.results["memory_usage"]
            print(f"  Memory Increase: {memory_metrics['memory_increase_mb']:.2f} MB")
            print(
                f"  Cleanup Efficiency: {(memory_metrics['memory_efficiency'] * 100):.1f}%"
            )

        # Recommendations
        print(f"\n RECOMMENDATIONS:")
        self.generate_recommendations()

        # Save detailed results
        self.save_detailed_results()

    def generate_recommendations(self):
        """Generate performance recommendations"""
        recommendations = []

        # Check API response times
        if self.results["api_response_times"]:
            avg_response_time = self.results["api_response_times"]["response_times"][
                "avg"
            ]
            if avg_response_time > 0.1:  # 100ms
                recommendations.append(
                    "Consider optimizing API endpoints - response times are above 100ms"
                )

        # Check concurrent operations
        if self.results["concurrent_operations"]:
            success_rate = (
                self.results["concurrent_operations"]["total_success"]
                / self.results["concurrent_operations"]["total_operations"]
            )
            if success_rate < 0.95:  # 95%
                recommendations.append(
                    "Improve concurrent operation handling - success rate below 95%"
                )

        # Check memory usage
        if self.results["memory_usage"]:
            memory_efficiency = self.results["memory_usage"]["memory_efficiency"]
            if memory_efficiency < 0.8:  # 80%
                recommendations.append(
                    "Optimize memory usage - cleanup efficiency below 80%"
                )

        # Check database performance
        if self.results["database_performance"]:
            db_success_rate = (
                self.results["database_performance"]["success_count"]
                / self.results["database_performance"]["total_operations"]
            )
            if db_success_rate < 0.99:  # 99%
                recommendations.append(
                    "Review database operations - success rate below 99%"
                )

        if not recommendations:
            recommendations.append(
                "Overall performance looks good! No major issues detected."
            )

        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

    def save_detailed_results(self):
        """Save detailed results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"simulation_results_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\n📁 Detailed results saved to: {filename}")


def main():
    """Main simulation function"""
    simulator = KingdomPaySimulator()
    simulator.run_comprehensive_simulation()


if __name__ == "__main__":
    main()
