# KingdomPay Deployment Guide - Render

## 🚀 Quick Deploy to Render

### Prerequisites

- GitHub repository with your code
- Render account (free tier available)

### Step 1: Prepare Your Repository

1. **Push your code to GitHub** (if not already done):

```bash
git add .
git commit -m "Initial Flask app setup"
git push origin main
```

2. **Verify these files are in your repo**:
   - ✅ `app.py`
   - ✅ `requirements.txt`
   - ✅ `render.yaml`
   - ✅ `Procfile`
   - ✅ `.renderignore`

### Step 2: Deploy on Render

1. **Go to Render Dashboard**: https://render.com/dashboard
2. **Click "New +"** → **"Blueprint"**
3. **Connect your GitHub repository**
4. **Select your repository** and branch (usually `main`)
5. **Render will automatically detect** the `render.yaml` file
6. **Click "Apply"** to deploy

### Step 3: Configure Environment Variables

After deployment, go to your service settings and add these environment variables:

#### Required for Production:

```
FLASK_ENV=production
LOG_LEVEL=INFO
```

#### Optional (for external services):

```
SMS_PROVIDER_API_KEY=your-sms-key
SMS_PROVIDER_URL=https://api.sms-provider.com
EMAIL_SERVER=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

### Step 4: Run Database Migrations

1. **Go to your service** in Render dashboard
2. **Click "Shell"** tab
3. **Run these commands**:

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Step 5: Test Your Deployment

1. **Get your service URL** from Render dashboard
2. **Test health endpoint**: `GET https://your-app.onrender.com/health`
3. **Expected response**:

```json
{
  "status": "healthy",
  "service": "kingdompay-api",
  "version": "1.0.0"
}
```

## 🔧 Render Configuration Details

### What `render.yaml` Does:

- **Creates PostgreSQL database** (free tier: 1GB)
- **Creates Redis instance** (free tier: 25MB)
- **Sets up web service** (free tier: 750 hours/month)
- **Generates secure keys** automatically
- **Links database and Redis** to your app

### Free Tier Limits:

- **Web Service**: 750 hours/month (sleeps after 15 min inactivity)
- **Database**: 1GB PostgreSQL
- **Redis**: 25MB memory
- **Bandwidth**: 100GB/month

### Production Considerations:

- **Upgrade to paid plans** for 24/7 uptime
- **Add custom domain** for production
- **Set up monitoring** and alerts
- **Configure SSL** (automatic with Render)

## 🐛 Troubleshooting

### Common Issues:

1. **Build fails**:

   - Check `requirements.txt` has all dependencies
   - Verify Python version compatibility

2. **Database connection fails**:

   - Wait 2-3 minutes after database creation
   - Check `DATABASE_URL` is set correctly

3. **App sleeps**:

   - Free tier apps sleep after 15 min inactivity
   - First request after sleep takes 30-60 seconds
   - Upgrade to paid plan for 24/7 uptime

4. **Environment variables not working**:
   - Restart service after adding new env vars
   - Check variable names match exactly

### Debug Commands:

```bash
# Check logs
# Go to Render dashboard → Your service → Logs

# Check environment variables
# Go to Render dashboard → Your service → Environment

# Access shell
# Go to Render dashboard → Your service → Shell
```

## 📊 Monitoring

### Built-in Monitoring:

- **Uptime monitoring** (paid plans)
- **Log aggregation** (all plans)
- **Performance metrics** (paid plans)

### Health Check:

- **Endpoint**: `/health`
- **Expected**: 200 OK with service status
- **Use for**: Uptime monitoring, load balancer health checks

## 🔄 Continuous Deployment

### Automatic Deploys:

- **Enabled by default** when connected to GitHub
- **Triggers on**: Push to main branch
- **Builds**: Automatically from `render.yaml`

### Manual Deploys:

- **Go to service** → **"Manual Deploy"**
- **Select branch** → **"Deploy latest commit"**

## 💰 Cost Breakdown

### Free Tier (Perfect for MVP):

- **Web Service**: $0 (750 hours/month)
- **PostgreSQL**: $0 (1GB)
- **Redis**: $0 (25MB)
- **Total**: $0/month

### Paid Plans (When Ready):

- **Starter**: $7/month (always-on web service)
- **Standard**: $25/month (better performance)
- **Pro**: $85/month (high availability)

## ✅ Next Steps After Deployment

1. **Test all endpoints** work correctly
2. **Set up external services** (SMS, Email)
3. **Configure monitoring** and alerts
4. **Set up custom domain** (optional)
5. **Plan database backups** (paid feature)

Your KingdomPay API will be live at: `https://your-app-name.onrender.com`
