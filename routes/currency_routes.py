"""
Currency routes for KingdomPay API v1
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from decimal import Decimal
from routes import api_v1_bp
from services.currency_service import CurrencyService

currency_service = CurrencyService()


@api_v1_bp.route("/currencies", methods=["GET"])
def get_currencies():
    """
    Get list of supported currencies
    ---
    tags:
      - Currency
    responses:
      200:
        description: List of supported currencies
        schema:
          type: object
          properties:
            success:
              type: boolean
            currencies:
              type: array
              items:
                type: object
                properties:
                  code:
                    type: string
                    example: "KES"
                  name:
                    type: string
                    example: "Kenyan Shilling"
                  symbol:
                    type: string
                    example: "KSh"
    """
    currencies = currency_service.get_supported_currencies()
    return jsonify({
        "success": True,
        "currencies": currencies
    }), 200


@api_v1_bp.route("/currencies/rates", methods=["GET"])
def get_exchange_rates():
    """
    Get current exchange rates
    ---
    tags:
      - Currency
    parameters:
      - in: query
        name: base
        type: string
        default: KES
        description: Base currency code
    responses:
      200:
        description: Exchange rates
        schema:
          type: object
          properties:
            success:
              type: boolean
            base:
              type: string
            rates:
              type: object
            timestamp:
              type: string
            source:
              type: string
              enum: [live, default]
    """
    base = request.args.get("base", "KES").upper()
    rates = currency_service.get_exchange_rates(base)
    
    return jsonify({
        "success": True,
        **rates
    }), 200


@api_v1_bp.route("/currencies/convert", methods=["POST"])
@jwt_required()
def convert_currency():
    """
    Convert amount between currencies
    ---
    tags:
      - Currency
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - amount
            - from_currency
            - to_currency
          properties:
            amount:
              type: number
              example: 1000
            from_currency:
              type: string
              example: "KES"
            to_currency:
              type: string
              example: "USD"
    responses:
      200:
        description: Conversion result
        schema:
          type: object
          properties:
            success:
              type: boolean
            amount:
              type: number
            from_currency:
              type: string
            to_currency:
              type: string
            converted_amount:
              type: number
            rate:
              type: number
      400:
        description: Invalid request
      401:
        description: Unauthorized
    """
    try:
        data = request.get_json() or {}
        
        amount = data.get("amount")
        from_currency = data.get("from_currency", "").upper()
        to_currency = data.get("to_currency", "").upper()

        if not amount or not from_currency or not to_currency:
            return jsonify({
                "success": False,
                "message": "amount, from_currency, and to_currency are required"
            }), 400

        result = currency_service.convert(
            amount=Decimal(str(amount)),
            from_currency=from_currency,
            to_currency=to_currency
        )

        if not result.get("success"):
            return jsonify(result), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
