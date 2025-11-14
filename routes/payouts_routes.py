"""
Payout routes for Phase 2: community treasurer payouts to external accounts
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from routes import api_v1_bp
from services.auth_service import AuthService
from services.provider_service import ProviderService
from services.multisig_service import MultiSigService
from services.ledger_service import LedgerService
from services.rbac import is_community_admin, is_community_treasurer
from extensions import db
from models.payment import Payment
from models.wallet import Wallet
from models.community import Community
from models.multisig import MultiSigApproval
from decimal import Decimal


auth_service = AuthService()
provider_service = ProviderService()
multisig_service = MultiSigService()
ledger_service = LedgerService()


@api_v1_bp.route("/payouts", methods=["POST"])
@jwt_required()
def create_payout():
    """Create payout from community wallet to external recipient"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        data = request.get_json() or {}
        from_wallet_id = data.get("from_wallet") or data.get("from_wallet_id")
        method = data.get("method")  # MOMO|BANK
        destination = data.get("destination")  # phone or account number
        amount = data.get("amount")
        currency = data.get("currency", "KES")
        provider = data.get("provider", "MPESA")
        community_id = data.get("community_id")

        if not from_wallet_id or not method or not destination or not amount:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "from_wallet, method, destination, amount are required",
                    }
                ),
                400,
            )

        wallet = Wallet.query.get(from_wallet_id)
        if not wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        if Decimal(str(amount)) > Decimal(wallet.balance):
            return jsonify({"success": False, "message": "Insufficient funds"}), 400

        # Check if this is a community wallet - require multi-sig approval
        wallet_owner_type = getattr(wallet, "owner_type", "USER")

        if wallet_owner_type == "COMMUNITY":
            # For community wallets, create multi-sig approval instead of executing immediately
            wallet_owner_id = getattr(wallet, "owner_id", None)

            if not community_id:
                community_id = wallet_owner_id

            if not community_id:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Community ID required for community wallet payouts",
                        }
                    ),
                    400,
                )

            # Verify user is admin/treasurer
            if not (
                is_community_admin(user.id, community_id)
                or is_community_treasurer(user.id, community_id)
            ):
                return jsonify({"success": False, "message": "Forbidden"}), 403

            # Create multi-sig approval request
            approval_result = multisig_service.create_approval_request(
                community_id=community_id,
                operation_type="PAYOUT",
                amount=float(amount),
                currency=currency,
                destination=destination,
                description=data.get("description", f"Payout via {provider}"),
                created_by=user.id,
                required_signatures=2,  # Default: 2 of N
            )

            if not approval_result.get("success"):
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": approval_result.get(
                                "message", "Failed to create approval"
                            ),
                        }
                    ),
                    400,
                )

            # Create pending payment record linked to approval
            payment = Payment(
                payee_wallet_id=from_wallet_id,
                amount=Decimal(str(amount)),
                currency=currency,
                status="PENDING_APPROVAL",
                method=method,
                provider=provider.upper(),
            )
            db.session.add(payment)
            db.session.flush()

            # Link payment to approval (via operation_ref)
            approval = MultiSigApproval.query.get(approval_result["approval_id"])
            if approval:
                approval.operation_ref = f"PAYMENT-{payment.id}"

            db.session.commit()

            return (
                jsonify(
                    {
                        "success": True,
                        "approval_id": approval_result["approval_id"],
                        "payment_id": payment.id,
                        "status": "PENDING_APPROVAL",
                        "message": "Payout requires multi-signature approval",
                    }
                ),
                202,
            )  # Accepted but pending
        else:
            # For personal wallets, execute immediately (no multi-sig)
            payment = Payment(
                payee_wallet_id=from_wallet_id,
                amount=Decimal(str(amount)),
                currency=currency,
                status="PENDING",
                method=method,
                provider=provider.upper(),
            )
            db.session.add(payment)
            db.session.flush()

            adapter = provider_service.get_adapter(provider)
            if not adapter:
                return (
                    jsonify({"success": False, "message": "Provider not available"}),
                    400,
                )

            # Execute payout
            reference = f"PAYOUT-{payment.id}"
            result = adapter.payout(
                phone=destination,
                amount=Decimal(str(amount)),
                currency=currency,
                reference=reference,
            )

            if result.success:
                payment.provider_ref = result.provider_ref
                payment.status = "SUCCESS"
                # Deduct from wallet (or use ledger posting)
                wallet.balance -= Decimal(str(amount))
                db.session.commit()
                return jsonify({"success": True, "payment_id": payment.id}), 200
            else:
                payment.status = "FAILED"
                db.session.commit()
                return jsonify({"success": False, "message": result.message}), 400

    except Exception as e:
        db.session.rollback()
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"An error occurred while processing your request: {str(e)}",
                }
            ),
            500,
        )


@api_v1_bp.route("/payouts/<int:approval_id>/execute", methods=["POST"])
@jwt_required()
def execute_approved_payout(approval_id: int):
    """Execute an approved payout"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        approval = MultiSigApproval.query.get(approval_id)
        if not approval:
            return jsonify({"success": False, "message": "Approval not found"}), 404

        if approval.status != "APPROVED":
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Approval not approved. Current status: {approval.status}",
                    }
                ),
                400,
            )

        if approval.operation_type != "PAYOUT":
            return jsonify({"success": False, "message": "Not a payout approval"}), 400

        # Find payment from operation_ref
        if not approval.operation_ref or not approval.operation_ref.startswith(
            "PAYMENT-"
        ):
            return (
                jsonify({"success": False, "message": "Invalid approval reference"}),
                400,
            )

        payment_id = int(approval.operation_ref.replace("PAYMENT-", ""))
        payment = Payment.query.get(payment_id)

        if not payment:
            return jsonify({"success": False, "message": "Payment not found"}), 404

        if payment.status != "PENDING_APPROVAL":
            return (
                jsonify({"success": False, "message": "Payment already processed"}),
                400,
            )

        wallet = Wallet.query.get(payment.payee_wallet_id)
        if not wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        # Execute payout via provider
        adapter = provider_service.get_adapter(payment.provider)
        if not adapter:
            return jsonify({"success": False, "message": "Provider not available"}), 400

        # Get destination from approval
        destination = approval.destination
        reference = f"PAYOUT-{payment.id}"

        result = adapter.payout(
            phone=destination,
            amount=payment.amount,
            currency=payment.currency,
            reference=reference,
        )

        if result.success:
            payment.provider_ref = result.provider_ref
            payment.status = "SUCCESS"
            wallet.balance -= payment.amount

            # Mark approval as executed
            multisig_service.execute_approval(approval_id, executed_by=user.id)

            db.session.commit()

            return (
                jsonify(
                    {
                        "success": True,
                        "payment_id": payment.id,
                        "approval_id": approval_id,
                        "message": "Payout executed successfully",
                    }
                ),
                200,
            )
        else:
            payment.status = "FAILED"
            db.session.commit()
            return jsonify({"success": False, "message": result.message}), 400

    except Exception as e:
        db.session.rollback()
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Execution failed: {str(e)}",
                }
            ),
            500,
        )
