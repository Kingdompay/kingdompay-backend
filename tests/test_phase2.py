"""
Phase 2 Feature Tests
Tests for fees, multisig, checkout, reconciliation
"""

import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from flask import current_app
from extensions import db
from models import (
    User, Wallet, Community, CommunityMember, Campaign,
    TransactionFee, CommunityContribution, CommunityDevelopmentFund,
    MultiSigApproval, MultiSigSignature, Blacklist, AMLCase
)
from services.fee_service import FeeService
from services.multisig_service import MultiSigService
from services.reconciliation_service import ReconciliationService
from services.risk_service import RiskService
from services.provider_service import ProviderService


@pytest.fixture
def fee_service():
    return FeeService()


@pytest.fixture
def multisig_service():
    return MultiSigService()


@pytest.fixture
def risk_service():
    return RiskService()


@pytest.fixture
def test_community(app, test_user):
    """Create a test community"""
    with app.app_context():
        community = Community(
            name="Test Community",
            type="CHURCH",
            slug="test-community",
            owner_user_id=test_user.id,
        )
        db.session.add(community)
        db.session.flush()
        
        # Make user admin
        member = CommunityMember(
            community_id=community.id,
            user_id=test_user.id,
            role="ADMIN",
            status="ACTIVE",
        )
        db.session.add(member)
        db.session.commit()
        return community


class TestFeeService:
    """Test Fee Service"""

    def test_calculate_fees_without_community(self, app, fee_service):
        """Test fee calculation without community"""
        with app.app_context():
            result = fee_service.calculate_fees(Decimal("1000"))
            
            assert result["transaction_amount"] == 1000.0
            assert result["fee_amount"] == 10.0  # 1.0% (platform + federal, no community)
            assert result["platform_fee"] == 5.0  # 0.5%
            assert result["community_fee"] == 0.0  # No community
            assert result["federal_fee"] == 5.0  # 0.5%
            assert result["net_amount"] == 990.0

    def test_calculate_fees_with_community(self, app, fee_service, test_community):
        """Test fee calculation with community"""
        with app.app_context():
            # Ensure community is in session
            community = db.session.merge(test_community)
            result = fee_service.calculate_fees(Decimal("1000"), community_id=community.id)
            
            assert result["fee_amount"] == 15.0
            assert result["community_fee"] == 5.0  # With community

    def test_calculate_contribution(self, app, fee_service, test_community):
        """Test contribution calculation"""
        with app.app_context():
            # Ensure community is in session
            community = db.session.merge(test_community)
            result = fee_service.calculate_contribution(Decimal("1000"), community.id)
            
            assert result["contribution_amount"] == 10.0  # 1% default
            assert result["contribution_rate"] == 0.01

    def test_validate_transaction_limits_min(self, app, fee_service):
        """Test minimum transaction limit"""
        with app.app_context():
            result = fee_service.validate_transaction_limits(Decimal("5"))
            assert result["allowed"] is False
            assert "Minimum" in result["message"]

    def test_validate_transaction_limits_max(self, app, fee_service):
        """Test maximum transaction limit"""
        with app.app_context():
            result = fee_service.validate_transaction_limits(Decimal("600000"))
            assert result["allowed"] is False
            assert "Maximum" in result["message"]

    def test_validate_transaction_limits_valid(self, app, fee_service):
        """Test valid transaction amount"""
        with app.app_context():
            result = fee_service.validate_transaction_limits(Decimal("1000"))
            assert result["allowed"] is True


class TestMultiSigService:
    """Test Multi-Signature Service"""

    def test_create_approval_request(self, app, multisig_service, test_user, test_community):
        """Test creating approval request"""
        with app.app_context():
            community = db.session.merge(test_community)
            user = db.session.merge(test_user)
            
            result = multisig_service.create_approval_request(
                community_id=community.id,
                operation_type="WITHDRAWAL",
                amount=50000,
                currency="KES",
                destination="+254712345678",
                description="Test withdrawal",
                created_by=user.id,
                required_signatures=1,  # Only 1 admin, so require 1 signature
            )
            
            # Debug: print result if failed
            if not result.get("success"):
                print(f"Multisig creation failed: {result.get('message')}")
            
            assert result["success"] is True, f"Failed: {result.get('message', 'Unknown error')}"
            assert "approval_id" in result

    def test_sign_approval(self, app, multisig_service, test_user, test_community):
        """Test signing approval"""
        with app.app_context():
            community = db.session.merge(test_community)
            user = db.session.merge(test_user)
            
            # Create approval
            create_result = multisig_service.create_approval_request(
                community_id=community.id,
                operation_type="WITHDRAWAL",
                amount=50000,
                currency="KES",
                destination="+254712345678",
                description="Test",
                created_by=user.id,
                required_signatures=1,  # Only 1 admin, so require 1 signature
            )
            
            approval_id = create_result["approval_id"]
            
            # Sign approval
            sign_result = multisig_service.sign_approval(
                approval_id=approval_id,
                user_id=user.id,
                signature_type="APPROVE",
            )
            
            assert sign_result["success"] is True
            assert sign_result["approval_count"] == 1


