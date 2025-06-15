# 🔧 Environment Variables Setup for Render

## For Render Dashboard - Environment Variables Section

Copy and paste these values into your Render service environment variables:

### 1. DISCORD_BOT_TOKEN
```
MTM4Mzc4ODc5Mzc4NTYxNDM0Ng.G-LVFF.rVYUsXhkP_xLe7I8cSWhnAamGiwA0Rh7N0mVmU
```

### 2. DB_NAME
```
discord_bot_db
```

### 3. MONGO_URL
You need to replace `<db_password>` with your actual MongoDB Atlas password:

**Template:**
```
mongodb+srv://arkoubioussam:YOUR_ACTUAL_PASSWORD@cluster0.6ioi3mk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
```

**Example (replace YOUR_ACTUAL_PASSWORD with real password):**
```
mongodb+srv://arkoubioussam:mypassword123@cluster0.6ioi3mk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
```

## 🔐 To Get Your MongoDB Password:

1. Go to [MongoDB Atlas](https://cloud.mongodb.com/)
2. Sign in to your account
3. Go to "Database Access" in the left sidebar
4. Find your user `arkoubioussam`
5. Click "Edit" next to the user
6. Either:
   - View the existing password (if saved)
   - Or set a new password
7. Copy the password and replace `<db_password>` in the connection string

## 📝 Alternative: Create New Database User

If you don't remember the password, create a new database user:

1. In MongoDB Atlas, go to "Database Access"
2. Click "Add New Database User"
3. Choose "Password" authentication
4. Username: `discord_bot_user`
5. Password: Generate a strong password (save it!)
6. Database User Privileges: "Read and write to any database"
7. Click "Add User"

Then use this connection string:
```
mongodb+srv://discord_bot_user:YOUR_NEW_PASSWORD@cluster0.6ioi3mk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
```

## 🚀 Ready to Deploy?

Once you have the correct MongoDB password, you can deploy to Render!