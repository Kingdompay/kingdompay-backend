"""
Savings routes for KingdomPay API v1
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required
from datetime import datetime
from decimal import Decimal
from routes import api_v1_bp
from services.auth_service import AuthService
from services.ledger_service import LedgerService
from services.transfer_service import TransferService
from models.savings_goal import SavingsGoal
from models.wallet import Wallet
from models.transaction import Transaction
from extensions import db

auth_service = AuthService()
ledger_service = LedgerService()
transfer_service = TransferService()


@api_v1_bp.route("/savings/goals", methods=["GET"])
@jwt_required()
def get_savings_goals():
    """
    Get all savings goals for the current user
    """
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        goals = SavingsGoal.query.filter_by(user_id=user.id).order_by(
            SavingsGoal.created_at.desc()
        ).all()

        return jsonify({
            "success": True,
            "goals": [goal.to_dict() for goal in goals]
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your request"
        }), 500


@api_v1_bp.route("/savings/goals", methods=["POST"])
@jwt_required()
def create_savings_goal():
    """
    Create a new savings goal
    """
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        data = request.get_json() or {}
        name = data.get("name")
        target_amount = data.get("target_amount") or data.get("targetAmount")
        icon = data.get("icon", "savings")
        deadline = data.get("deadline")
        currency = data.get("currency", "KES")

        if not name:
            return jsonify({"success": False, "message": "Goal name is required"}), 400

        if not target_amount:
            return jsonify({"success": False, "message": "Target amount is required"}), 400

        try:
            target_amount_decimal = Decimal(str(target_amount))
            if target_amount_decimal <= 0:
                return jsonify({"success": False, "message": "Target amount must be greater than 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid target amount"}), 400

        # Parse deadline if provided
        deadline_datetime = None
        if deadline:
            try:
                deadline_datetime = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return jsonify({"success": False, "message": "Invalid deadline format"}), 400

        goal = SavingsGoal(
            user_id=user.id,
            name=name,
            target_amount=target_amount_decimal,
            current_amount=Decimal("0.00"),
            currency=currency,
            icon=icon,
            deadline=deadline_datetime,
            status="active"
        )

        db.session.add(goal)
        db.session.commit()

        return jsonify({
            "success": True,
            "goal": goal.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your request"
        }), 500


@api_v1_bp.route("/savings/goals/<int:goal_id>", methods=["GET"])
@jwt_required()
def get_savings_goal(goal_id):
    """
    Get a specific savings goal
    """
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user.id).first()
        if not goal:
            return jsonify({"success": False, "message": "Goal not found"}), 404

        return jsonify({
            "success": True,
            "goal": goal.to_dict()
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your request"
        }), 500


@api_v1_bp.route("/savings/goals/<int:goal_id>", methods=["PUT"])
@jwt_required()
def update_savings_goal(goal_id):
    """
    Update a savings goal
    """
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user.id).first()
        if not goal:
            return jsonify({"success": False, "message": "Goal not found"}), 404

        data = request.get_json() or {}
        
        if "name" in data:
            goal.name = data["name"]
        if "target_amount" in data or "targetAmount" in data:
            target = data.get("target_amount") or data.get("targetAmount")
            try:
                goal.target_amount = Decimal(str(target))
            except (ValueError, TypeError):
                return jsonify({"success": False, "message": "Invalid target amount"}), 400
        if "icon" in data:
            goal.icon = data["icon"]
        if "deadline" in data:
            deadline = data["deadline"]
            if deadline:
                try:
                    goal.deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    return jsonify({"success": False, "message": "Invalid deadline format"}), 400
            else:
                goal.deadline = None
        if "status" in data:
            goal.status = data["status"]

        goal.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "success": True,
            "goal": goal.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your request"
        }), 500


@api_v1_bp.route("/savings/goals/<int:goal_id>", methods=["DELETE"])
@jwt_required()
def delete_savings_goal(goal_id):
    """
    Delete a savings goal
    """
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user.id).first()
        if not goal:
            return jsonify({"success": False, "message": "Goal not found"}), 404

        db.session.delete(goal)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Goal deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your request"
        }), 500


@api_v1_bp.route("/savings/goals/<int:goal_id>/contribute", methods=["POST"])
@jwt_required()
def contribute_to_goal(goal_id):
    """
    Contribute money to a savings goal from wallet
    """
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user.id).first()
        if not goal:
            return jsonify({"success": False, "message": "Goal not found"}), 404

        if goal.status != "active":
            return jsonify({"success": False, "message": "Cannot contribute to inactive goal"}), 400

        data = request.get_json() or {}
        amount = data.get("amount")

        if not amount:
            return jsonify({"success": False, "message": "Amount is required"}), 400

        try:
            amount_decimal = Decimal(str(amount))
            if amount_decimal <= 0:
                return jsonify({"success": False, "message": "Amount must be greater than 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid amount"}), 400

        # Get user wallet
        wallet = Wallet.find_by_user_id(user.id)
        if not wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        # Check if wallet has sufficient balance
        if wallet.balance < amount_decimal:
            return jsonify({"success": False, "message": "Insufficient balance"}), 400

        # Check if goal is already completed
        if goal.is_completed():
            return jsonify({"success": False, "message": "Goal is already completed"}), 400

        # Deduct from wallet and create transaction
        try:
            transaction = wallet.deduct_funds(
                amount_decimal,
                description=f"Contribution to savings goal: {goal.name}"
            )
            
            # Update goal current amount
            goal.current_amount += amount_decimal
            goal.update_status()  # Check if goal is completed
            db.session.commit()
        except ValueError as e:
            db.session.rollback()
            return jsonify({
                "success": False,
                "message": str(e)
            }), 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(f"Error contributing to goal {goal_id}: {str(e)}")
            return jsonify({
                "success": False,
                "message": "Failed to process contribution"
            }), 500

        return jsonify({
            "success": True,
            "goal": goal.to_dict(),
            "transaction_id": transaction.id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your request"
        }), 500


@api_v1_bp.route("/savings/goals/<int:goal_id>/withdraw", methods=["POST"])
@jwt_required()
def withdraw_from_goal(goal_id):
    """
    Withdraw money from a savings goal back to wallet
    """
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user.id).first()
        if not goal:
            return jsonify({"success": False, "message": "Goal not found"}), 404

        data = request.get_json() or {}
        amount = data.get("amount")

        if not amount:
            return jsonify({"success": False, "message": "Amount is required"}), 400

        try:
            amount_decimal = Decimal(str(amount))
            if amount_decimal <= 0:
                return jsonify({"success": False, "message": "Amount must be greater than 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid amount"}), 400

        # Check if goal has sufficient balance
        if goal.current_amount < amount_decimal:
            return jsonify({"success": False, "message": "Insufficient funds in goal"}), 400

        # Get user wallet
        wallet = Wallet.find_by_user_id(user.id)
        if not wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        # Add funds to wallet and create transaction
        try:
            transaction = wallet.add_funds(
                amount_decimal,
                description=f"Withdrawal from savings goal: {goal.name}"
            )
            
            # Update goal current amount
            goal.current_amount -= amount_decimal
            if goal.current_amount < 0:
                goal.current_amount = Decimal("0.00")
            goal.updated_at = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(f"Error withdrawing from goal {goal_id}: {str(e)}")
            return jsonify({
                "success": False,
                "message": "Failed to process withdrawal"
            }), 500

        return jsonify({
            "success": True,
            "goal": goal.to_dict(),
            "transaction_id": transaction.id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your request"
        }), 500
