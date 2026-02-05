#!/usr/bin/env python3
"""
Performance and Load Testing Script for KingdomPay
Tests system performance under various load conditions
"""

import os
import time
import json
import random
import threading
import statistics
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from decimal import Decimal
from app import create_app
from extensions import db
from models import User, Wallet, Transaction, OTPVerification


class PerformanceTester:
    """Performance and load testing for KingdomPay"""

    def __init__(self):
        self.app = None
        self.results = {
            "load_test_results": {},
            "performance_metrics": {},
            "bottleneck_analysis": {},
            "scalability_tests": {},
            "memory_analysis": {},
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

    def test_concurrent_users(self, num_users=50, operations_per_user=10):
        """Test concurrent user operations"""
        print(
            f"... Testing {num_users} concurrent users with {operations_per_user} operations each..."
        )

        start_time = time.time()
        results = []

        def user_operations(user_id):
            user_results = {
                "user_id": user_id,
                "success": 0,
                "errors": 0,
                "operations": [],
            }

            with self.app.app_context():
                try:
                    # Create unique user
                    phone_number = f"+2547{random.randint(10000000, 99999999)}"
                    user = User(
                        full_name=f"Concurrent User {user_id}",
                        phone_number=phone_number,
                        email=f"concurrent{user_id}@test.com",
                        is_phone_verified=True,
                        is_active=True,
                    )
                    db.session.add(user)
                    db.session.flush()

                    wallet = Wallet(user_id=user.id, balance=1000.0)
                    db.session.add(wallet)
                    db.session.commit()

                    # Perform operations
                    for i in range(operations_per_user):
                        op_start = time.time()

                        try:
                            # Random operation
                            operation = random.choice(["deposit", "withdraw", "query"])

                            if operation == "deposit":
                                amount = Decimal(str(random.uniform(10, 100)))
                                wallet.balance += amount

                                transaction = Transaction(
                                    destination_wallet_id=wallet.id,
                                    transaction_type="DEPOSIT",
                                    amount=amount,
                                    destination_balance_after=wallet.balance,
                                    status="SUCCESS",
                                    description=f"Concurrent deposit {user_id}-{i}",
                                )
                                db.session.add(transaction)
                                db.session.commit()

                            elif operation == "withdraw":
                                amount = Decimal(str(random.uniform(10, 50)))
                                if wallet.balance >= amount:
                                    wallet.balance -= amount

                                    transaction = Transaction(
                                        source_wallet_id=wallet.id,
                                        transaction_type="WITHDRAWAL",
                                        amount=amount,
                                        source_balance_after=wallet.balance,
                                        status="SUCCESS",
                                        description=f"Concurrent withdrawal {user_id}-{i}",
                                    )
                                    db.session.add(transaction)
                                    db.session.commit()

                            elif operation == "query":
                                # Simple query operation
                                balance = wallet.balance
                                transactions = Transaction.query.filter_by(
                                    destination_wallet_id=wallet.id
                                ).count()

                            op_end = time.time()
                            user_results["operations"].append(op_end - op_start)
                            user_results["success"] += 1

                        except Exception as e:
                            user_results["errors"] += 1
                            db.session.rollback()

                except Exception as e:
                    user_results["errors"] += 1
                    db.session.rollback()

            return user_results

        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=min(num_users, 20)) as executor:
            futures = [executor.submit(user_operations, i) for i in range(num_users)]

            for future in as_completed(futures):
                results.append(future.result())

        end_time = time.time()
        total_time = end_time - start_time

        total_success = sum(r["success"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        all_operations = [op for r in results for op in r["operations"]]

        self.results["load_test_results"]["concurrent_users"] = {
            "num_users": num_users,
            "operations_per_user": operations_per_user,
            "total_operations": num_users * operations_per_user,
            "total_success": total_success,
            "total_errors": total_errors,
            "success_rate": (
                (total_success / (total_success + total_errors)) * 100
                if (total_success + total_errors) > 0
                else 0
            ),
            "total_time": total_time,
            "operations_per_second": (num_users * operations_per_user) / total_time,
            "avg_operation_time": (
                statistics.mean(all_operations) if all_operations else 0
            ),
            "max_operation_time": max(all_operations) if all_operations else 0,
            "min_operation_time": min(all_operations) if all_operations else 0,
        }

        print(
            f"[OK] Concurrent users test completed: {total_success}/{num_users * operations_per_user} successful"
        )
        return total_success, total_errors

    def test_api_load(self, num_requests=200, concurrent_requests=10):
        """Test API load handling"""
        print(
            f"... Testing API load: {num_requests} requests with {concurrent_requests} concurrent..."
        )

        start_time = time.time()
        results = []

        def api_request(request_id):
            request_results = {
                "request_id": request_id,
                "success": False,
                "response_time": 0,
                "status_code": 0,
            }

            with self.app.test_client() as client:
                with self.app.app_context():
                    try:
                        # Create test user
                        user = User(
                            full_name=f"API Load User {request_id}",
                            phone_number=f"+2547{random.randint(10000000, 99999999)}",
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

                        # Make API request
                        req_start = time.time()

                        endpoint = random.choice(
                            [
                                "/api/v1/auth/me",
                                "/api/v1/wallets/balance",
                                "/api/v1/wallets/transactions",
                                "/health",
                            ]
                        )

                        response = client.get(endpoint, headers=headers)

                        req_end = time.time()

                        request_results["response_time"] = req_end - req_start
                        request_results["status_code"] = response.status_code
                        request_results["success"] = response.status_code == 200

                    except Exception as e:
                        request_results["error"] = str(e)

            return request_results

        # Execute concurrent API requests
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(api_request, i) for i in range(num_requests)]

            for future in as_completed(futures):
                results.append(future.result())

        end_time = time.time()
        total_time = end_time - start_time

        successful_requests = len([r for r in results if r["success"]])
        failed_requests = len([r for r in results if not r["success"]])
        response_times = [r["response_time"] for r in results if r["response_time"] > 0]

        self.results["load_test_results"]["api_load"] = {
            "total_requests": num_requests,
            "concurrent_requests": concurrent_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / num_requests) * 100,
            "total_time": total_time,
            "requests_per_second": num_requests / total_time,
            "avg_response_time": (
                statistics.mean(response_times) if response_times else 0
            ),
            "max_response_time": max(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "response_times": response_times,
        }

        print(
            f"[OK] API load test completed: {successful_requests}/{num_requests} successful"
        )
        return successful_requests, failed_requests

    def test_database_scalability(self, num_records=1000):
        """Test database scalability with large datasets"""
        print(f"... Testing database scalability with {num_records} records...")

        start_time = time.time()
        operations_count = 0
        error_count = 0

        with self.app.app_context():
            try:
                # Create users in batches
                batch_size = 100
                for batch_start in range(0, num_records, batch_size):
                    batch_end = min(batch_start + batch_size, num_records)

                    users = []
                    wallets = []

                    for i in range(batch_start, batch_end):
                        user = User(
                            full_name=f"Scalability User {i}",
                            phone_number=f"+2547{random.randint(10000000, 99999999)}",
                            email=f"scalability{i}@test.com",
                            is_phone_verified=True,
                            is_active=True,
                        )
                        users.append(user)
                        db.session.add(user)

                    db.session.flush()
                    operations_count += len(users)

                    # Create wallets
                    for user in users:
                        wallet = Wallet(
                            user_id=user.id, balance=random.uniform(100, 1000)
                        )
                        wallets.append(wallet)
                        db.session.add(wallet)

                    db.session.flush()
                    operations_count += len(wallets)

                    # Create transactions
                    for i in range(len(wallets)):
                        wallet = wallets[i]
                        amount = Decimal(str(random.uniform(10, 100)))
                        wallet.balance = Decimal(str(wallet.balance)) + amount

                        transaction = Transaction(
                            destination_wallet_id=wallet.id,
                            transaction_type="DEPOSIT",
                            amount=amount,
                            destination_balance_after=wallet.balance,
                            status="SUCCESS",
                            description=f"Scalability transaction {batch_start + i}",
                        )
                        db.session.add(transaction)

                    db.session.commit()
                    operations_count += len(wallets)

                # Test queries on large dataset
                user_count = User.query.count()
                wallet_count = Wallet.query.count()
                transaction_count = Transaction.query.count()

                operations_count += 3

                # Test complex queries
                complex_query_start = time.time()
                complex_result = (
                    db.session.query(User, Wallet).join(Wallet).limit(100).all()
                )
                complex_query_time = time.time() - complex_query_start

                operations_count += 1

                print(
                    f"[OK] Database scalability test completed: {operations_count} operations"
                )

            except Exception as e:
                error_count += 1
                print(f"[FAIL] Database scalability test failed: {str(e)}")
                db.session.rollback()

        end_time = time.time()
        total_time = end_time - start_time

        self.results["scalability_tests"]["database_scalability"] = {
            "num_records": num_records,
            "total_operations": operations_count,
            "error_count": error_count,
            "success_rate": (
                ((operations_count - error_count) / operations_count) * 100
                if operations_count > 0
                else 0
            ),
            "total_time": total_time,
            "operations_per_second": (
                operations_count / total_time if total_time > 0 else 0
            ),
            "complex_query_time": (
                complex_query_time if "complex_query_time" in locals() else 0
            ),
        }

        return operations_count, error_count

    def test_memory_usage(self):
        """Test memory usage patterns"""
        print("... Testing memory usage patterns...")

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_snapshots = []

        with self.app.app_context():
            # Create data in batches and monitor memory
            for batch in range(5):
                batch_start_memory = process.memory_info().rss / 1024 / 1024

                users = []
                wallets = []
                transactions = []

                # Create batch of data
                for i in range(100):
                    user = User(
                        full_name=f"Memory Test User {batch}-{i}",
                        phone_number=f"+2547{random.randint(10000000, 99999999)}",
                        email=f"memory{batch}-{i}@test.com",
                        is_phone_verified=True,
                        is_active=True,
                    )
                    users.append(user)
                    db.session.add(user)

                db.session.flush()

                for user in users:
                    wallet = Wallet(user_id=user.id, balance=random.uniform(100, 1000))
                    wallets.append(wallet)
                    db.session.add(wallet)

                db.session.flush()

                for wallet in wallets:
                    amount = Decimal(str(random.uniform(10, 100)))
                    wallet.balance = Decimal(str(wallet.balance)) + amount

                    transaction = Transaction(
                        destination_wallet_id=wallet.id,
                        transaction_type="DEPOSIT",
                        amount=amount,
                        destination_balance_after=wallet.balance,
                        status="SUCCESS",
                        description=f"Memory test transaction {batch}-{i}",
                    )
                    transactions.append(transaction)
                    db.session.add(transaction)

                db.session.commit()

                batch_end_memory = process.memory_info().rss / 1024 / 1024

                memory_snapshots.append(
                    {
                        "batch": batch,
                        "start_memory": batch_start_memory,
                        "end_memory": batch_end_memory,
                        "memory_increase": batch_end_memory - batch_start_memory,
                    }
                )

        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_increase = final_memory - initial_memory

        self.results["memory_analysis"] = {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "total_memory_increase_mb": total_memory_increase,
            "memory_snapshots": memory_snapshots,
            "avg_memory_per_batch": (
                statistics.mean([s["memory_increase"] for s in memory_snapshots])
                if memory_snapshots
                else 0
            ),
        }

        print(f"[OK] Memory usage test completed")
        print(f"   Initial: {initial_memory:.2f} MB")
        print(f"   Final: {final_memory:.2f} MB")
        print(f"   Increase: {total_memory_increase:.2f} MB")

    def analyze_bottlenecks(self):
        """Analyze performance bottlenecks"""
        print("... Analyzing performance bottlenecks...")

        bottlenecks = []

        # Analyze concurrent user performance
        if "concurrent_users" in self.results["load_test_results"]:
            concurrent_data = self.results["load_test_results"]["concurrent_users"]
            if concurrent_data["success_rate"] < 95:
                bottlenecks.append(
                    {
                        "type": "Concurrent Operations",
                        "issue": f"Success rate {concurrent_data['success_rate']:.1f}% below 95%",
                        "impact": "High",
                        "recommendation": "Review database locking and transaction handling",
                    }
                )

            if concurrent_data["avg_operation_time"] > 0.1:
                bottlenecks.append(
                    {
                        "type": "Operation Speed",
                        "issue": f"Average operation time {concurrent_data['avg_operation_time']:.4f}s above 100ms",
                        "impact": "Medium",
                        "recommendation": "Optimize database queries and operations",
                    }
                )

        # Analyze API performance
        if "api_load" in self.results["load_test_results"]:
            api_data = self.results["load_test_results"]["api_load"]
            if api_data["avg_response_time"] > 0.05:  # 50ms
                bottlenecks.append(
                    {
                        "type": "API Response Time",
                        "issue": f"Average response time {api_data['avg_response_time']:.4f}s above 50ms",
                        "impact": "High",
                        "recommendation": "Optimize API endpoints and database queries",
                    }
                )

            if api_data["success_rate"] < 99:
                bottlenecks.append(
                    {
                        "type": "API Reliability",
                        "issue": f"API success rate {api_data['success_rate']:.1f}% below 99%",
                        "impact": "High",
                        "recommendation": "Improve error handling and validation",
                    }
                )

        # Analyze database scalability
        if "database_scalability" in self.results["scalability_tests"]:
            db_data = self.results["scalability_tests"]["database_scalability"]
            if db_data["complex_query_time"] > 1.0:  # 1 second
                bottlenecks.append(
                    {
                        "type": "Database Query Performance",
                        "issue": f"Complex query time {db_data['complex_query_time']:.4f}s above 1s",
                        "impact": "Medium",
                        "recommendation": "Add database indexes and optimize queries",
                    }
                )

        # Analyze memory usage
        if "memory_analysis" in self.results:
            memory_data = self.results["memory_analysis"]
            if memory_data["avg_memory_per_batch"] > 10:  # 10MB per batch
                bottlenecks.append(
                    {
                        "type": "Memory Usage",
                        "issue": f"Average memory increase {memory_data['avg_memory_per_batch']:.2f}MB per batch above 10MB",
                        "impact": "Medium",
                        "recommendation": "Optimize memory usage and implement cleanup",
                    }
                )

        self.results["bottleneck_analysis"] = {
            "bottlenecks": bottlenecks,
            "total_bottlenecks": len(bottlenecks),
            "high_impact": len([b for b in bottlenecks if b["impact"] == "High"]),
            "medium_impact": len([b for b in bottlenecks if b["impact"] == "Medium"]),
            "low_impact": len([b for b in bottlenecks if b["impact"] == "Low"]),
        }

        print(
            f"[OK] Bottleneck analysis completed: {len(bottlenecks)} bottlenecks identified"
        )

    def generate_recommendations(self):
        """Generate performance recommendations"""
        recommendations = []

        # Based on bottleneck analysis
        if self.results["bottleneck_analysis"]["high_impact"] > 0:
            recommendations.append(
                "Address high-impact performance bottlenecks immediately"
            )

        if self.results["bottleneck_analysis"]["medium_impact"] > 0:
            recommendations.append(
                "Plan optimization for medium-impact performance issues"
            )

        # Based on specific metrics
        if "concurrent_users" in self.results["load_test_results"]:
            concurrent_data = self.results["load_test_results"]["concurrent_users"]
            if concurrent_data["success_rate"] < 95:
                recommendations.append("Implement better database connection pooling")
                recommendations.append(
                    "Review and optimize transaction isolation levels"
                )

        if "api_load" in self.results["load_test_results"]:
            api_data = self.results["load_test_results"]["api_load"]
            if api_data["avg_response_time"] > 0.05:
                recommendations.append("Implement API response caching")
                recommendations.append("Optimize database queries with proper indexing")

        if "database_scalability" in self.results["scalability_tests"]:
            db_data = self.results["scalability_tests"]["database_scalability"]
            if db_data["complex_query_time"] > 1.0:
                recommendations.append(
                    "Add database indexes for frequently queried fields"
                )
                recommendations.append("Consider database query optimization")

        if "memory_analysis" in self.results:
            memory_data = self.results["memory_analysis"]
            if memory_data["avg_memory_per_batch"] > 10:
                recommendations.append("Implement memory cleanup routines")
                recommendations.append("Consider pagination for large data operations")

        if not recommendations:
            recommendations.append(
                "Performance looks good! Consider implementing monitoring for production"
            )

        self.results["recommendations"] = recommendations

    def run_performance_tests(self):
        """Run all performance tests"""
        print("🚀 Starting KingdomPay Performance Tests...")
        print("=" * 60)

        # Run all tests
        self.test_concurrent_users(50, 10)
        self.test_api_load(200, 10)
        self.test_database_scalability(1000)
        self.test_memory_usage()

        # Analyze results
        self.analyze_bottlenecks()
        self.generate_recommendations()

        # Generate report
        self.generate_report()

        print("=" * 60)
        print("[OK] Performance tests completed!")

    def generate_report(self):
        """Generate performance report"""
        print("\n PERFORMANCE TEST REPORT")
        print("=" * 60)

        # Load Test Results
        print("\n LOAD TEST RESULTS:")
        for test_name, results in self.results["load_test_results"].items():
            print(f"\n{test_name.upper()}:")
            print(f"  Success Rate: {results['success_rate']:.1f}%")
            if "operations_per_second" in results:
                print(f"  Operations/sec: {results['operations_per_second']:.2f}")
            if "avg_response_time" in results:
                print(f"  Avg Response Time: {results['avg_response_time']:.4f}s")
            if "avg_operation_time" in results:
                print(f"  Avg Operation Time: {results['avg_operation_time']:.4f}s")

        # Scalability Tests
        print("\n📈 SCALABILITY TESTS:")
        for test_name, results in self.results["scalability_tests"].items():
            print(f"\n{test_name.upper()}:")
            print(f"  Success Rate: {results['success_rate']:.1f}%")
            print(f"  Operations/sec: {results['operations_per_second']:.2f}")
            if "complex_query_time" in results:
                print(f"  Complex Query Time: {results['complex_query_time']:.4f}s")

        # Memory Analysis
        print("\n💾 MEMORY ANALYSIS:")
        memory_data = self.results["memory_analysis"]
        print(f"  Initial Memory: {memory_data['initial_memory_mb']:.2f} MB")
        print(f"  Final Memory: {memory_data['final_memory_mb']:.2f} MB")
        print(f"  Total Increase: {memory_data['total_memory_increase_mb']:.2f} MB")
        print(f"  Avg per Batch: {memory_data['avg_memory_per_batch']:.2f} MB")

        # Bottleneck Analysis
        print("\n🔍 BOTTLENECK ANALYSIS:")
        bottleneck_data = self.results["bottleneck_analysis"]
        print(f"  Total Bottlenecks: {bottleneck_data['total_bottlenecks']}")
        print(f"  High Impact: {bottleneck_data['high_impact']}")
        print(f"  Medium Impact: {bottleneck_data['medium_impact']}")
        print(f"  Low Impact: {bottleneck_data['low_impact']}")

        if bottleneck_data["bottlenecks"]:
            print("\n  Identified Bottlenecks:")
            for i, bottleneck in enumerate(bottleneck_data["bottlenecks"], 1):
                print(f"    {i}. {bottleneck['type']}: {bottleneck['issue']}")
                print(f"       Impact: {bottleneck['impact']}")
                print(f"       Recommendation: {bottleneck['recommendation']}")

        # Recommendations
        print("\n RECOMMENDATIONS:")
        for i, rec in enumerate(self.results["recommendations"], 1):
            print(f"  {i}. {rec}")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_test_results_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\n📁 Detailed results saved to: {filename}")


def main():
    """Main performance testing function"""
    tester = PerformanceTester()
    tester.run_performance_tests()


if __name__ == "__main__":
    main()
