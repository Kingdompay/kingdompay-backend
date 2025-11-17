/**
 * KingdomPay API Client
 * Centralized API client for frontend templates
 */

// Helper function to get the correct API base URL
// Use relative URLs to avoid hostname issues
function getApiBaseURL() {
  // Use relative path - this works regardless of hostname (localhost, 127.0.0.1, or 0.0.0.0)
  return '/api/v1';
}

const API_CONFIG = {
  // Use relative path to avoid hostname issues
  baseURL: '/api/v1',
  timeout: 10000,
};

// Token management
function getAuthToken() {
  return localStorage.getItem("access_token");
}

function storeTokens(accessToken, refreshToken) {
  localStorage.setItem("access_token", accessToken);
  localStorage.setItem("refresh_token", refreshToken);
}

function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

// Generic API call function
async function apiCall(endpoint, options = {}) {
  const token = getAuthToken();

  const config = {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  };

  if (options.body) {
    config.body =
      typeof options.body === "string"
        ? options.body
        : JSON.stringify(options.body);
  }

  try {
    // Ensure endpoint starts with / if baseURL is relative
    const fullEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${API_CONFIG.baseURL}${fullEndpoint}`;
    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      const error = new Error(data.message || "Request failed");
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

// Authentication functions
const AuthAPI = {
  async requestOTP(phoneNumber) {
    return await apiCall("/auth/otp/request", {
      method: "POST",
      body: { phone_number: phoneNumber },
    });
  },

  async verifyOTP(phoneNumber, otpCode, fullName) {
    const response = await apiCall("/auth/otp/verify", {
      method: "POST",
      body: {
        phone_number: phoneNumber,
        otp_code: otpCode,
        full_name: fullName,
      },
    });

    if (response.success && response.access_token) {
      storeTokens(response.access_token, response.refresh_token);
    }

    return response;
  },

  async getCurrentUser() {
    return await apiCall("/auth/me");
  },

  logout() {
    clearTokens();
    window.location.href = "/static/auth.html";
  },
};

// Wallet functions
const WalletAPI = {
  async getBalance() {
    const response = await apiCall("/wallets/balance");
    return response.wallet;
  },

  async getTransactions(page = 1, perPage = 20) {
    return await apiCall(
      `/wallets/transactions?page=${page}&per_page=${perPage}`
    );
  },

  async transfer(destinationWallet, amount, description) {
    return await apiCall("/wallets/transfer", {
      method: "POST",
      body: {
        destination_wallet_number: destinationWallet,
        amount: amount,
        description: description,
      },
    });
  },

  async deposit(amount, description) {
    return await apiCall("/wallets/deposit", {
      method: "POST",
      body: {
        amount: amount,
        description: description,
      },
    });
  },

  async withdraw(amount, description) {
    return await apiCall("/wallets/withdraw", {
      method: "POST",
      body: {
        amount: amount,
        description: description,
      },
    });
  },
};

// KYC functions
const KYCAPI = {
  async getStatus() {
    return await apiCall("/kyc/status");
  },

  async uploadDocument(file, documentType, metadata = null) {
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
    if (!response.ok) {
      throw new Error(data.message || "Upload failed");
    }
    return data;
  },

  async initiate() {
    return await apiCall("/kyc/initiate", {
      method: "POST",
    });
  },
};

// Community functions
const CommunityAPI = {
  async create(data) {
    return await apiCall("/communities", {
      method: "POST",
      body: data,
    });
  },

  async list() {
    const response = await apiCall("/communities");
    return response.communities || [];
  },

  async get(communityId) {
    const response = await apiCall(`/communities/${communityId}`);
    return response.community;
  },

  async join(communityId) {
    return await apiCall(`/communities/${communityId}/join`, {
      method: "POST",
    });
  },

  async leave(communityId) {
    return await apiCall(`/communities/${communityId}/leave`, {
      method: "POST",
    });
  },

  async getMembers(communityId) {
    const response = await apiCall(`/communities/${communityId}/members`);
    return response.members || [];
  },

  async getContributions(communityId) {
    const response = await apiCall(`/communities/${communityId}/contributions`);
    return response.contributions || [];
  },

  async contribute(communityId, amount, description) {
    return await apiCall(`/communities/${communityId}/contributions`, {
      method: "POST",
      body: {
        amount: amount,
        description: description,
      },
    });
  },
};

// Campaign functions
const CampaignAPI = {
  async create(data) {
    return await apiCall("/campaigns", {
      method: "POST",
      body: data,
    });
  },

  async listByCommunity(communityId) {
    const response = await apiCall(`/communities/${communityId}/campaigns`);
    return response.campaigns || [];
  },

  async get(campaignId) {
    const response = await apiCall(`/campaigns/${campaignId}`);
    return response.campaign;
  },

  async contribute(campaignId, amount, description) {
    // Generate idempotency key
    const idempotencyKey = `campaign-${campaignId}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    return await apiCall(`/campaigns/${campaignId}/contribute`, {
      method: "POST",
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
      body: {
        amount: amount,
        memo: description,
      },
    });
  },
};

// M-Pesa functions
const MpesaAPI = {
  async initiateSTKPush(phone, amount, accountReference, transactionDesc = "Payment") {
    return await apiCall("/mpesa/pay", {
      method: "POST",
      body: {
        phone: phone,
        amount: amount,
        account_reference: accountReference,
        transaction_desc: transactionDesc,
      },
    });
  },

  async checkPaymentStatus(checkoutRequestId) {
    // Note: This endpoint may need to be implemented in the backend
    return await apiCall(`/mpesa/status/${checkoutRequestId}`);
  },
};

// Utility functions
function showError(message) {
  alert(message);
}

function showSuccess(message) {
  alert(message);
}

function formatCurrency(amount, currency = "KES") {
  return `${currency} ${parseFloat(amount).toFixed(2)}`;
}

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString() + " " + date.toLocaleTimeString();
}

// Check if user is authenticated
function isAuthenticated() {
  return !!getAuthToken();
}

// Redirect to login if not authenticated
function requireAuth() {
  const token = getAuthToken();
  if (!token) {
    window.location.href = "/static/auth.html";
    return false;
  }
  // Demo mode: Allow demo tokens to pass through
  if (token && token.startsWith("demo_")) {
    return true;
  }
  return true;
}
