"""
Transfer Service: Enhanced transfer with fee and contribution handling
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from flask import current_app
from extensions import db
from models.wallet import Wallet
from models.payment import Payment
from services.ledger_service import LedgerService
from services.fee_service import FeeService
from services.risk_service import RiskService
from services.wallet_service import WalletService


class TransferService:
    """Service for handling transfers with fees and contributions"""

    def __init__(self):
        self.ledger_service = LedgerService()
        self.fee_service = FeeService()
        self.risk_service = RiskService()
        self.wallet_service = WalletService()

    def process_transfer(
        self,
        *,
        from_wallet_id: int,
        to_wallet_id: int,
        amount: Decimal,
        currency: str,
        memo: Optional[str],
        idempotency_key: str,
        user_id: Optional[int] = None,
        external_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process transfer with fee calculation and allocation

        Steps:
        1. Validate transaction limits
        2. Detect community involvement
        3. Calculate fees and contributions
        4. Validate sufficient balance (amount + fees + contributions)
        5. Post main transfer journal
        6. Allocate fees (platform, community, federal)
        7. Allocate contributions (if community involved)
        8. Create fee and contribution records
        """
        try:
            amt = Decimal(str(amount))

            # Step 1: Get wallets first
            from_wallet = Wallet.query.get(from_wallet_id)
            to_wallet = Wallet.query.get(to_wallet_id)

            if not from_wallet or not to_wallet:
                return {"success": False, "message": "Wallet not found"}

            # Step 2: Validate transaction limits
            limit_check = self.fee_service.validate_transaction_limits(
                amt, user_id=user_id
            )
            if not limit_check.get("allowed"):
                return {
                    "success": False,
                    "message": limit_check.get("message", "Transaction limit exceeded"),
                }

            # Step 2.5: Risk checks (minimal destination context to avoid heavy joins)
            destination_info = None

            risk_check = self.risk_service.check_transaction_risk(
                user_id=user_id,
                wallet_id=from_wallet_id,
                amount=amt,
                destination=destination_info,
            )

            if not risk_check.get("allowed"):
                # High risk - create AML case but block transaction
                if risk_check.get("risk_score", 0) >= 80:
                    self.risk_service.create_aml_case(
                        user_id=user_id,
                        case_type="HIGH_RISK_TRANSACTION",
                        details={
                            "amount": float(amt),
                            "from_wallet_id": from_wallet_id,
                            "to_wallet_id": to_wallet_id,
                            "risk_score": risk_check.get("risk_score"),
                            "warnings": risk_check.get("warnings", []),
                        },
                    )
                return {
                    "success": False,
                    "message": risk_check.get(
                        "reason", "Transaction blocked by risk system"
                    ),
                    "risk_score": risk_check.get("risk_score"),
                    "warnings": risk_check.get("warnings", []),
                }

            # Step 3: Validate wallets and detect community involvement
            if from_wallet.currency != currency or to_wallet.currency != currency:
                return {"success": False, "message": "Currency mismatch"}

            if from_wallet_id == to_wallet_id:
                return {
                    "success": False,
                    "message": "Cannot transfer to the same wallet",
                }

            # Detect community involvement
            community_id = None
            from_community_id = None
            to_community_id = None

            from_owner_type = getattr(from_wallet, "owner_type", "USER")
            to_owner_type = getattr(to_wallet, "owner_type", "USER")

            if from_owner_type == "COMMUNITY":
                from_community_id = getattr(from_wallet, "owner_id", None)
                community_id = from_community_id
            elif to_owner_type == "COMMUNITY":
                to_community_id = getattr(to_wallet, "owner_id", None)
                community_id = to_community_id

            # Step 4: Calculate fees and contributions
            fee_breakdown = self.fee_service.calculate_fees(
                amt, community_id=community_id
            )
            contribution_breakdown = None

            if community_id:
                contribution_breakdown = self.fee_service.calculate_contribution(
                    amt, community_id
                )

            total_deduction = amt + Decimal(str(fee_breakdown["fee_amount"]))
            if contribution_breakdown:
                total_deduction += Decimal(
                    str(contribution_breakdown["contribution_amount"])
                )

            # Step 5: Validate sufficient balance
            if Decimal(from_wallet.balance) < total_deduction:
                return {
                    "success": False,
                    "message": f"Insufficient funds. Required: {total_deduction}, Available: {from_wallet.balance}",
                }

            # Step 6: Post main transfer journal
            transfer_result = self.ledger_service.post_transfer(
                from_wallet_id=from_wallet_id,
                to_wallet_id=to_wallet_id,
                amount=amt,
                currency=currency,
                memo=memo,
                idempotency_key=idempotency_key,
                external_ref=external_ref,
            )

            if not transfer_result.get("success"):
                return transfer_result

            journal_id = transfer_result.get("journal_id")

            # Step 7: Allocate fees
            fee_record = self.fee_service.allocate_fees(
                journal_id=journal_id,
                payment_id=None,
                amount=amt,
                community_id=community_id,
            )

            # Post fee allocation journal entries
            platform_wallet = self.wallet_service.get_or_create_platform_wallet()
            federal_wallet = self.wallet_service.get_or_create_federal_wallet()

            # Platform fee allocation
            if fee_breakdown["platform_fee"] > 0:
                self._allocate_fee_to_wallet(
                    journal_id=journal_id,
                    from_wallet_id=from_wallet_id,
                    to_wallet_id=platform_wallet.id,
                    amount=Decimal(str(fee_breakdown["platform_fee"])),
                    currency=currency,
                    fee_type="PLATFORM",
                )

            # Federal fee allocation
            if fee_breakdown["federal_fee"] > 0:
                self._allocate_fee_to_wallet(
                    journal_id=journal_id,
                    from_wallet_id=from_wallet_id,
                    to_wallet_id=federal_wallet.id,
                    amount=Decimal(str(fee_breakdown["federal_fee"])),
                    currency=currency,
                    fee_type="FEDERAL",
                )

            # Community fee allocation
            if fee_breakdown["community_fee"] > 0 and community_id:
                community_wallet = self.wallet_service.get_or_create_community_wallet(
                    community_id
                )
                if community_wallet:
                    self._allocate_fee_to_wallet(
                        journal_id=journal_id,
                        from_wallet_id=from_wallet_id,
                        to_wallet_id=community_wallet.id,
                        amount=Decimal(str(fee_breakdown["community_fee"])),
                        currency=currency,
                        fee_type="COMMUNITY",
                    )

            # Step 8: Allocate contributions
            if contribution_breakdown and community_id:
                contribution_record = self.fee_service.allocate_contribution(
                    journal_id=journal_id,
                    payment_id=None,
                    amount=amt,
                    community_id=community_id,
                    allocated_to="GENERAL",  # Default, can be configured
                )

                # Post contribution allocation journal entry
                # Contributions go to CDF, which is tracked separately
                # but we still need to deduct from source wallet
                from models.ledger_entry import LedgerEntry

                contribution_entry = LedgerEntry(
                    journal_id=journal_id,
                    wallet_id=from_wallet_id,
                    account_code="CDF_CONTRIBUTION",
                    debit=Decimal("0.00"),
                    credit=Decimal(str(contribution_breakdown["contribution_amount"])),
                    currency=currency,
                    meta={
                        "contribution_id": contribution_record.id,
                        "community_id": community_id,
                    },
                )
                db.session.add(contribution_entry)
                from_wallet.balance -= Decimal(
                    str(contribution_breakdown["contribution_amount"])
                )

            db.session.commit()

            return {
                "success": True,
                "status": "posted",
                "journal_id": journal_id,
                "transfer_amount": float(amt),
                "fee_breakdown": fee_breakdown,
                "contribution_breakdown": contribution_breakdown,
                "total_deduction": float(total_deduction),
            }

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Transfer processing failed")
            return {"success": False, "message": f"Transfer failed: {str(e)}"}

    def _allocate_fee_to_wallet(
        self,
        journal_id: int,
        from_wallet_id: int,
        to_wallet_id: int,
        amount: Decimal,
        currency: str,
        fee_type: str,
    ):
        """Create ledger entries for fee allocation"""
        from models.ledger_entry import LedgerEntry
        from models.wallet import Wallet

        # Credit from source wallet (deduct fee)
        credit_entry = LedgerEntry(
            journal_id=journal_id,
            wallet_id=from_wallet_id,
            account_code=f"FEES_{fee_type}",
            debit=Decimal("0.00"),
            credit=amount,
            currency=currency,
            meta={"fee_type": fee_type},
        )

        # Debit to fee wallet (add fee)
        debit_entry = LedgerEntry(
            journal_id=journal_id,
            wallet_id=to_wallet_id,
            account_code=f"{fee_type}_FEES",
            debit=amount,
            credit=Decimal("0.00"),
            currency=currency,
            meta={"fee_type": fee_type},
        )

        db.session.add_all([credit_entry, debit_entry])

        # Update wallet balances
        from_wallet = Wallet.query.get(from_wallet_id)
        to_wallet = Wallet.query.get(to_wallet_id)

        if from_wallet:
            from_wallet.balance -= amount
        if to_wallet:
            to_wallet.balance += amount
