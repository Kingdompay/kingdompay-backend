"""
Reports routes for treasurer CSV exports
"""

import csv
import io
from flask import Response, request, jsonify
from flask_jwt_extended import jwt_required
from routes import api_v1_bp
from services.auth_service import AuthService
from services.rbac import is_community_admin
from models.transaction import Transaction
from models.community import CommunityMember
from models.wallet import Wallet


auth_service = AuthService()


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
