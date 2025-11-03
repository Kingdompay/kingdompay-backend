"""
Reconciliation routes for Phase 2
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from api.v1 import api_v1_bp
from services.auth_service import AuthService
from services.rbac import require_admin
from services.reconciliation_service import ReconciliationService
from datetime import datetime, date
from extensions import db


auth_service = AuthService()
reconciliation_service = ReconciliationService()


@api_v1_bp.route("/reconciliation/reconcile", methods=["POST"])
@jwt_required()
@require_admin
def reconcile_provider():
    """Reconcile provider statement with internal payments (admin only)"""
    try:
        data = request.get_json() or {}
        provider = data.get("provider")
        statement_date_str = data.get("statement_date")
        provider_transactions = data.get("provider_transactions", [])

        if not provider or not statement_date_str or not provider_transactions:
            return (
                jsonify({
                    "success": False,
                    "message": "provider, statement_date, and provider_transactions are required",
                }),
                400,
            )

        try:
            statement_date = datetime.fromisoformat(statement_date_str.split("T")[0]).date()
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format"}), 400

        result = reconciliation_service.reconcile_provider(
            provider=provider,
            statement_date=statement_date,
            provider_transactions=provider_transactions,
        )

        return jsonify(result), 200

    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"success": False, "message": f"Reconciliation failed: {str(e)}"}),
            500,
        )


@api_v1_bp.route("/reconciliation/reports", methods=["GET"])
@jwt_required()
@require_admin
def get_reconciliation_reports():
    """Get reconciliation reports (admin only)"""
    try:
        provider = request.args.get("provider")
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")

        start_date = None
        end_date = None

        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str.split("T")[0]).date()
            except ValueError:
                return jsonify({"success": False, "message": "Invalid start_date format"}), 400

        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.split("T")[0]).date()
            except ValueError:
                return jsonify({"success": False, "message": "Invalid end_date format"}), 400

        result = reconciliation_service.get_reconciliation_report(
            provider=provider,
            start_date=start_date,
            end_date=end_date,
        )

        return jsonify(result), 200

    except Exception as e:
        return (
            jsonify({"success": False, "message": f"Failed to get reports: {str(e)}"}),
            500,
        )

