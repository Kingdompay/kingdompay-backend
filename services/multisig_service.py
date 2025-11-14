"""
Multi-signature Service: Handle community wallet approvals
"""

from datetime import datetime
from typing import Dict, Any, Optional
from flask import current_app, request
from extensions import db
from models.multisig import MultiSigApproval, MultiSigSignature
from models.community import CommunityMember, CommunityRole
from models.wallet import Wallet
from services.rbac import is_community_admin


class MultiSigService:
    """Service for multi-signature approval management"""

    def create_approval_request(
        self,
        community_id: int,
        operation_type: str,
        amount: float,
        currency: str,
        destination: str,
        description: str,
        created_by: int,
        operation_ref: Optional[str] = None,
        required_signatures: int = 2,
    ) -> Dict[str, Any]:
        """
        Create a multi-signature approval request
        
        Args:
            community_id: Community ID
            operation_type: WITHDRAWAL|PAYOUT|DISBURSEMENT
            amount: Amount to withdraw/payout
            currency: Currency code
            destination: Destination (phone, account, etc.)
            description: Description of the operation
            created_by: User ID creating the request
            operation_ref: Reference to related operation (payment_id, etc.)
            required_signatures: Number of signatures required (default 2 of N)
        """
        # Verify creator is admin/treasurer
        if not is_community_admin(created_by, community_id):
            return {
                "success": False,
                "message": "Only community admins/treasurers can create approval requests",
            }

        # Get count of eligible signers
        eligible_signers = CommunityMember.query.filter(
            CommunityMember.community_id == community_id,
            CommunityMember.role.in_([CommunityRole.ADMIN.value, CommunityRole.TREASURER.value]),
            CommunityMember.status == "ACTIVE",
        ).count()

        if eligible_signers < required_signatures:
            return {
                "success": False,
                "message": f"Not enough eligible signers. Need {required_signatures}, have {eligible_signers}",
            }

        approval = MultiSigApproval(
            community_id=community_id,
            operation_type=operation_type,
            operation_ref=operation_ref,
            amount=amount,
            currency=currency,
            destination=destination,
            description=description,
            status="PENDING",
            required_signatures=required_signatures,
            approval_count=0,
            created_by=created_by,
        )
        db.session.add(approval)
        db.session.commit()

        return {
            "success": True,
            "approval_id": approval.id,
            "status": approval.status,
            "required_signatures": approval.required_signatures,
        }

    def sign_approval(self, approval_id: int, user_id: int, signature_type: str = "APPROVE") -> Dict[str, Any]:
        """
        Sign an approval request
        
        Args:
            approval_id: Approval request ID
            user_id: User signing
            signature_type: APPROVE|REJECT
        """
        approval = MultiSigApproval.query.get(approval_id)
        if not approval:
            return {"success": False, "message": "Approval request not found"}

        # Verify user is eligible to sign
        if not is_community_admin(user_id, approval.community_id):
            return {
                "success": False,
                "message": "Only community admins/treasurers can sign",
            }

        # Check if already signed
        existing_signature = MultiSigSignature.query.filter_by(
            approval_id=approval_id,
            user_id=user_id,
        ).first()

        if existing_signature:
            return {
                "success": False,
                "message": "You have already signed this approval",
            }

        # Create signature
        signature = MultiSigSignature(
            approval_id=approval_id,
            user_id=user_id,
            signature_type=signature_type,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get("User-Agent") if request else None,
        )
        db.session.add(signature)

        # Update approval count
        if signature_type == "APPROVE":
            approval.approval_count += 1
        elif signature_type == "REJECT":
            approval.status = "REJECTED"
            approval.approved_at = datetime.utcnow()

        # Check if approved (enough signatures)
        if approval.approval_count >= approval.required_signatures and approval.status == "PENDING":
            approval.status = "APPROVED"
            approval.approved_at = datetime.utcnow()

        db.session.commit()

        return {
            "success": True,
            "approval_id": approval_id,
            "status": approval.status,
            "approval_count": approval.approval_count,
            "required_signatures": approval.required_signatures,
            "message": "Approved" if approval.status == "APPROVED" else "Signature recorded",
        }

    def execute_approval(self, approval_id: int, executed_by: int) -> Dict[str, Any]:
        """
        Execute an approved request (after multi-sig approval)
        """
        approval = MultiSigApproval.query.get(approval_id)
        if not approval:
            return {"success": False, "message": "Approval request not found"}

        if approval.status != "APPROVED":
            return {
                "success": False,
                "message": f"Approval not ready. Status: {approval.status}",
            }

        if approval.executed_at:
            return {"success": False, "message": "Already executed"}

        # Mark as executed
        approval.executed_at = datetime.utcnow()
        approval.status = "EXECUTED"
        db.session.commit()

        return {
            "success": True,
            "approval_id": approval_id,
            "message": "Approval executed",
        }

    def get_approval_status(self, approval_id: int) -> Dict[str, Any]:
        """Get approval status and signatures"""
        approval = MultiSigApproval.query.get(approval_id)
        if not approval:
            return {"success": False, "message": "Approval not found"}

        signatures = MultiSigSignature.query.filter_by(approval_id=approval_id).all()

        return {
            "success": True,
            "approval": approval.to_dict(),
            "signatures": [s.to_dict() for s in signatures],
            "pending_signatures": approval.required_signatures - approval.approval_count,
        }

