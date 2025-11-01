# Frontend Development Guide for KingdomPay

## Overview

This guide helps frontend developers integrate with the KingdomPay API. It covers:

- API endpoints and authentication
- Connecting frontend templates to backend
- Making API calls
- Handling responses and errors
- Best practices

## API Base Configuration

### Base URL

- **Development**: `http://localhost:5040/api/v1`
- **Production**: `https://your-domain.com/api/v1`

### Authentication

KingdomPay uses JWT (JSON Web Tokens) for authentication:

1. Request OTP using phone number
2. Verify OTP to receive access and refresh tokens
3. Include access token in `Authorization` header for protected endpoints

## API Endpoints Reference

### Authentication Endpoints

#### 1. Request OTP

```http
POST /api/v1/auth/otp/request
Content-Type: application/json
```

**Request Body:**

```json
{
  "phone_number": "+254712345678"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "message": "OTP sent successfully",
  "phone_number": "+254712345678"
}
```

#### 2. Verify OTP

```http
POST /api/v1/auth/otp/verify
Content-Type: application/json
```

**Request Body:**

```json
{
  "phone_number": "+254712345678",
  "otp_code": "123456",
  "full_name": "John Doe"
}
```

**Response (200 OK):**

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
    "created_at": "2024-01-01T00:00:00Z"
  },
  "tokens": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

### Wallet Endpoints

#### 3. Get Wallet Balance

```http
GET /api/v1/wallets/balance
Authorization: Bearer <access_token>
```

**Response (200 OK):**

```json
{
  "success": true,
  "wallet": {
    "id": 1,
    "user_id": 1,
    "wallet_number": "550e8400-e29b-41d4-a716-446655440000",
    "display_number": "WAL-123456789",
    "balance": 1000.5,
    "currency": "KES"
  }
}
```

#### 4. Get Wallet Transactions

```http
GET /api/v1/wallets/transactions?page=1&per_page=20
Authorization: Bearer <access_token>
```

**Response (200 OK):**

```json
{
  "success": true,
  "transactions": [
    {
      "id": 1,
      "transaction_type": "DEPOSIT",
      "amount": 1000.0,
      "status": "SUCCESS",
      "reference_number": "TX-123456789012",
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

#### 5. Transfer Funds

```http
POST /api/v1/wallets/transfer
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "destination_wallet_number": "WAL-123456789",
  "amount": 100.0,
  "description": "Payment for services"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "message": "Transfer completed successfully",
  "transaction": {
    "id": 1,
    "transaction_type": "TRANSFER",
    "amount": 100.0,
    "status": "SUCCESS",
    "reference_number": "TX-123456789012",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### KYC Endpoints

#### 6. Get KYC Status

```http
GET /api/v1/kyc/status
Authorization: Bearer <access_token>
```

**Response (200 OK):**

```json
{
  "success": true,
  "kyc_status": {
    "status": "PENDING",
    "tier": "TIER_1",
    "verification_level": 1
  }
}
```

#### 7. Upload KYC Document

```http
POST /api/v1/kyc/documents
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Form Data:**

- `file`: Document file (ID, proof of address, selfie)
- `document_type`: NATIONAL_ID, PROOF_OF_ADDRESS, or SELFIE
- `metadata`: Optional JSON string

**Response (201 Created):**

```json
{
  "success": true,
  "message": "Document uploaded successfully",
  "document": {
    "id": 1,
    "document_type": "NATIONAL_ID",
    "status": "PENDING"
  }
}
```

## Frontend Integration Guide

### 1. API Configuration

Create a configuration file `config.js` in your frontend:

```javascript
// config.js
const API_CONFIG = {
  baseURL: "http://localhost:5040/api/v1",
  timeout: 10000, // 10 seconds
  headers: {
    "Content-Type": "application/json",
  },
};

// Helper function to get stored token
function getAuthToken() {
  return localStorage.getItem("access_token");
}

// Helper function to store tokens
function storeTokens(accessToken, refreshToken) {
  localStorage.setItem("access_token", accessToken);
  localStorage.setItem("refresh_token", refreshToken);
}

// Helper function to clear tokens
function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}
```

### 2. API Client Function

Create an API client for making requests:

```javascript
// api.js
async function apiCall(endpoint, options = {}) {
  const token = getAuthToken();

  const config = {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
    ...options,
  };

  if (options.body) {
    config.body = JSON.stringify(options.body);
  }

  try {
    const response = await fetch(`${API_CONFIG.baseURL}${endpoint}`, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || "Request failed");
    }

    return data;
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}
```

### 3. Authentication Flow

```javascript
// auth.js

