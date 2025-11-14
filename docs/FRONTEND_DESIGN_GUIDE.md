# KingdomPay Frontend Design System & Guide

## Table of Contents
1. [Design Philosophy](#design-philosophy)
2. [Color Palette](#color-palette)
3. [Typography](#typography)
4. [Component Library](#component-library)
5. [Layout Patterns](#layout-patterns)
6. [Responsive Design](#responsive-design)
7. [Animation Guidelines](#animation-guidelines)
8. [API Integration Patterns](#api-integration-patterns)
9. [Template Examples](#template-examples)
10. [Development Guidelines](#development-guidelines)

---

## Design Philosophy

### Core Principles
- **Trust & Security**: Clean, professional design that instills confidence in financial transactions
- **Accessibility**: WCAG 2.1 AA compliant with high contrast ratios and keyboard navigation
- **Mobile-First**: Responsive design optimized for mobile devices
- **Performance**: Fast loading with optimized assets and minimal dependencies
- **Consistency**: Unified design language across all components and pages

### Visual Identity
- **Modern & Clean**: Minimalist design with plenty of white space
- **Gradient Accents**: Subtle gradients for visual interest without overwhelming content
- **Glass Morphism**: Frosted glass effects for modern, premium feel
- **Card-Based Layout**: Information organized in digestible, scannable cards

---

## Color Palette

### Primary Colors
```css
/* Primary Gradient */
--primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
--primary-start: #667eea;
--primary-end: #764ba2;

/* Secondary Gradients */
--success-gradient: linear-gradient(45deg, #48bb78, #38a169);
--warning-gradient: linear-gradient(45deg, #f6e05e, #d69e2e);
--danger-gradient: linear-gradient(45deg, #f56565, #e53e3e);
--info-gradient: linear-gradient(45deg, #4facfe, #00f2fe);
```

### Neutral Colors
```css
/* Text Colors */
--text-primary: #2d3748;
--text-secondary: #4a5568;
--text-muted: #718096;
--text-light: #a0aec0;

/* Background Colors */
--bg-primary: #ffffff;
--bg-secondary: #f7fafc;
--bg-tertiary: #edf2f7;
--bg-glass: rgba(255, 255, 255, 0.95);

/* Border Colors */
--border-light: #e2e8f0;
--border-medium: #cbd5e0;
--border-dark: #a0aec0;
```

### Status Colors
```css
/* Success States */
--success-bg: #c6f6d5;
--success-text: #22543d;
--success-border: #9ae6b4;

/* Warning States */
--warning-bg: #fef5e7;
--warning-text: #744210;
--warning-border: #f6e05e;

/* Error States */
--error-bg: #fed7d7;
--error-text: #742a2a;
--error-border: #feb2b2;

/* Info States */
--info-bg: #bee3f8;
--info-text: #2a4365;
--info-border: #90cdf4;
```

---

## Typography

### Font Stack
```css
font-family: "Inter", "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
```

### Type Scale
```css
/* Headings */
--text-4xl: 2.5rem;    /* 40px - Page titles */
--text-3xl: 2rem;      /* 32px - Section headers */
--text-2xl: 1.5rem;    /* 24px - Card titles */
--text-xl: 1.25rem;    /* 20px - Subsection headers */
--text-lg: 1.125rem;   /* 18px - Large body text */

/* Body Text */
--text-base: 1rem;     /* 16px - Default body text */
--text-sm: 0.875rem;   /* 14px - Small text */
--text-xs: 0.75rem;    /* 12px - Captions */

/* Font Weights */
--font-light: 300;
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
--font-extrabold: 800;
```

### Text Styles
```css
.heading-primary {
  font-size: var(--text-4xl);
  font-weight: var(--font-extrabold);
  color: var(--text-primary);
  background: var(--primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.heading-secondary {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.body-text {
  font-size: var(--text-base);
  font-weight: var(--font-normal);
  color: var(--text-secondary);
  line-height: 1.6;
}
```

---

## Component Library

### Buttons

#### Primary Button
```css
.btn-primary {
  background: var(--primary-gradient);
  color: white;
  padding: 15px 25px;
  border: none;
  border-radius: 12px;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
}
```

#### Secondary Button
```css
.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-secondary);
  padding: 15px 25px;
  border: 2px solid var(--border-light);
  border-radius: 12px;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-secondary:hover {
  background: var(--border-medium);
  border-color: var(--border-dark);
}
```

### Cards

#### Basic Card
```css
.card {
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  border-radius: 25px;
  padding: 30px;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--primary-gradient);
}

.card:hover {
  transform: translateY(-8px);
  box-shadow: 0 35px 70px rgba(0, 0, 0, 0.15);
}
```

#### Wallet Card
```css
.wallet-card {
  background: var(--primary-gradient);
  color: white;
  border-radius: 25px;
  padding: 40px;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.2);
  position: relative;
  overflow: hidden;
}

.wallet-card::before {
  content: "";
  position: absolute;
  top: -50%;
  right: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(
    circle,
    rgba(255, 255, 255, 0.1) 0%,
    transparent 70%
  );
  animation: float 6s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(180deg); }
}
```

### Form Elements

#### Input Fields
```css
.form-group {
  margin-bottom: 25px;
}

.form-group label {
  display: block;
  margin-bottom: 10px;
  color: var(--text-secondary);
  font-weight: var(--font-semibold);
  font-size: var(--text-base);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 15px;
  border: 2px solid var(--border-light);
  border-radius: 12px;
  font-size: var(--text-base);
  transition: all 0.3s ease;
  background: white;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--primary-start);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}
```

#### File Upload
```css
.file-upload {
  border: 2px dashed var(--border-medium);
  border-radius: 12px;
  padding: 30px;
  text-align: center;
  background: var(--bg-secondary);
  transition: all 0.3s ease;
  cursor: pointer;
}

.file-upload:hover {
  border-color: var(--primary-start);
  background: #f0f4ff;
}

.file-upload.dragover {
  border-color: var(--primary-start);
  background: #f0f4ff;
  transform: scale(1.02);
}
```

### Status Indicators

#### Status Badges
```css
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  border-radius: 25px;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  margin: 10px 0;
}

.status-success {
  background: var(--success-bg);
  color: var(--success-text);
}

.status-warning {
  background: var(--warning-bg);
  color: var(--warning-text);
}

.status-error {
  background: var(--error-bg);
  color: var(--error-text);
}

.status-info {
  background: var(--info-bg);
  color: var(--info-text);
}
```

### Navigation

#### Navigation Menu
```css
.nav-menu {
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 20px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 15px;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  background: var(--primary-gradient);
  color: white;
  padding: 12px 20px;
  border-radius: 15px;
  text-decoration: none;
  font-weight: var(--font-semibold);
  transition: all 0.3s ease;
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

.nav-link:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
}
```

---

## Layout Patterns

### Container System
```css
.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.container-sm {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.container-lg {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px;
}
```

### Grid System
```css
.grid {
  display: grid;
  gap: 30px;
}

.grid-2 {
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
}

.grid-3 {
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
}

.grid-4 {
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}
```

### Dashboard Layout
```css
.dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 30px;
  margin-bottom: 40px;
}
```

### Header Pattern
```css
.header {
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  border-radius: 25px;
  padding: 40px;
  margin-bottom: 30px;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.1);
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.2);
}
```

---

## Responsive Design

### Breakpoints
```css
/* Mobile First Approach */
/* Base styles for mobile (320px+) */

/* Small tablets (768px+) */
@media (min-width: 768px) {
  .container { padding: 30px; }
  .grid-2 { grid-template-columns: repeat(2, 1fr); }
}

/* Large tablets and small desktops (1024px+) */
@media (min-width: 1024px) {
  .container { padding: 40px; }
  .grid-3 { grid-template-columns: repeat(3, 1fr); }
}

/* Large desktops (1280px+) */
@media (min-width: 1280px) {
  .container { padding: 50px; }
  .grid-4 { grid-template-columns: repeat(4, 1fr); }
}
```

### Mobile Optimizations
```css
@media (max-width: 768px) {
  .nav-menu {
    flex-direction: column;
    align-items: center;
  }
  
  .nav-link {
    width: 100%;
    justify-content: center;
    max-width: 300px;
  }
  
  .dashboard {
    grid-template-columns: 1fr;
  }
  
  .card {
    padding: 20px;
  }
}
```

---

## Animation Guidelines

### Transition Timing
```css
/* Standard transitions */
--transition-fast: 0.2s ease;
--transition-normal: 0.3s ease;
--transition-slow: 0.5s ease;
```

### Hover Effects
```css
.hover-lift {
  transition: transform var(--transition-normal);
}

.hover-lift:hover {
  transform: translateY(-5px);
}

.hover-scale {
  transition: transform var(--transition-normal);
}

.hover-scale:hover {
  transform: scale(1.05);
}
```

### Loading Animations
```css
@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-up {
  animation: fadeInUp 0.6s ease forwards;
}
```

### Staggered Animations
```css
.stagger-animation > * {
  opacity: 0;
  transform: translateY(20px);
}

.stagger-animation > *:nth-child(1) { animation-delay: 0.1s; }
.stagger-animation > *:nth-child(2) { animation-delay: 0.2s; }
.stagger-animation > *:nth-child(3) { animation-delay: 0.3s; }
.stagger-animation > *:nth-child(4) { animation-delay: 0.4s; }
```

---

## API Integration Patterns

### API Client Setup
```javascript
class KingdomPayAPI {
  constructor(baseURL = '/api/v1') {
    this.baseURL = baseURL;
    this.token = localStorage.getItem('access_token');
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...(this.token && { 'Authorization': `Bearer ${this.token}` }),
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || 'Request failed');
      }
      
      return data;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  // Authentication methods
  async requestOTP(phoneNumber) {
    return this.request('/auth/otp/request', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phoneNumber }),
    });
  }

  async verifyOTP(phoneNumber, otp, userData) {
    return this.request('/auth/otp/verify', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phoneNumber, otp, ...userData }),
    });
  }

  // Wallet methods
  async getWalletBalance() {
    return this.request('/wallets/balance');
  }

  async getTransactions(limit = 50, offset = 0) {
    return this.request(`/wallets/transactions?limit=${limit}&offset=${offset}`);
  }

  async transferFunds(recipientWallet, amount, description) {
    return this.request('/wallets/transfer', {
      method: 'POST',
      body: JSON.stringify({
        recipient_wallet: recipientWallet,
        amount: parseFloat(amount),
        description,
      }),
    });
  }

  // KYC methods
  async getKYCStatus() {
    return this.request('/kyc/status');
  }

  async uploadKYCDocuments(formData) {
    return this.request('/kyc/documents', {
      method: 'POST',
      headers: {
        // Remove Content-Type to let browser set it for FormData
      },
      body: formData,
    });
  }
}
```

### Error Handling
```javascript
class ErrorHandler {
  static handle(error) {
    console.error('Error:', error);
    
    // Show user-friendly error message
    const errorMessage = this.getErrorMessage(error);
    this.showNotification(errorMessage, 'error');
  }

  static getErrorMessage(error) {
    const errorMessages = {
      'Invalid phone number format': 'Please enter a valid phone number',
      'OTP expired': 'Verification code has expired. Please request a new one.',
      'Insufficient funds': 'You don\'t have enough balance for this transaction',
      'Wallet not found': 'Recipient wallet not found. Please check the wallet number.',
      'Rate limit exceeded': 'Too many requests. Please wait a moment and try again.',
    };

    return errorMessages[error.message] || 'Something went wrong. Please try again.';
  }

  static showNotification(message, type = 'info') {
    // Implementation for showing notifications
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.remove();
    }, 5000);
  }
}
```

### Loading States
```javascript
class LoadingManager {
  static show(element) {
    element.classList.add('loading');
    element.disabled = true;
    
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    spinner.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    element.appendChild(spinner);
  }

  static hide(element) {
    element.classList.remove('loading');
    element.disabled = false;
    
    const spinner = element.querySelector('.spinner');
    if (spinner) {
      spinner.remove();
    }
  }
}
```

---

## Template Examples

### Complete Page Template
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KingdomPay - Page Title</title>
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
  <link href="styles.css" rel="stylesheet">
</head>
<body>
  <div class="container">
    <!-- Header -->
    <div class="header">
      <h1><i class="fas fa-icon"></i> Page Title</h1>
      <p>Page description or subtitle</p>
    </div>

    <!-- Navigation -->
    <div class="nav-menu">
      <a href="/dashboard" class="nav-link">
        <i class="fas fa-home"></i> Dashboard
      </a>
      <a href="/wallet" class="nav-link">
        <i class="fas fa-wallet"></i> Wallet
      </a>
      <a href="/transactions" class="nav-link">
        <i class="fas fa-exchange-alt"></i> Transactions
      </a>
    </div>

    <!-- Main Content -->
    <div class="dashboard">
      <div class="card">
        <div class="card-header">
          <div class="card-icon">
            <i class="fas fa-icon"></i>
          </div>
          <div class="card-title">Card Title</div>
        </div>
        <div class="card-content">
          <!-- Card content here -->
        </div>
      </div>
    </div>
  </div>

  <script src="app.js"></script>
</body>
</html>
```

### Form Template
```html
<form class="form-container" id="exampleForm">
  <div class="form-group">
    <label for="field1">Field Label</label>
    <input type="text" id="field1" name="field1" placeholder="Enter value" required>
  </div>

  <div class="form-group">
    <label for="field2">Select Field</label>
    <select id="field2" name="field2" required>
      <option value="">Choose an option</option>
      <option value="option1">Option 1</option>
      <option value="option2">Option 2</option>
    </select>
  </div>

  <div class="form-group">
    <label>File Upload</label>
    <div class="file-upload" onclick="document.getElementById('fileInput').click()">
      <i class="fas fa-cloud-upload-alt"></i>
      <div class="file-upload-text">Click to upload file</div>
      <div class="file-upload-subtext">JPG, PNG, PDF (Max 5MB)</div>
    </div>
    <input type="file" id="fileInput" accept="image/*,.pdf" style="display: none">
  </div>

  <button type="submit" class="btn btn-primary">
    <i class="fas fa-check"></i> Submit Form
  </button>
</form>
```

### Modal Template
```html
<div id="exampleModal" class="modal">
  <div class="modal-content">
    <div class="modal-header">
      <div class="modal-title">Modal Title</div>
      <span class="close" onclick="closeModal('exampleModal')">&times;</span>
    </div>
    
    <div class="modal-body">
      <!-- Modal content here -->
    </div>
    
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal('exampleModal')">
        Cancel
      </button>
      <button class="btn btn-primary" onclick="confirmAction()">
        Confirm
      </button>
    </div>
  </div>
</div>
```

---

## Development Guidelines

### File Structure
```
frontend/
├── assets/
│   ├── css/
│   │   ├── main.css
│   │   ├── components.css
│   │   └── responsive.css
│   ├── js/
│   │   ├── app.js
│   │   ├── api.js
│   │   └── components.js
│   └── images/
├── templates/
│   ├── dashboard.html
│   ├── wallet.html
│   ├── transactions.html
│   └── kyc.html
└── index.html
```

### CSS Organization
```css
/* main.css */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* CSS Custom Properties */
:root {
  /* Colors */
  --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  /* ... other variables */
}

/* Base Styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: "Inter", "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  background: var(--primary-gradient);
  min-height: 100vh;
  color: var(--text-primary);
  line-height: 1.6;
}

/* Utility Classes */
.container { /* ... */ }
.grid { /* ... */ }
.btn { /* ... */ }
```

### JavaScript Organization
```javascript
// app.js - Main application logic
class KingdomPayApp {
  constructor() {
    this.api = new KingdomPayAPI();
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.loadInitialData();
  }

  setupEventListeners() {
    // Global event listeners
  }

  loadInitialData() {
    // Load initial page data
  }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new KingdomPayApp();
});
```

### Performance Best Practices

1. **Optimize Images**
   - Use WebP format when possible
   - Implement lazy loading
   - Provide multiple sizes for responsive images

2. **Minimize Dependencies**
   - Use CDN for common libraries
   - Bundle and minify CSS/JS
   - Remove unused CSS

3. **Caching Strategy**
   - Implement service worker for offline functionality
   - Cache API responses appropriately
   - Use browser caching headers

4. **Accessibility**
   - Use semantic HTML elements
   - Provide alt text for images
   - Ensure keyboard navigation works
   - Maintain proper color contrast ratios

### Testing Guidelines

1. **Cross-Browser Testing**
   - Test on Chrome, Firefox, Safari, Edge
   - Test on mobile browsers (iOS Safari, Chrome Mobile)

2. **Responsive Testing**
   - Test on various screen sizes (320px to 1920px)
   - Test orientation changes on mobile devices

3. **Performance Testing**
   - Use Lighthouse for performance audits
   - Test on slow 3G connections
   - Monitor Core Web Vitals

4. **Accessibility Testing**
   - Use screen readers for testing
   - Test keyboard-only navigation
   - Validate with accessibility tools

---

## Conclusion

This design system provides a comprehensive foundation for building the KingdomPay frontend. The components are designed to be:

- **Reusable**: Consistent patterns across all pages
- **Accessible**: WCAG 2.1 AA compliant
- **Responsive**: Mobile-first approach
- **Performant**: Optimized for speed and efficiency
- **Maintainable**: Clear structure and documentation

Use this guide as a reference when building new features or updating existing ones. Always test thoroughly across different devices and browsers to ensure the best user experience.

