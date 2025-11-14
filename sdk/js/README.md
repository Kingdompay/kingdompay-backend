# KingdomPay JavaScript SDK

Minimal JavaScript SDK for integrating KingdomPay checkout and transfers into web applications.

## Installation

```bash
# Copy kingdompay.js to your project
cp sdk/js/kingdompay.js ./src/
```

Or include via CDN (once hosted):
```html
<script type="module" src="https://cdn.kingdompay.example/sdk/kingdompay.js"></script>
```

## Usage

### Basic Setup

```javascript
import { KingdomPay } from './kingdompay.js';

const kp = new KingdomPay({
  baseUrl: 'https://api.kingdompay.example'
});
```

### Checkout (Redirect Flow)

Redirect user to hosted checkout page:

```javascript
// Simple checkout
kp.checkout({
  amount: 1000,
  memo: 'Donation to church'
});

// With campaign
kp.checkout({
  amount: 5000,
  memo: 'Tithe',
  campaignId: 123
});
```

### Initiate Payment (API Flow)

Initiate payment without redirect:

```javascript
const result = await kp.initiatePayment({
  amount: 2000,
  phone: '+254712345678',
  provider: 'MPESA', // MPESA, AIRTEL, or TKASH
  campaignId: 123
});

if (result.success) {
  console.log('Payment initiated:', result.checkout_request_id);
  // User will receive STK prompt on their phone
} else {
  console.error('Payment failed:', result.message);
}
```

### Wallet Transfer (Authenticated)

```javascript
const result = await kp.transfer({
  token: 'your-jwt-token',
  toWallet: 'WAL-123456789',
  amount: 500,
  memo: 'P2P transfer',
  idemKey: 'unique-idempotency-key' // Optional, auto-generated if not provided
});

if (result.success) {
  console.log('Transfer successful:', result.journal_id);
  console.log('Fee breakdown:', result.fee_breakdown);
} else {
  console.error('Transfer failed:', result.message);
}
```

## Complete Example

```html
<!DOCTYPE html>
<html>
<head>
  <title>KingdomPay Integration</title>
</head>
<body>
  <button onclick="handleDonation()">Donate KSh 1000</button>

  <script type="module">
    import { KingdomPay } from './kingdompay.js';
    
    const kp = new KingdomPay({
      baseUrl: 'http://localhost:5000'
    });

    window.handleDonation = async () => {
      try {
        // Option 1: Redirect to hosted checkout
        kp.checkout({
          amount: 1000,
          memo: 'Church donation',
          campaignId: 1
        });
        
        // Option 2: Direct API call (requires phone number)
        // const result = await kp.initiatePayment({
        //   amount: 1000,
        //   phone: '+254712345678',
        //   provider: 'MPESA',
        //   campaignId: 1
        // });
        // console.log(result);
      } catch (error) {
        console.error('Error:', error);
      }
    };
  </script>
</body>
</html>
```

## Error Handling

```javascript
try {
  const result = await kp.initiatePayment({ amount: 1000, phone: '+254712345678', provider: 'MPESA' });
  
  if (!result.success) {
    // Handle API errors
    if (result.message.includes('insufficient')) {
      alert('Insufficient balance');
    } else if (result.message.includes('limit')) {
      alert('Transaction limit exceeded');
    }
  }
} catch (error) {
  // Handle network errors
  console.error('Network error:', error);
}
```

## Response Formats

### Checkout Response
```json
{
  "success": true,
  "checkout_request_id": "abc123",
  "message": "Payment initiated"
}
```

### Transfer Response
```json
{
  "success": true,
  "status": "posted",
  "journal_id": 456,
  "transfer_amount": 500.0,
  "fee_breakdown": {
    "fee_amount": 7.5,
    "platform_fee": 2.5,
    "community_fee": 2.5,
    "federal_fee": 2.5
  },
  "contribution_breakdown": {
    "contribution_amount": 5.0,
    "community_id": 123
  },
  "total_deduction": 512.5
}
```

## Browser Support

- Modern browsers with ES6 module support
- Requires `fetch` API (or polyfill for older browsers)
- `crypto.randomUUID()` for idempotency (or provide your own `idemKey`)

## Notes

- All amounts are in KES (Kenyan Shillings)
- Phone numbers should be in international format (+254...)
- Idempotency keys ensure safe retries; use same key for duplicate requests
- Transfers require JWT authentication token

