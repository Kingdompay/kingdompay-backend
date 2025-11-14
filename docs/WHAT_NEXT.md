# What's Next? - KingdomPay Roadmap

## ✅ Current Status

**Phase 2 Core Features**: **COMPLETE**

- ✅ Payment providers (M-Pesa, Airtel, T-Kash)
- ✅ Fees & contributions integrated
- ✅ Multi-signature approvals
- ✅ Risk & AML checks
- ✅ Reconciliation system
- ✅ Hosted checkout & QR codes
- ✅ All tests passing (89/89)

**Deployment Readiness**: **READY**

- ✅ Documentation complete
- ✅ SDK created
- ✅ Deployment scripts ready
- ✅ Environment templates ready

---

## 🎯 Immediate Next Steps (Priority Order)

### 1. **Provider Credentials & Testing** (CRITICAL - Do First)

**Status**: Not started  
**Time**: 2-4 hours

**What to do**:

1. Get M-Pesa Daraja credentials from https://developer.safaricom.co.ke/
2. Get Airtel Money credentials from https://openapi.airtel.africa/
3. Get T-Kash credentials (contact T-Kash)
4. Update `.env` with credentials
5. Test STK Push flow end-to-end
6. Verify webhooks are received

**Files to update**:

- `.env` (add provider credentials)
- Test with: `curl -X POST http://localhost:5001/api/v1/topups/momo`

**Success criteria**:

- [ ] Can initiate STK Push
- [ ] Webhook received and processed
- [ ] Wallet balance updated correctly

---

### 2. **Staging Environment Deployment** (HIGH PRIORITY)

**Status**: Ready to deploy  
**Time**: 1-2 hours

**What to do**:

1. Set up staging server (AWS/GCP/Azure)
2. Configure environment variables
3. Run deployment script: `./scripts/deploy.sh staging deploy`
4. Verify system wallets created
5. Test core flows

**Commands**:

```bash
# Deploy
./scripts/deploy.sh staging deploy

# Check system wallets
docker-compose exec backend flask shell
# Then: Wallet.query.filter(Wallet.owner_type.in_(['PLATFORM', 'FEDERAL'])).all()
```

**Success criteria**:

- [ ] Staging environment running
- [ ] System wallets exist
- [ ] Health check passes
- [ ] Can create users and communities

---

### 3. **Phase 1 Gaps: Mandates & Invoices** (MEDIUM PRIORITY)

**Status**: Not implemented  
**Time**: 1-2 days

**What's missing**:

#### 3.1 Recurring Giving (Mandates)

**Models needed**:

- `Mandate` model (user_id, community_id, amount, frequency, next_run_at, status)
- `MandateExecution` model (mandate_id, payment_id, executed_at, status)

**Routes needed**:

- `POST /api/v1/mandates` - Create recurring giving mandate
- `GET /api/v1/mandates` - List user's mandates
- `PUT /api/v1/mandates/{id}` - Update/pause mandate
- `DELETE /api/v1/mandates/{id}` - Cancel mandate

**Scheduler needed**:

- Background job (Celery/cron) to process mandates
- Runs daily, checks `next_run_at <= now()`
- Creates payment using TransferService
- Updates `next_run_at` based on frequency

**Files to create**:

- `models/mandate.py`
- `routes/mandate_routes.py`
- `services/mandate_service.py`
- `tasks/mandate_scheduler.py` (or Celery task)

#### 3.2 Invoicing

**Models needed**:

- `Invoice` model (community_id, to_wallet_id, amount, due_date, status, items_json)
- `InvoicePayment` model (invoice_id, payment_id, amount_paid)

**Routes needed**:

- `POST /api/v1/invoices` - Create invoice
- `GET /api/v1/invoices` - List invoices
- `GET /api/v1/invoices/{id}` - Get invoice details
- `POST /api/v1/invoices/{id}/pay` - Pay invoice
- `GET /api/v1/invoices/{id}/pdf` - Generate PDF receipt

**Files to create**:

- `models/invoice.py`
- `routes/invoice_routes.py`
- `services/invoice_service.py`
- `templates/invoice_pdf.html` (for PDF generation)

