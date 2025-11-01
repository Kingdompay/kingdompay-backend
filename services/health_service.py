"""
Health Check Service for KingdomPay
Comprehensive health monitoring for production
"""

import time
import psutil
from typing import Dict, Any, List
from flask import current_app
from sqlalchemy import text
from extensions import db
import logging

logger = logging.getLogger(__name__)


class HealthService:
    """Service for comprehensive health monitoring"""

    def __init__(self):
        self.start_time = time.time()

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            health_checks = {
                "database": self._check_database(),
                "redis": self._check_redis(),
                "disk_space": self._check_disk_space(),
                "memory": self._check_memory(),
                "cpu": self._check_cpu(),
                "uptime": self._get_uptime(),
            }

            # Determine overall status
            critical_services = ["database", "redis"]
            overall_status = "healthy"

            for service in critical_services:
                if health_checks[service]["status"] != "healthy":
                    overall_status = "unhealthy"
                    break

            return {
                "status": overall_status,
                "timestamp": time.time(),
                "version": "1.0.0",
                "environment": current_app.config.get("APP_ENV", "development"),
                "checks": health_checks,
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "timestamp": time.time(), "error": str(e)}

    def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            start_time = time.time()

            # Test basic connectivity
            result = db.session.execute(text("SELECT 1")).fetchone()

            # Test query performance
            query_time = time.time() - start_time

            # Get database info
            db_info = db.session.execute(text("SELECT version()")).fetchone()

            return {
                "status": "healthy",
                "response_time_ms": round(query_time * 1000, 2),
                "version": db_info[0] if db_info else "unknown",
                "connection_pool": {
                    "size": db.engine.pool.size(),
                    "checked_in": db.engine.pool.checkedin(),
                    "checked_out": db.engine.pool.checkedout(),
                    "overflow": db.engine.pool.overflow(),
                },
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        try:
            start_time = time.time()

            # Test basic connectivity
            current_app.cache_service.redis.ping()

            # Test set/get performance
            test_key = "health_check_test"
            test_value = "test_value"
            current_app.cache_service.set(test_key, test_value, 10)
            retrieved_value = current_app.cache_service.get(test_key)
            current_app.cache_service.delete(test_key)

            # Get Redis info
            redis_info = current_app.cache_service.health_check()

            response_time = time.time() - start_time

            if retrieved_value == test_value:
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time * 1000, 2),
                    "redis_info": redis_info,
                }
            else:
                return {"status": "unhealthy", "error": "Redis read/write test failed"}
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def _check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space"""
        try:
            disk_usage = psutil.disk_usage("/")
            total_gb = disk_usage.total / (1024**3)
            free_gb = disk_usage.free / (1024**3)
            used_percent = (disk_usage.used / disk_usage.total) * 100

            status = "healthy"
            if used_percent > 90:
                status = "critical"
            elif used_percent > 80:
                status = "warning"

            return {
                "status": status,
                "total_gb": round(total_gb, 2),
                "free_gb": round(free_gb, 2),
                "used_percent": round(used_percent, 2),
            }
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            available_gb = memory.available / (1024**3)
            used_percent = memory.percent

            status = "healthy"
            if used_percent > 90:
                status = "critical"
            elif used_percent > 80:
                status = "warning"

            return {
                "status": status,
                "total_gb": round(memory_gb, 2),
                "available_gb": round(available_gb, 2),
                "used_percent": round(used_percent, 2),
            }
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def _check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            status = "healthy"
            if cpu_percent > 90:
                status = "critical"
            elif cpu_percent > 80:
                status = "warning"

            return {
                "status": status,
                "usage_percent": round(cpu_percent, 2),
                "cpu_count": cpu_count,
            }
        except Exception as e:
            logger.error(f"CPU check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def _get_uptime(self) -> Dict[str, Any]:
        """Get application uptime"""
        try:
            uptime_seconds = time.time() - self.start_time
            uptime_hours = uptime_seconds / 3600

            return {
                "status": "healthy",
                "uptime_seconds": round(uptime_seconds, 2),
                "uptime_hours": round(uptime_hours, 2),
            }
        except Exception as e:
            logger.error(f"Uptime check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def get_readiness(self) -> Dict[str, Any]:
        """Check if the application is ready to serve traffic"""
        try:
            # Check critical dependencies
            db_health = self._check_database()
            redis_health = self._check_redis()

            if db_health["status"] == "healthy" and redis_health["status"] == "healthy":
                return {"status": "ready", "timestamp": time.time()}
            else:
                return {
                    "status": "not_ready",
                    "timestamp": time.time(),
                    "issues": [
                        {"service": "database", "status": db_health["status"]},
                        {"service": "redis", "status": redis_health["status"]},
                    ],
                }
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return {"status": "not_ready", "timestamp": time.time(), "error": str(e)}

    def get_liveness(self) -> Dict[str, Any]:
        """Check if the application is alive (basic health)"""
        try:
            # Basic liveness check - just ensure the app is responding
            return {
                "status": "alive",
                "timestamp": time.time(),
                "uptime_seconds": round(time.time() - self.start_time, 2),
            }
        except Exception as e:
            logger.error(f"Liveness check failed: {e}")
            return {"status": "dead", "timestamp": time.time(), "error": str(e)}