// Request OTP
async function requestOTP(phoneNumber) {
  try {
    const response = await apiCall("/auth/otp/request", {
      method: "POST",
      body: { phone_number: phoneNumber },
    });

    console.log("OTP sent:", response.message);
    return response;
  } catch (error) {
    console.error("Failed to send OTP:", error);
    throw error;
  }
}

// Verify OTP
async function verifyOTP(phoneNumber, otpCode, fullName) {
  try {
    const response = await apiCall("/auth/otp/verify", {
      method: "POST",
      body: {
        phone_number: phoneNumber,
        otp_code: otpCode,
        full_name: fullName,
      },
    });

    if (response.success && response.tokens) {
      storeTokens(response.tokens.access_token, response.tokens.refresh_token);
    }

    return response;
  } catch (error) {
    console.error("OTP verification failed:", error);
    throw error;
  }
}

// Logout
function logout() {
  clearTokens();
  // Redirect to login page
  window.location.href = "/static/auth.html";
}
```

### 4. Wallet Operations

```javascript
// wallet.js

// Get wallet balance
async function getWalletBalance() {
  try {
    const response = await apiCall("/wallets/balance");
    return response.wallet;
  } catch (error) {
    console.error("Failed to get balance:", error);
    throw error;
  }
}

// Get wallet transactions
async function getTransactions(page = 1, perPage = 20) {
  try {
    const response = await apiCall(
      `/wallets/transactions?page=${page}&per_page=${perPage}`
    );
    return response;
  } catch (error) {
    console.error("Failed to get transactions:", error);
    throw error;
  }
}

// Transfer funds
async function transferFunds(destinationWallet, amount, description) {
  try {
    const response = await apiCall("/wallets/transfer", {
      method: "POST",
      body: {
        destination_wallet_number: destinationWallet,
        amount: amount,
        description: description,
      },
    });

    return response;
  } catch (error) {
    console.error("Transfer failed:", error);
    throw error;
  }
}
```

### 5. KYC Operations

```javascript
// kyc.js

// Get KYC status
async function getKYCStatus() {
  try {
    const response = await apiCall("/kyc/status");
    return response;
  } catch (error) {
    console.error("Failed to get KYC status:", error);
    throw error;
  }
}

// Upload KYC document
async function uploadDocument(file, documentType, metadata = null) {
  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", documentType);
    if (metadata) {
      formData.append("metadata", JSON.stringify(metadata));
    }

    const token = getAuthToken();
    const response = await fetch(`${API_CONFIG.baseURL}/kyc/documents`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Failed to upload document:", error);
    throw error;
  }
}
```

### 6. Error Handling

```javascript
// error-handler.js

function handleAPIError(error, userMessage = null) {
  const messages = {
    400: 'Invalid request. Please check your input.',
    401: 'Authentication required. Please log in.',
    403: 'You do not have permission to perform this action.',
    404: 'Resource not found.',
    429: 'Too many requests. Please try again later.',
    500: 'Server error. Please try again later.'
  };

  console.error('API Error:', error);

  const message = userMessage || handleAPIError.userMessage = `${message} Error code: ${error.status || 'Unknown'}`;

  // Show error to user
  alert(message);
}
```

### 7. Loading States

```javascript
// ui-helpers.js

function showLoading(elementId) {
  const element = document.getElementById(elementId);
  if (element) {
    element.innerHTML = '<div class="loading">Loading...</div>';
  }
}

function hideLoading(elementId) {
  const element = document.getElementById(elementId);
  if (element) {
    element.innerHTML = "";
  }
}

function updateBalance(balance) {
  const balanceElement = document.getElementById("balance");
  if (balanceElement) {
    balanceElement.textContent = `KES ${balance.toFixed(2)}`;
  }
}
```

## Complete Integration Example

### Authentication Flow (auth.html update)

```javascript
// Update the requestOTP function in auth.html
async function requestOTP() {
  const phone = document.getElementById("phone").value;

  if (!phone) {
    alert("Please enter your phone number");
    return;
  }

  try {
    showLoading("otp-status");
    const response = await apiCall("/auth/otp/request", {
      method: "POST",
      body: { phone_number: phone },
    });

    document.getElementById("otp-status").style.display = "block";
    document.getElementById("otp-status").textContent =
      "Verification code sent successfully!";

    // Move to next step after 2 seconds
    setTimeout(() => {
      nextStep();
    }, 2000);
  } catch (error) {
    alert("Failed to send OTP: " + error.message);
  }
}

