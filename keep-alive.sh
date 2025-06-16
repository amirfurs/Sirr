#!/bin/bash

# 🚀 Keep Render Service Alive Script
# استخدم هذا الـ script على أي server للحفاظ على خدمة Render نشطة

# ============ Configuration ============
# غير هذا الرابط برابط خدمتك على Render
SERVICE_URL="https://YOUR_RENDER_URL.onrender.com"

# ============ Colors for output ============
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============ Functions ============
log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success_message() {
    echo -e "${GREEN}✅ $1${NC}"
}

error_message() {
    echo -e "${RED}❌ $1${NC}"
}

warning_message() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

ping_service() {
    local endpoint=$1
    local description=$2
    
    log_message "Pinging $description..."
    
    if curl -f -s --max-time 30 "$SERVICE_URL$endpoint" > /dev/null 2>&1; then
        success_message "$description ping successful"
        return 0
    else
        error_message "$description ping failed"
        return 1
    fi
}

# ============ Main Script ============
log_message "🚀 Starting Render Keep-Alive Service"
log_message "🎯 Target: $SERVICE_URL"

if [ "$SERVICE_URL" = "https://YOUR_RENDER_URL.onrender.com" ]; then
    error_message "Please update SERVICE_URL in the script with your actual Render URL!"
    exit 1
fi

# Counter for successful pings
successful_pings=0
failed_pings=0

# Main loop
while true; do
    log_message "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_message "💓 Keep-Alive Ping #$((successful_pings + failed_pings + 1))"
    
    # Try multiple endpoints
    endpoints=(
        "/wake-up:Wake-up"
        "/api/keep-alive:Keep-alive"
        "/:Root"
        "/api/health:Health Check"
    )
    
    ping_success=false
    
    for endpoint_info in "${endpoints[@]}"; do
        IFS=':' read -r endpoint description <<< "$endpoint_info"
        
        if ping_service "$endpoint" "$description"; then
            ping_success=true
            break
        fi
        
        sleep 2  # Small delay between attempts
    done
    
    if [ "$ping_success" = true ]; then
        successful_pings=$((successful_pings + 1))
        success_message "Service is alive! (Success: $successful_pings, Failed: $failed_pings)"
    else
        failed_pings=$((failed_pings + 1))
        error_message "All pings failed! (Success: $successful_pings, Failed: $failed_pings)"
        
        if [ $failed_pings -ge 5 ]; then
            warning_message "Service appears to be down after 5 consecutive failures!"
            # You can add notification logic here (email, webhook, etc.)
        fi
    fi
    
    log_message "😴 Sleeping for 5 minutes..."
    sleep 300  # 5 minutes
done