# 🌐 Discord Bot Web Service - Render Deployment Guide

## 🚀 **Web Service Features:**

✅ **FastAPI Web Interface** - Manage your bot via HTTP API  
✅ **Discord Bot Running 24/7** - All Arabic commands working  
✅ **Web Dashboard Access** - Control bot remotely  
✅ **API Endpoints** - Integration with other services  
✅ **Real-time Logs** - Monitor bot activity  

## 📊 **Available Web Endpoints:**

### 🤖 **Bot Management:**
- `GET /api/bot/status` - Check bot status
- `POST /api/bot/start` - Start the bot
- `POST /api/bot/stop` - Stop the bot
- `POST /api/bot/restart` - Restart the bot
- `GET /api/bot/logs` - Get bot logs

### 📈 **Statistics & Reports:**
- `GET /api/bot/moderation-logs` - Get moderation logs
- `GET /api/bot/server-activity` - Server activity statistics
- `GET /api/bot/reports/daily` - Daily reports
- `GET /api/bot/reports/violations` - Violations report

### 🔧 **System:**
- `GET /api/health` - Health check
- `GET /api/` - API info

## 🌐 **Your Render Web Service URL:**

After deployment, you'll get a URL like:
```
https://discord-bot-arabic-web.onrender.com
```

### 📱 **Access Examples:**

**Bot Status:**
```
https://your-app.onrender.com/api/bot/status
```

**Health Check:**
```
https://your-app.onrender.com/api/health
```

**Daily Report:**
```
https://your-app.onrender.com/api/bot/reports/daily
```

## 🚀 **Deployment Steps:**

### 1. **Environment Variables for Render:**
```
DISCORD_BOT_TOKEN=MTM4Mzc4ODc5Mzc4NTYxNDM0Ng.G-LVFF.rVYUsXhkP_xLe7I8cSWhnAamGiwA0Rh7N0mVmU

MONGO_URL=mongodb+srv://arkoubioussam:vXvLY1zxbkU2zgj9@cluster0.2ps5tzx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0

DB_NAME=discord_bot_db

PORT=10000
```

### 2. **Deploy on Render:**
- Go to [render.com](https://render.com)
- Click **"New"** → **"Web Service"** 
- Connect your GitHub repository
- Or use **"Blueprint"** (detects render.yaml automatically)

### 3. **Configuration:**
- **Build Command**: `pip install -r backend/requirements.txt`
- **Start Command**: `cd backend && python web_server.py`
- **Environment**: `Python 3`

### 4. **Monitor Deployment:**
Watch logs for:
```
Starting Discord Bot Web Service...
Discord bot thread started
Siraj ● سراج قد اتصل بديسكورد!
Starting FastAPI web server on port 10000...
```

## 🎯 **Benefits of Web Service vs Worker:**

| Feature | Web Service | Background Worker |
|---------|-------------|-------------------|
| Discord Bot | ✅ 24/7 | ✅ 24/7 |
| Web API Access | ✅ Yes | ❌ No |
| Remote Management | ✅ Yes | ❌ No |
| Statistics Dashboard | ✅ Yes | ❌ No |
| Public URL | ✅ Yes | ❌ No |
| Integration Ready | ✅ Yes | ❌ Limited |

## 🔧 **Web Service Commands:**

### **Start/Stop Bot Remotely:**
```bash
# Start bot
curl -X POST https://your-app.onrender.com/api/bot/start

# Stop bot  
curl -X POST https://your-app.onrender.com/api/bot/stop

# Check status
curl https://your-app.onrender.com/api/bot/status
```

### **Get Reports:**
```bash
# Daily report
curl https://your-app.onrender.com/api/bot/reports/daily

# Server activity
curl https://your-app.onrender.com/api/bot/server-activity
```

## 💰 **Render Free Tier:**
- **750 hours/month** free
- **Public HTTPS URL** included
- **Automatic SSL certificate**
- **Custom domain** support (optional)

## 🛡️ **Discord Bot Features:**

All 20 Arabic commands available:
- **إدارة**: `/مسح` `/كتم` `/طرد` `/حظر` `/تحذير`
- **إعلانات**: `/إعلان` `/استبيان` 
- **إحصائيات**: `/الإحصائيات` `/تقرير_يومي` `/أكثر_نشاط`
- **عام**: `/اختبار` `/مساعدة`

## ✅ **Ready to Deploy!**

Your web service is configured and ready. The Discord bot will run automatically in the background when the web service starts.

**Next Step**: Deploy to Render and get your public URL! 🚀