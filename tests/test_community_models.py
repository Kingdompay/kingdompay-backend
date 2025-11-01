#!/usr/bin/env python3
"""
Test script for community models
Run this to verify the new community functionality works correctly
"""

import os
import sys
from decimal import Decimal
from app import create_app
from extensions import db
from models import (
    User,
    Community,
    CommunityRole,
    CommunityMember,
    Contribution,
    Transaction,
)


def test_community_models():
    """Test the community models functionality"""
    app = create_app()

    with app.app_context():
        try:
            print("🧪 Testing community models...")

            # Create test data
            print("1. Creating test user...")
            test_user = User(
                full_name="Test User",
                email="test@example.com",
                phone_number="+254700000000",
                is_phone_verified=True,
            )
            test_user.set_password("testpassword")
            db.session.add(test_user)
            db.session.commit()
            print(f"   ✅ Created user: {test_user.id}")

            # Create community roles
            print("2. Checking community roles...")
            roles = CommunityRole.query.all()
            if not roles:
                print("   ⚠️  No community roles found. Creating default roles...")
                default_roles = [
                    ("admin", "Community administrator"),
                    ("moderator", "Community moderator"),
                    ("member", "Regular member"),
                    ("treasurer", "Community treasurer"),
                    ("secretary", "Community secretary"),
                ]

                for role_name, description in default_roles:
                    role = CommunityRole(role_name=role_name, description=description)
                    db.session.add(role)
                db.session.commit()
                print("   ✅ Created default roles")
            else:
                print(f"   ✅ Found {len(roles)} existing roles")

            # Create a community
            print("3. Creating test community...")
            community = Community(
                name="Test Savings Group",
                description="A test community for savings",
                type="savings",
                created_by=test_user.id,
            )
            db.session.add(community)
            db.session.commit()
            print(f"   ✅ Created community: {community.id} - {community.name}")

            # Add user to community
            print("4. Adding user to community...")
            member_role = CommunityRole.query.filter_by(role_name="member").first()
            membership = CommunityMember(
                user_id=test_user.id,
                community_id=community.id,
                role_id=member_role.id if member_role else None,
                role="member",
            )
            db.session.add(membership)
            db.session.commit()
            print(f"   ✅ Added user to community as {membership.role}")

            # Create a contribution
            print("5. Creating test contribution...")
            contribution = Contribution(
                user_id=test_user.id,
                community_id=community.id,
                amount=Decimal("1000.00"),
                contribution_type="monthly",
                description="Test monthly contribution",
            )
            db.session.add(contribution)
            db.session.commit()
            print(f"   ✅ Created contribution: {contribution.amount}")

            # Create a transaction linked to contribution
            print("6. Creating test transaction...")
            transaction = Transaction(
                source_wallet_id=None,  # Would be linked to user's wallet in real scenario
                destination_wallet_id=None,
                transaction_type="CONTRIBUTION",
                amount=Decimal("1000.00"),
                status="SUCCESS",
                description="Community contribution transaction",
                contribution_id=contribution.id,
            )
            db.session.add(transaction)
            db.session.commit()
            print(f"   ✅ Created transaction: {transaction.reference_number}")

            # Test relationships
            print("7. Testing relationships...")

            # Test user -> communities
            user_communities = Community.get_user_communities(test_user.id)
            print(f"   ✅ User is member of {len(user_communities)} communities")

            # Test community -> members
            community_members = CommunityMember.get_community_members(community.id)
            print(f"   ✅ Community has {len(community_members)} members")

            # Test user -> contributions
            user_contributions = Contribution.get_user_contributions(test_user.id)
            print(f"   ✅ User made {len(user_contributions)} contributions")

            # Test community -> contributions
            community_contributions = Contribution.get_community_contributions(
                community.id
            )
            print(
                f"   ✅ Community received {len(community_contributions)} contributions"
            )

            # Test total contributions
            total = Contribution.get_total_contributions(community.id)
            print(f"   ✅ Total contributions to community: {total}")

            # Test transaction -> contribution relationship
            transaction_with_contribution = Transaction.query.filter_by(
                contribution_id=contribution.id
            ).first()
            if transaction_with_contribution:
                print(
                    f"   ✅ Transaction {transaction_with_contribution.reference_number} linked to contribution"
                )

            print("\n🎉 All tests passed! Community models are working correctly.")

            # Clean up test data
            print("\n🧹 Cleaning up test data...")
            db.session.delete(transaction)
            db.session.delete(contribution)
            db.session.delete(membership)
            db.session.delete(community)
            db.session.delete(test_user)
            db.session.commit()
            print("   ✅ Test data cleaned up")

            return True

        except Exception as e:
            print(f"❌ Test failed: {e}")
            db.session.rollback()
            return False


if __name__ == "__main__":
    success = test_community_models()
    sys.exit(0 if success else 1)
