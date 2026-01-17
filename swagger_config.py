"""
Swagger/OpenAPI Configuration for KingdomPay API
"""

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "KingdomPay API",
        "description": """
# KingdomPay Payment Platform API

A comprehensive payment platform API supporting:
- **Authentication**: OTP-based phone verification
- **Wallets**: Balance management and transfers
- **M-Pesa**: Deposits (STK Push) and Withdrawals (B2C)
- **Communities**: Group savings and contributions
- **KYC**: Identity verification and tier management

## Authentication
All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## Rate Limiting
- OTP requests: 10/minute, 30/hour
- General API: 100/minute

## Phone Number Formats
The API accepts phone numbers in multiple formats:
- `+254712345678` (International)
- `0712345678` (Local)
- `712345678` (9 digits)

All formats are normalized to `+254XXXXXXXXX` internally.
        """,
        "version": "1.0.0",
        "contact": {
            "name": "KingdomPay Support",
            "email": "support@kingdompay.com"
        },
        "license": {
            "name": "Proprietary"
        }
    },
    "host": "localhost:5001",
    "basePath": "/api/v1",
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header. Example: 'Bearer {token}'"
        }
    },
    "tags": [
        {
            "name": "Authentication",
            "description": "OTP-based authentication and user management"
        },
        {
            "name": "Wallet",
            "description": "Wallet operations - balance, transfers, transactions"
        },
        {
            "name": "M-Pesa",
            "description": "M-Pesa integration - deposits and withdrawals"
        },
        {
            "name": "KYC",
            "description": "Know Your Customer verification"
        },
        {
            "name": "Communities",
            "description": "Community and group management"
        },
        {
            "name": "Campaigns",
            "description": "Community campaigns and contributions"
        },
        {
            "name": "Admin",
            "description": "Administrative endpoints"
        },
        {
            "name": "Health",
            "description": "Health check endpoints"
        }
    ]
}

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
}


# ═══════════════════════════════════════════════════════════════════════════════
#                         API DOCUMENTATION SPECS
# ═══════════════════════════════════════════════════════════════════════════════

# Authentication Specs
AUTH_OTP_REQUEST_SPEC = """
Send OTP to phone number for authentication
---
tags:
  - Authentication
parameters:
  - in: body
    name: body
    required: true
    schema:
      type: object
      required:
        - phone_number
      properties:
        phone_number:
          type: string
          description: Phone number (+254XXXXXXXXX or 07XXXXXXXX)
          example: "+254712345678"
responses:
  200:
    description: OTP sent successfully
    schema:
      type: object
      properties:
        success:
          type: boolean
          example: true
        message:
          type: string
          example: "OTP sent successfully"
        phone_number:
          type: string
          example: "+254712345678"
  400:
    description: Invalid phone number
  429:
    description: Rate limit exceeded
"""

AUTH_OTP_VERIFY_SPEC = """
Verify OTP and get JWT tokens
---
tags:
  - Authentication
parameters:
  - in: body
    name: body
    required: true
    schema:
      type: object
      required:
        - phone_number
        - otp_code
      properties:
        phone_number:
          type: string
          example: "+254712345678"
        otp_code:
          type: string
          example: "123456"
        full_name:
          type: string
          description: Required for new users
          example: "John Doe"
responses:
  200:
    description: OTP verified successfully
    schema:
      type: object
      properties:
        success:
          type: boolean
        access_token:
          type: string
        refresh_token:
          type: string
        user:
          type: object
  401:
    description: Invalid or expired OTP
"""

AUTH_ME_SPEC = """
Get current user information
---
tags:
  - Authentication
security:
  - Bearer: []
responses:
  200:
    description: User information
    schema:
      type: object
      properties:
        success:
          type: boolean
        user:
          type: object
          properties:
            id:
              type: integer
            full_name:
              type: string
            phone_number:
              type: string
            email:
              type: string
            role:
              type: string
              enum: [USER, ADMIN, SUPPORT]
  401:
    description: Unauthorized
"""

# Wallet Specs
WALLET_BALANCE_SPEC = """
Get wallet balance
---
tags:
  - Wallet
security:
  - Bearer: []
responses:
  200:
    description: Wallet balance
    schema:
      type: object
      properties:
        success:
          type: boolean
        wallet:
          type: object
          properties:
            id:
              type: integer
            balance:
              type: number
            currency:
              type: string
              example: "KES"
            wallet_number:
              type: string
  401:
    description: Unauthorized
  404:
    description: Wallet not found
"""

WALLET_TRANSFER_SPEC = """
Transfer funds to another wallet
---
tags:
  - Wallet
security:
  - Bearer: []
parameters:
  - in: header
    name: Idempotency-Key
    type: string
    required: true
    description: Unique key to prevent duplicate transfers
  - in: body
    name: body
    required: true
    schema:
      type: object
      required:
        - recipient_phone
        - amount
      properties:
        recipient_phone:
          type: string
          example: "+254712345678"
        amount:
          type: number
          example: 1000
        description:
          type: string
          example: "Payment for services"
responses:
  200:
    description: Transfer successful
    schema:
      type: object
      properties:
        success:
          type: boolean
        transaction_id:
          type: integer
        new_balance:
          type: number
  400:
    description: Invalid request or insufficient balance
  401:
    description: Unauthorized
"""

