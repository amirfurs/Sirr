# 🚀 Guide: Deploy Discord Bot to Render

This guide will help you deploy your Arabic Discord bot as a background worker on Render.

## 📋 Prerequisites

Before deployment, ensure you have:

1. **Discord Bot Token** - Get it from [Discord Developer Portal](https://discord.com/developers/applications)
2. **MongoDB Database** - Free option: [MongoDB Atlas](https://cloud.mongodb.com/)
3. **Render Account** - Sign up at [render.com](https://render.com)
4. **Git Repository** - Your code needs to be in a Git repository (GitHub, GitLab, etc.)

## 🛠️ Step 1: Prepare Your Repository

1. **Push your code to GitHub/GitLab**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Discord bot with Arabic commands"
   git branch -M main
   git remote add origin YOUR_REPOSITORY_URL
   git push -u origin main
   ```

## 🔧 Step 2: Set up MongoDB (if needed)

If you don't have MongoDB set up:

1. Go to [MongoDB Atlas](https://cloud.mongodb.com/)
2. Create a free account and cluster
3. Create a database user
4. Get your connection string (it should look like: `mongodb+srv://username:password@cluster.mongodb.net/`)

## 🌐 Step 3: Deploy on Render

### Option A: Using render.yaml (Recommended)

1. **Connect Repository**:
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New" → "Blueprint"
   - Connect your Git repository
   - Render will automatically detect the `render.yaml` file

2. **Set Environment Variables**:
   After deployment starts, go to your service settings and add:
   ```
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   MONGO_URL=your_mongodb_connection_string_here
   DB_NAME=discord_bot_db
   ```

### Option B: Manual Setup

1. **Create Background Worker**:
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New" → "Background Worker"
   - Connect your Git repository

2. **Configure Service**:
   - **Name**: `discord-bot-arabic`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && python start_bot.py`

3. **Set Environment Variables**:
   ```
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   MONGO_URL=your_mongodb_connection_string_here
   DB_NAME=discord_bot_db
   ```

## 🔐 Environment Variables Details

| Variable | Description | Example |
|----------|-------------|---------|
| `DISCORD_BOT_TOKEN` | Your Discord bot token | `MTIzNDU2Nzg5MDEyMzQ1Njc4OTAuXXXXXX.YYYYYY` |
| `MONGO_URL` | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `DB_NAME` | Database name | `discord_bot_db` |

## 🚀 Step 4: Deploy

1. Click "Create Background Worker" or "Deploy"
2. Render will:
   - Clone your repository
   - Install dependencies
   - Start your bot
3. Check the logs to ensure everything is working

## 📊 Step 5: Monitor Your Bot

### Check Logs
- Go to your service in Render dashboard
- Click on "Logs" tab
- You should see messages like:
  ```
  Bot connected to Discord!
  Bot is in X servers
  Synced X command(s)
  ```

### Test Your Bot
In Discord, use these commands to test:
- `/اختبار` - Test if bot is working
- `/مساعدة` - Show help menu
- `/مسح 5` - Clear 5 messages (if you have permissions)

## 🛠️ Available Commands

Your bot includes these Arabic commands:

### 🛡️ Moderation Commands
- `/مسح [عدد]` - Clear messages
- `/كتم @عضو [دقائق] [سبب]` - Mute member
- `/فك_كتم @عضو` - Unmute member
- `/طرد @عضو [سبب]` - Kick member
- `/حظر @عضو [سبب]` - Ban member
- `/فك_حظر [معرف_العضو]` - Unban member
- `/تحذير @عضو [سبب]` - Warn member

### 📢 Announcements & Polls
- `/إعلان [عنوان] [محتوى]` - Create announcement
- `/استبيان [سؤال] [خيارات]` - Create poll

### 📊 Statistics & Reports
- `/الإحصائيات` - Server statistics
- `/تقرير_يومي` - Daily report
- `/أكثر_نشاط [فترة]` - Most active members
- `/إحصائيات_عضو @عضو` - Member statistics

### ℹ️ General Commands
- `/اختبار` - Test bot
- `/مساعدة` - Help menu

## 🔧 Troubleshooting

### Common Issues:

1. **Bot not responding**:
   - Check if `DISCORD_BOT_TOKEN` is correct
   - Ensure bot has required permissions in your Discord server

2. **Database errors**:
   - Verify `MONGO_URL` is correct
   - Check if MongoDB cluster is running
   - Ensure network access is allowed from anywhere (0.0.0.0/0)

3. **Commands not showing**:
   - Wait a few minutes for Discord to sync commands
   - Try re-inviting the bot with proper permissions

4. **Service crashes**:
   - Check Render logs for error messages
   - Ensure all environment variables are set correctly

### Bot Permissions Required:
When inviting your bot to Discord servers, ensure it has these permissions:
- Send Messages
- Use Slash Commands
- Manage Messages (for clear command)
- Moderate Members (for mute/timeout)
- Kick Members
- Ban Members
- View Audit Log

## 💰 Costs

- **Render Background Worker**: Free tier available (750 hours/month)
- **MongoDB Atlas**: Free tier (512MB storage)
- **Total**: FREE for small/medium Discord servers

## 🔄 Updates

To update your bot:
1. Push changes to your Git repository
2. Render will automatically redeploy
3. Your bot will restart with new code

## 📞 Support

If you encounter issues:
1. Check Render service logs
2. Verify all environment variables
3. Test Discord bot permissions
4. Check MongoDB connection

---

**🎉 Congratulations!** Your Arabic Discord bot is now running 24/7 on Render!