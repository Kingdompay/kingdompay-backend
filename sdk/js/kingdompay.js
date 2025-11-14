// Minimal JS SDK for KingdomPay
// Usage:
//  const kp = new KingdomPay({ baseUrl: 'https://api.kingdompay.example', apiKey: null });
//  kp.checkout({ amount: 1000, memo: 'Donation', campaignId: 1 });

export class KingdomPay {
  constructor(config) {
    this.baseUrl = (config && config.baseUrl) || '';
  }

  async checkout({ amount, memo, campaignId, checkoutId }) {
    const params = new URLSearchParams({ amount });
    if (memo) params.append('memo', memo);
    if (campaignId) params.append('campaign_id', campaignId);
    if (checkoutId) params.append('checkout_id', checkoutId);
    window.location.href = `${this.baseUrl}/api/v1/checkout?${params.toString()}`;
  }

  async initiatePayment({ amount, phone, provider, campaignId, checkoutId }) {
    const resp = await fetch(`${this.baseUrl}/api/v1/checkout/initiate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount, phone, provider, campaign_id: campaignId, checkout_id: checkoutId })
    });
    return await resp.json();
  }

  async transfer({ token, toWallet, amount, memo, idemKey }) {
    const resp = await fetch(`${this.baseUrl}/api/v1/transfers`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        'Idempotency-Key': idemKey || self.crypto.randomUUID()
      },
      body: JSON.stringify({ to_wallet: toWallet, amount, memo })
    });
    return await resp.json();
  }
}