// Update verifyOTP function
async function verifyOTP() {
  const phone = document.getElementById("phone").value;
  const otp = document.getElementById("otp").value;
  const fullname = document.getElementById("fullname").value;

  if (!otp || !fullname) {
    alert("Please fill in all required fields");
    return;
  }

  try {
    const response = await apiCall("/auth/otp/verify", {
      method: "POST",
      body: {
        phone_number: phone,
        otp_code: otp,
        full_name: fullname,
      },
    });

    if (response.success) {
      // Store tokens
      storeTokens(response.tokens.access_token, response.tokens.refresh_token);

      // Update UI with user info
      document.getElementById("user-info").style.display = "block";
      document.getElementById("tokens").style.display = "block";

      // Move to success step
      nextStep();
    }
  } catch (error) {
    alert("OTP verification failed: " + error.message);
  }
}
```

### Wallet Dashboard (wallet.html update)

```javascript
// Load wallet data on page load
document.addEventListener("DOMContentLoaded", async function () {
  try {
    // Load balance
    const wallet = await getWalletBalance();
    updateBalance(wallet.balance);
    document.getElementById("wallet-number").textContent =
      wallet.display_number;

    // Load transactions
    const transactionsResponse = await getTransactions();
    displayTransactions(transactionsResponse.transactions);
  } catch (error) {
    console.error("Failed to load wallet data:", error);
  }
});

// Display transactions
function displayTransactions(transactions) {
  const container = document.getElementById("transactions-container");
  transactions.forEach((tx) => {
    const txElement = createTransactionElement(tx);
    container.appendChild(txElement);
  });
}

// Transfer function
async function processTransfer() {
  const recipient = document.getElementById("recipient").value;
  const amount = document.getElementById("amount").value;
  const description = document.getElementById("description").value;

  if (!recipient || !amount || !description) {
    alert("Please fill in all fields");
    return;
  }

  try {
    const response = await transferFunds(
      recipient,
      parseFloat(amount),
      description
    );
    alert(
      `Transfer successful! Reference: ${response.transaction.reference_number}`
    );

    // Reload balance
    const wallet = await getWalletBalance();
    updateBalance(wallet.balance);

    // Reload transactions
    const transactionsResponse = await getTransactions();
    displayTransactions(transactionsResponse.transactions);
  } catch (error) {
    alert("Transfer failed: " + error.message);
  }
}
```

## Testing Your Integration

### 1. Test Authentication Flow

1. Open `auth.html` in browser
2. Enter phone number (e.g., +254712345678)
3. Request OTP
4. Verify OTP
5. Check localStorage for tokens

### 2. Test Wallet Operations

1. Open `wallet.html` in browser
2. Verify you're authenticated
3. Try transferring funds
4. Check transaction history
5. Verify balance updates

### 3. Test KYC Upload

1. Open `kyc.html` in browser
2. Upload documents
3. Check status

## Best Practices

1. **Always handle errors gracefully**

   - Show user-friendly error messages
   - Log technical errors for debugging

2. **Store tokens securely**

   - Use localStorage for demo
   - Consider httpOnly cookies for production

3. **Implement loading states**

   - Show loading indicators during API calls
   - Disable buttons to prevent duplicate requests

4. **Validate input before sending**

   - Check required fields
   - Validate formats (phone numbers, amounts)

5. **Handle token expiration**

   - Refresh access tokens when they expire
   - Logout user if refresh fails

6. **Optimize API calls**

   - Cache data when appropriate
   - Debounce user input for search

7. **Mobile responsiveness**
   - Ensure all templates work on mobile
   - Test touch interactions

## Common Issues and Solutions

### Issue: CORS Error

**Solution**: Ensure backend has CORS enabled and credentials are properly set

### Issue: Token Expired

**Solution**: Implement token refresh logic or redirect to login

### Issue: Rate Limiting

**Solution**: Implement exponential backoff for failed requests

### Issue: Unauthorized Access

**Solution**: Check that tokens are being sent in Authorization header

## Next Steps

1. Integrate API calls into existing templates
2. Add proper error handling
3. Implement token refresh logic
4. Add loading states and animations
5. Test all endpoints
6. Optimize for production

## Resources

- API Documentation: `API_DOCUMENTATION.md`
- Postman Collection: `docs/postman/KingdomPay.postman_collection.json`
- Community Features: `COMMUNITY_FEATURES.md`

## Support

For questions or issues:

- Check API documentation
- Review error logs
- Test with Postman collection
- Contact backend team