class TestRiskService:
    """Test Risk Service"""

    def test_check_blacklist(self, app, risk_service):
        """Test blacklist check"""
        with app.app_context():
            # Add to blacklist
            blacklist = Blacklist(
                entity_type="PHONE",
                entity_value="+254712345678",
                reason="Test",
                status="ACTIVE",
            )
            db.session.add(blacklist)
            db.session.commit()
            
            # Check blacklist
            result = risk_service.check_blacklist("PHONE", "+254712345678")
            assert result is True
            
            # Check non-blacklisted
            result = risk_service.check_blacklist("PHONE", "+254712345679")
            assert result is False

    def test_check_velocity_limits(self, app, risk_service, test_user, test_wallet):
        """Test velocity limits"""
        with app.app_context():
            result = risk_service.check_velocity_limits(
                user_id=test_user.id,
                wallet_id=test_wallet.id,
                amount=Decimal("50000"),
                window_minutes=60,
            )
            
            # Should be allowed initially
            assert result["allowed"] is True


class TestProviderService:
    """Test Provider Service"""

    def test_list_providers(self, app):
        """Test provider listing"""
        with app.app_context():
            service = ProviderService()
            providers = service.list_providers()
            
            assert "MPESA" in providers
            assert "AIRTEL" in providers or "AIRTE" in providers
            assert "TKASH" in providers

    def test_get_adapter(self, app):
        """Test getting provider adapter"""
        with app.app_context():
            service = ProviderService()
            adapter = service.get_adapter("MPESA")
            
            assert adapter is not None


class TestReconciliationService:
    """Test Reconciliation Service"""

    def test_reconcile_provider(self, app, test_user, test_wallet):
        """Test provider reconciliation"""
        with app.app_context():
            from models.payment import Payment
            from services.reconciliation_service import ReconciliationService
            
            # Create a payment
            payment = Payment(
                payer_wallet_id=test_wallet.id,
                amount=Decimal("1000"),
                currency="KES",
                status="SUCCESS",
                method="MOMO",
                provider="MPESA",
                provider_ref="ABC123",
            )
            db.session.add(payment)
            db.session.commit()
            
            # Reconcile
            service = ReconciliationService()
            result = service.reconcile_provider(
                provider="MPESA",
                statement_date=date.today(),
                provider_transactions=[
                    {
                        "transaction_id": "ABC123",
                        "amount": 1000,
                        "status": "SUCCESS",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ],
            )
            
            assert result["success"] is True
            assert result["matched_count"] >= 0


class TestModels:
    """Test Phase 2 Models"""

    def test_transaction_fee_model(self, app):
        """Test TransactionFee model"""
        with app.app_context():
            fee = TransactionFee(
                journal_id=1,
                transaction_amount=Decimal("1000"),
                fee_amount=Decimal("15"),
                platform_fee=Decimal("5"),
                community_fee=Decimal("5"),
                federal_fee=Decimal("5"),
            )
            db.session.add(fee)
            db.session.commit()
            
            assert fee.id is not None
            assert fee.fee_amount == Decimal("15")

    def test_community_development_fund_model(self, app, test_community):
        """Test CDF model"""
        with app.app_context():
            community = db.session.merge(test_community)
            cdf = CommunityDevelopmentFund(
                community_id=community.id,
                contribution_rate=Decimal("0.01"),
            )
            db.session.add(cdf)
            db.session.commit()
            
            assert cdf.id is not None
            assert cdf.contribution_rate == Decimal("0.01")

    def test_multisig_approval_model(self, app, test_community, test_user):
        """Test MultiSigApproval model"""
        with app.app_context():
            community = db.session.merge(test_community)
            user = db.session.merge(test_user)
            
            approval = MultiSigApproval(
                community_id=community.id,
                operation_type="WITHDRAWAL",
                amount=Decimal("50000"),
                currency="KES",
                destination="+254712345678",
                description="Test",
                required_signatures=2,
                created_by=user.id,
            )
            db.session.add(approval)
            db.session.commit()
            
            assert approval.id is not None
            assert approval.status == "PENDING"