---

### 4. **SDK Documentation: Android/iOS** (LOW PRIORITY)

**Status**: JS SDK done, mobile docs needed  
**Time**: 2-4 hours

**What to do**:

1. Document Android SDK integration pattern
2. Document iOS SDK integration pattern
3. Provide code examples
4. Document authentication flow

**Files to create**:

- `sdk/android/README.md`
- `sdk/ios/README.md`
- `sdk/android/example.kt` (Kotlin example)
- `sdk/ios/example.swift` (Swift example)

**Content should include**:

- How to initialize SDK
- How to handle authentication
- How to initiate payments
- How to handle webhooks/callbacks
- Error handling patterns

---

### 5. **Production Hardening** (BEFORE GO-LIVE)

**Status**: Not started  
**Time**: 1-2 weeks

**Security**:

- [ ] Move secrets to Vault/KMS (remove from .env)
- [ ] Enable HTTPS/TLS everywhere
- [ ] Set up HSTS headers
- [ ] Run security audit (OWASP, dependency scan)
- [ ] Penetration testing

**Monitoring**:

- [ ] Set up Prometheus metrics
- [ ] Configure Grafana dashboards (see `docs/observability/dashboards.md`)
- [ ] Set up alerts (PagerDuty/Slack)
- [ ] Log aggregation (ELK/CloudWatch)

**Operations**:

- [ ] Database backups (automated, tested restore)
- [ ] Disaster recovery plan
- [ ] Runbooks for common incidents
- [ ] Load testing (target: 200 RPS)
- [ ] Failover testing

**Compliance**:

- [ ] CBK NPS regulations compliance checklist
- [ ] Data Protection Act 2019 compliance
- [ ] AML/CFT procedures documented
- [ ] Privacy policy and terms of service

---

### 6. **Phase 3 Features** (FUTURE)

**Status**: Not started  
**Time**: 4-6 weeks

**Features**:

- Bill payments (utilities, etc.)
- Treasury/Float management
- Disputes & refunds system
- Advanced reporting & analytics

**See original plan**: Phase 3 details in engineering blueprint

---

## 📋 Quick Action Checklist

**This Week**:

- [ ] Get provider credentials (M-Pesa, Airtel, T-Kash)
- [ ] Test provider integrations locally
- [ ] Deploy to staging
- [ ] Verify webhooks work

**Next Week**:

- [ ] Implement Mandates (recurring giving)
- [ ] Implement Invoices
- [ ] Document mobile SDKs

**Before Production**:

- [ ] Security audit
- [ ] Load testing
- [ ] Monitoring setup
- [ ] Compliance review

---

## 🚀 Ready to Start?

**If you want to start with provider testing**:

```bash
# 1. Get credentials from provider dashboards
# 2. Update .env with credentials
# 3. Start services
docker-compose up -d

# 4. Test STK Push
curl -X POST http://localhost:5001/api/v1/topups/momo \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "phone": "+254712345678", "provider": "MPESA"}'
```

**If you want to implement Mandates/Invoices**:

- Start with `models/mandate.py` and `models/invoice.py`
- Then create routes
- Then add scheduler for mandates

**If you want to deploy to staging**:

- Follow `docs/STAGING_BRINGUP.md`
- Use `./scripts/deploy.sh staging deploy`

---

## 📚 Reference Documents

- `docs/STAGING_BRINGUP.md` - Staging setup
- `docs/WEBHOOK_INTEGRATION.md` - Webhook configuration
- `docs/QUICK_START.md` - Local development
- `docs/NEXT_STEPS_SUMMARY.md` - Detailed next steps
- `sdk/js/README.md` - JS SDK usage

---

## ❓ Questions?

**What should I do first?**
→ Start with **Provider Credentials & Testing** (#1) - it's critical and quick.

**Can I skip Mandates/Invoices?**
→ Yes, they're Phase 1 gaps but not blocking. You can launch without them and add later.

**When can we go to production?**
→ After completing #1, #2, and #5 (Production Hardening). Estimate: 2-3 weeks.

**What's the biggest risk?**
→ Provider integration issues. Test thoroughly before production.
