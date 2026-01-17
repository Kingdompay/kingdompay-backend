"""
Reports routes for treasurer CSV exports
"""

import csv
import io
from datetime import datetime, timedelta
from flask import Response, request, jsonify
from flask_jwt_extended import jwt_required
from routes import api_v1_bp
from services.auth_service import AuthService
from services.rbac import is_community_admin, require_admin
from models.transaction import Transaction
from models.community import CommunityMember
from models.wallet import Wallet
from extensions import db


auth_service = AuthService()


@api_v1_bp.route("/reports/daily", methods=["GET"])
@jwt_required()
@require_admin
def get_daily_report():
    """Get daily transaction report (admin only)"""
    try:
        date_str = request.args.get("date")
        
        if date_str:
            try:
                report_date = datetime.fromisoformat(date_str).date()
            except ValueError:
                return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD"}), 400
        else:
            report_date = datetime.utcnow().date()
        
        # Get start and end of day
        start_of_day = datetime.combine(report_date, datetime.min.time())
        end_of_day = datetime.combine(report_date, datetime.max.time())
        
        # Query transactions for the day
        transactions = Transaction.query.filter(
            Transaction.created_at >= start_of_day,
            Transaction.created_at <= end_of_day
        ).all()
        
        # Calculate summary
        total_volume = sum(float(t.amount) for t in transactions)
        successful = [t for t in transactions if t.status == "SUCCESS"]
        failed = [t for t in transactions if t.status == "FAILED"]
        
        return jsonify({
            "success": True,
            "report": {
                "date": report_date.isoformat(),
                "total_transactions": len(transactions),
                "successful_transactions": len(successful),
                "failed_transactions": len(failed),
                "total_volume": total_volume,
                "successful_volume": sum(float(t.amount) for t in successful),
            }
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to generate report: {str(e)}"}), 500


@api_v1_bp.route("/reports/settlement", methods=["GET"])
@jwt_required()
@require_admin
def get_settlement_report():
    """Get settlement report (admin only)"""
    try:
        # Get date range
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str)
            except ValueError:
                return jsonify({"success": False, "message": "Invalid start_date format"}), 400
        else:
            start_date = datetime.utcnow() - timedelta(days=7)
        
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str)
            except ValueError:
                return jsonify({"success": False, "message": "Invalid end_date format"}), 400
        else:
            end_date = datetime.utcnow()
        
        # Query transactions in date range
        transactions = Transaction.query.filter(
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date,
            Transaction.status == "SUCCESS"
        ).all()
        
        # Group by type
        transfers = [t for t in transactions if t.transaction_type == "TRANSFER"]
        deposits = [t for t in transactions if t.transaction_type == "DEPOSIT"]
        withdrawals = [t for t in transactions if t.transaction_type == "WITHDRAWAL"]
        
        return jsonify({
            "success": True,
            "report": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_transactions": len(transactions),
                "transfers": {
                    "count": len(transfers),
                    "volume": sum(float(t.amount) for t in transfers)
                },
                "deposits": {
                    "count": len(deposits),
                    "volume": sum(float(t.amount) for t in deposits)
                },
                "withdrawals": {
                    "count": len(withdrawals),
                    "volume": sum(float(t.amount) for t in withdrawals)
                },
                "net_flow": sum(float(t.amount) for t in deposits) - sum(float(t.amount) for t in withdrawals)
            }
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to generate report: {str(e)}"}), 500


@api_v1_bp.route(
    "/communities/<int:community_id>/reports/transactions.csv", methods=["GET"]
)
@jwt_required()
def export_transactions_csv(community_id: int):
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        if not is_community_admin(user.id, community_id):
            return jsonify({"success": False, "message": "Forbidden"}), 403

        # Collect all wallets for community members (MVP approach)
        member_ids = [
            m.user_id
            for m in CommunityMember.query.filter_by(community_id=community_id).all()
        ]
        wallet_ids = [
            w.id for w in Wallet.query.filter(Wallet.user_id.in_(member_ids)).all()
        ]
        txs = (
            Transaction.query.filter(
                (Transaction.source_wallet_id.in_(wallet_ids))
                | (Transaction.destination_wallet_id.in_(wallet_ids))
            )
            .order_by(Transaction.created_at.desc())
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "source_wallet_id",
                "destination_wallet_id",
                "type",
                "amount",
                "status",
                "created_at",
            ]
        )
        for t in txs:
            writer.writerow(
                [
                    t.id,
                    t.source_wallet_id,
                    t.destination_wallet_id,
                    t.transaction_type,
                    float(t.amount),
                    t.status,
                    t.created_at.isoformat() if t.created_at else "",
                ]
            )

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=community_{community_id}_transactions.csv"
            },
        )
    except Exception:
        return jsonify({"success": False, "message": "Failed to generate CSV"}), 500