WALLET_TRANSACTIONS_SPEC = """
Get wallet transaction history
---
tags:
  - Wallet
security:
  - Bearer: []
parameters:
  - in: query
    name: page
    type: integer
    default: 1
  - in: query
    name: per_page
    type: integer
    default: 20
responses:
  200:
    description: Transaction list
    schema:
      type: object
      properties:
        success:
          type: boolean
        transactions:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              type:
                type: string
                enum: [DEPOSIT, WITHDRAWAL, TRANSFER, REFUND]
              amount:
                type: number
              status:
                type: string
              created_at:
                type: string
        pagination:
          type: object
  401:
    description: Unauthorized
"""

# M-Pesa Specs
MPESA_DEPOSIT_SPEC = """
Initiate M-Pesa STK Push deposit
---
tags:
  - M-Pesa
security:
  - Bearer: []
parameters:
  - in: body
    name: body
    required: true
    schema:
      type: object
      required:
        - phone_number
        - amount
      properties:
        phone_number:
          type: string
          description: M-Pesa phone number
          example: "0712345678"
        amount:
          type: number
          minimum: 1
          maximum: 70000
          example: 1000
        reference:
          type: string
          description: Optional reference
          example: "Wallet top-up"
responses:
  200:
    description: STK Push initiated
    schema:
      type: object
      properties:
        success:
          type: boolean
        payment_id:
          type: integer
        checkout_request_id:
          type: string
        message:
          type: string
  400:
    description: Invalid request
  401:
    description: Unauthorized
"""

MPESA_WITHDRAW_SPEC = """
Initiate M-Pesa B2C withdrawal
---
tags:
  - M-Pesa
security:
  - Bearer: []
parameters:
  - in: body
    name: body
    required: true
    schema:
      type: object
      required:
        - phone_number
        - amount
      properties:
        phone_number:
          type: string
          description: M-Pesa phone number to receive funds
          example: "0712345678"
        amount:
          type: number
          minimum: 10
          maximum: 70000
          example: 1000
responses:
  200:
    description: Withdrawal initiated
    schema:
      type: object
      properties:
        success:
          type: boolean
        payment_id:
          type: integer
        transaction_id:
          type: integer
        amount:
          type: number
        phone:
          type: string
        new_balance:
          type: number
        message:
          type: string
  400:
    description: Invalid request or insufficient balance
  401:
    description: Unauthorized
"""

# KYC Specs
KYC_STATUS_SPEC = """
Get user's KYC verification status
---
tags:
  - KYC
security:
  - Bearer: []
responses:
  200:
    description: KYC status
    schema:
      type: object
      properties:
        success:
          type: boolean
        verification:
          type: object
          properties:
            status:
              type: string
              enum: [pending, approved, rejected]
            tier:
              type: string
              enum: [tier_0, tier_1, tier_2]
            daily_limit:
              type: number
            documents:
              type: array
  401:
    description: Unauthorized
"""

KYC_DOCUMENT_UPLOAD_SPEC = """
Upload KYC verification document
---
tags:
  - KYC
security:
  - Bearer: []
consumes:
  - multipart/form-data
parameters:
  - in: formData
    name: file
    type: file
    required: true
    description: Document file (PDF, JPG, PNG)
  - in: formData
    name: document_type
    type: string
    required: true
    enum: [national_id, passport, drivers_license, utility_bill, bank_statement]
responses:
  200:
    description: Document uploaded
    schema:
      type: object
      properties:
        success:
          type: boolean
        document:
          type: object
  400:
    description: Invalid file or document type
  401:
    description: Unauthorized
"""

# Community Specs
COMMUNITY_LIST_SPEC = """
List user's communities
---
tags:
  - Communities
security:
  - Bearer: []
responses:
  200:
    description: Community list
    schema:
      type: object
      properties:
        success:
          type: boolean
        communities:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
              description:
                type: string
              member_count:
                type: integer
              my_role:
                type: string
  401:
    description: Unauthorized
"""

COMMUNITY_CREATE_SPEC = """
Create a new community
---
tags:
  - Communities
security:
  - Bearer: []
parameters:
  - in: body
    name: body
    required: true
    schema:
      type: object
      required:
        - name
      properties:
        name:
          type: string
          example: "Savings Group"
        description:
          type: string
          example: "Monthly savings group"
responses:
  201:
    description: Community created
    schema:
      type: object
      properties:
        success:
          type: boolean
        community:
          type: object
  400:
    description: Invalid request
  401:
    description: Unauthorized
"""

# Health Specs
HEALTH_SPEC = """
Basic health check
---
tags:
  - Health
responses:
  200:
    description: Service is healthy
    schema:
      type: object
      properties:
        status:
          type: string
          example: "healthy"
        timestamp:
          type: string
"""

HEALTH_READY_SPEC = """
Readiness check (includes database and Redis)
---
tags:
  - Health
responses:
  200:
    description: Service is ready
    schema:
      type: object
      properties:
        status:
          type: string
        database:
          type: string
        redis:
          type: string
  503:
    description: Service not ready
"""
