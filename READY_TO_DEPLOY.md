# Discord Bot - Ready for Render Deployment
# Environment Variables - Copy these to Render Dashboard

## Environment Variables for Render:

DISCORD_BOT_TOKEN=MTM4Mzc4ODc5Mzc4NTYxNDM0Ng.G-LVFF.rVYUsXhkP_xLe7I8cSWhnAamGiwA0Rh7N0mVmU

MONGO_URL=mongodb+srv://arkoubioussam:vXvLY1zxbkU2zgj9@cluster0.2ps5tzx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0

DB_NAME=discord_bot_db

## ✅ All credentials are ready for deployment!

## 🚀 Deployment Steps:

### 1. Push to GitHub (if not done):
```bash
git add .
git commit -m "Discord bot ready for Render"
git push origin main
```

### 2. Deploy to Render:
- Go to https://render.com
- Click "New" → "Blueprint" 
- Connect your GitHub repository
- Render will detect the render.yaml file

### 3. Add Environment Variables:
In Render dashboard, add the three variables above exactly as shown.

### 4. Deploy!
Click "Deploy" and watch the logs for "Bot connected to Discord!"

## 🧪 Test Commands:
- /اختبار - Test bot
- /مساعدة - Help menu
- /مسح 5 - Clear messages (if you have permissions)

## Bot Features:
✅ Arabic commands for moderation
✅ Statistics and reporting
✅ Announcements and polls
✅ 24/7 uptime on Render
✅ Free hosting (750 hours/month)