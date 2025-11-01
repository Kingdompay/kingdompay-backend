"""
Simple RBAC helpers for community roles
"""

from models.community import CommunityMember, CommunityRole


def is_community_admin(user_id: int, community_id: int) -> bool:
    m = CommunityMember.query.filter_by(
        community_id=community_id, user_id=user_id
    ).first()
    return bool(
        m and m.role in (CommunityRole.ADMIN.value, CommunityRole.TREASURER.value)
    )


def is_community_treasurer(user_id: int, community_id: int) -> bool:
    m = CommunityMember.query.filter_by(
        community_id=community_id, user_id=user_id
    ).first()
    return bool(m and m.role == CommunityRole.TREASURER.value)
