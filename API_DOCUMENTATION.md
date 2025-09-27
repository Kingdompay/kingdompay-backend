# KingdomPay API Documentation

## Overview

KingdomPay is a Flask-based financial platform designed for communities, churches, and organizations to manage digital wallets, contributions, and payments. This API provides secure authentication, wallet management, and transaction tracking capabilities.

## Base Information

- **Base URL**: `http://localhost:5000/api/v1` (development)
- **Content-Type**: `application/json`
- **Authentication**: Bearer Token (JWT)
- **Version**: 1.0.0

## Authentication

KingdomPay uses OTP-based authentication with JWT tokens for API access.

### Authentication Flow

1. **Request OTP**: Send phone number to receive verification code
2. **Verify OTP**: Submit OTP code to get access and refresh tokens
3. **Use Tokens**: Include access token in Authorization header for protected endpoints
4. **Refresh Tokens**: Use refresh token to get new access token when expired

## API Endpoints

### Authentication Endpoints

#### Request OTP

```http
POST /api/v1/auth/otp/request
```

**Description**: Request an OTP code for phone number verification.

**Rate Limit**: 5 requests per minute

**Request Body**:

```json
{
  "phone_number": "+254712345678"
}
```

**Response** (200 OK):

```json
{
  "success": true,
  "message": "OTP sent successfully",
  "phone_number": "+254712345678"
}
```

**Response** (400 Bad Request):

```json
{
  "success": false,
  "message": "Invalid phone number format"
}
```

#### Verify OTP

```http
POST /api/v1/auth/otp/verify
```

**Description**: Verify OTP code and authenticate user.

**Rate Limit**: 10 requests per minute

**Request Body**:

```json
{
  "phone_number": "+254712345678",
  "otp_code": "123456",
  "full_name": "John Doe"
}
```

**Response** (200 OK):

