"""
Simple RBAC helpers for community roles
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from models.community import CommunityMember, CommunityRole
from models.user import User


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


def require_admin(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        # Check if user has admin role
        if not user.is_admin():
            return jsonify({"success": False, "message": "Admin access required"}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def require_support(f):
    """Decorator to require support or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        # Check if user has support or admin role
        if not user.is_support():
            return jsonify({"success": False, "message": "Support access required"}), 403
        
        return f(*args, **kwargs)
    return decorated_function