```json
{
  "success": true,
  "message": "OTP verified successfully",
  "user": {
    "id": 1,
    "full_name": "John Doe",
    "email": null,
    "phone_number": "+254712345678",
    "is_phone_verified": true,
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  "tokens": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

#### Refresh Token

```http
POST /api/v1/auth/refresh
```

**Description**: Refresh access token using refresh token.

**Headers**:

```
Authorization: Bearer <refresh_token>
```

**Response** (200 OK):

```json
{
  "success": true,
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Get Current User

```http
GET /api/v1/auth/me
```

**Description**: Get current authenticated user information.

**Headers**:

```
Authorization: Bearer <access_token>
```

**Response** (200 OK):

```json
{
  "success": true,
  "user": {
    "id": 1,
    "full_name": "John Doe",
    "email": null,
    "phone_number": "+254712345678",
    "is_phone_verified": true,
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

#### Update Profile

```http
PUT /api/v1/auth/profile
```

**Description**: Update user profile information.

**Headers**:

```
Authorization: Bearer <access_token>
```

**Request Body**:

```json
{
  "full_name": "John Smith",
  "email": "john@example.com"
}
```

**Response** (200 OK):

```json
{
  "success": true,
  "message": "Profile updated successfully",
  "user": {
    "id": 1,
    "full_name": "John Smith",
    "email": "john@example.com",
    "phone_number": "+254712345678",
    "is_phone_verified": true,
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

#### Logout

```http
POST /api/v1/auth/logout
```

**Description**: Logout user (invalidates session).

**Headers**:

```
Authorization: Bearer <access_token>
```

**Response** (200 OK):

```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

### Wallet Endpoints

#### Get Wallet Balance

```http
GET /api/v1/wallets/balance
```

**Description**: Get current user's wallet balance and information.

**Headers**:

```
Authorization: Bearer <access_token>
```

**Response** (200 OK):

```json
{
  "success": true,
  "wallet": {
    "id": 1,
    "user_id": 1,
    "wallet_number": "550e8400-e29b-41d4-a716-446655440000",
    "display_number": "WAL-123456789",
    "balance": 1000.5,
    "currency": "KES",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

#### Get Wallet Transactions

```http
GET /api/v1/wallets/transactions
```

**Description**: Get current user's wallet transaction history.

**Headers**:

```
Authorization: Bearer <access_token>
```

**Query Parameters**:

- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20)

**Response** (200 OK):

```json
{
  "success": true,
  "transactions": [
    {
      "id": 1,
      "source_wallet_id": null,
      "destination_wallet_id": 1,
      "transaction_type": "DEPOSIT",
      "amount": 1000.0,
      "source_balance_after": null,
      "destination_balance_after": 1000.0,
      "reference_number": "TX-123456789012",
      "status": "SUCCESS",
      "description": "Initial deposit",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "has_more": false
  }
}
```

#### Get Wallet Ledger

```http
GET /api/v1/wallets/ledger
```

**Description**: Get wallet ledger (same as transactions endpoint).

**Headers**:

```
Authorization: Bearer <access_token>
```

**Response**: Same as Get Wallet Transactions

#### Transfer Funds

```http
POST /api/v1/wallets/transfer
```

**Description**: Transfer funds between wallets.

**Headers**:

```
Authorization: Bearer <access_token>
```

**Request Body**:

```json
{
  "destination_wallet_number": "WAL-123456789",
  "amount": 100.0,
  "description": "Payment for services"
}
```

**Response** (200 OK):

```json
{
  "success": true,
  "message": "Transfer completed successfully",
  "transaction": {
    "id": 1,
    "source_wallet_id": 1,
    "destination_wallet_id": 2,
    "transaction_type": "TRANSFER",
    "amount": 100.0,
    "source_balance_after": 900.0,
    "destination_balance_after": 1100.0,
    "reference_number": "TX-123456789012",
    "status": "SUCCESS",
    "description": "Payment for services",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "source_balance": 900.0,
  "destination_balance": 1100.0
}
```

**Response** (400 Bad Request):

```json
{
  "success": false,
  "message": "Insufficient funds"
}
```

#### Deposit Funds

```http
POST /api/v1/wallets/deposit
```

**Description**: Add funds to wallet (admin/system operation).

**Headers**:

```
Authorization: Bearer <access_token>
```

**Request Body**:

```json
{
  "amount": 500.0,
  "description": "Initial deposit"
}
```

**Response** (200 OK):

```json
{
  "success": true,
  "message": "Deposit completed successfully",
  "transaction": {
    "id": 1,
    "source_wallet_id": null,
    "destination_wallet_id": 1,
    "transaction_type": "DEPOSIT",
    "amount": 500.0,
    "source_balance_after": null,
    "destination_balance_after": 500.0,
    "reference_number": "TX-123456789012",
    "status": "SUCCESS",
    "description": "Initial deposit",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "new_balance": 500.0
}
```

#### Withdraw Funds

```http
POST /api/v1/wallets/withdraw
```

**Description**: Remove funds from wallet.

**Headers**:

```
Authorization: Bearer <access_token>
```

**Request Body**:

```json
{
  "amount": 200.0,
  "description": "Cash withdrawal"
}
```

**Response** (200 OK):

```json
{
  "success": true,
  "message": "Withdrawal completed successfully",
  "transaction": {
    "id": 1,
    "source_wallet_id": 1,
    "destination_wallet_id": null,
    "transaction_type": "WITHDRAWAL",
    "amount": 200.0,
    "source_balance_after": 300.0,
    "destination_balance_after": null,
    "reference_number": "TX-123456789012",
    "status": "SUCCESS",
    "description": "Cash withdrawal",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "new_balance": 300.0
}
```

**Response** (400 Bad Request):

```json
{
  "success": false,
  "message": "Insufficient funds"
}
```

### Health Check

#### Health Check

```http
GET /health
```

**Description**: Check API health status.

**Response** (200 OK):

```json
{
  "status": "healthy",
  "service": "kingdompay-api",
  "version": "1.0.0"
}
```

## Error Responses

All endpoints return consistent error responses:

### 400 Bad Request

```json
{
  "success": false,
  "message": "Bad request"
}
```

### 401 Unauthorized

```json
{
  "success": false,
  "message": "Authentication required"
}
```

### 403 Forbidden

```json
{
  "success": false,
  "message": "Insufficient permissions"
}
```

### 404 Not Found

```json
{
  "success": false,
  "message": "Resource not found"
}
```

### 429 Too Many Requests

```json
{
  "success": false,
  "message": "Too many requests"
}
```

### 500 Internal Server Error

```json
{
  "success": false,
  "message": "An unexpected error occurred"
}
```

## Data Models

### User Model

```json
{
  "id": 1,
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone_number": "+254712345678",
  "is_phone_verified": true,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Wallet Model

```json
{
  "id": 1,
  "user_id": 1,
  "wallet_number": "550e8400-e29b-41d4-a716-446655440000",
  "display_number": "WAL-123456789",
  "balance": 1000.5,
  "currency": "KES",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Transaction Model

```json
{
  "id": 1,
  "source_wallet_id": 1,
  "destination_wallet_id": 2,
  "transaction_type": "TRANSFER",
  "amount": 100.0,
  "source_balance_after": 900.0,
  "destination_balance_after": 1100.0,
  "reference_number": "TX-123456789012",
  "status": "SUCCESS",
  "description": "Payment for services",
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Rate Limiting

- **OTP Request**: 5 requests per minute per IP
- **OTP Verification**: 10 requests per minute per IP
- **General API**: 1000 requests per hour per IP

## Phone Number Format

KingdomPay accepts phone numbers in the following formats:

- `+254712345678` (International format)
- `0712345678` (Local format with leading 0)
- `712345678` (Local format without leading 0)

All phone numbers are normalized to international format (`+254...`) internally.

## Security Features

- **OTP Verification**: 6-digit codes with 5-minute expiry
- **JWT Tokens**: Secure access and refresh tokens
- **Rate Limiting**: Protection against abuse
- **Input Validation**: Comprehensive validation on all inputs
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **CORS Support**: Configurable cross-origin resource sharing

## Transaction Types

- `DEPOSIT`: Money added to wallet
- `WITHDRAWAL`: Money removed from wallet
- `TRANSFER`: Money transferred between wallets

## Status Codes

- `SUCCESS`: Transaction completed successfully
- `PENDING`: Transaction in progress
- `FAILED`: Transaction failed
- `CANCELLED`: Transaction cancelled

## Currency Support

Currently supports:

- `KES` (Kenyan Shilling) - Default
- `USD` (US Dollar)
- `EUR` (Euro)

## Development Notes

- The API is designed for Phase 1: Wallets + Communities + Giving
- Wallet creation is automatic when a user is created
- All monetary values are stored with 2 decimal places
- Database uses PostgreSQL in production, SQLite in development
- Redis is used for caching and rate limiting in production
