#!/usr/bin/env python3
"""
Daily check script - runs at 22:00
Asks all users: "Staat alles erin voor vandaag?"
"""

import os
import sys
import pytz
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.supabase_client import supabase_client
from app.config import BotConfig
import requests

def send_telegram_message(bot_token: str, chat_id: int, message: str):
    """Send a message via Telegram API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")
        return False

def main():
    """Daily check at 22:00 - ask users if everything is logged."""
    print("🕙 DAILY CHECK - 22:00")
    print("=" * 50)
    
    load_dotenv()
    
    # Test database
    if not supabase_client.test_connection():
        print("❌ Database connection failed")
        return
    
    print("✅ Database connected")
    
    # Get bot token
    bot_token = os.getenv("TELEGRAM_API_TOKEN")
    if not bot_token:
        print("❌ TELEGRAM_API_TOKEN not found")
        return
    
    # Get all users
    users = supabase_client.get_all_users()
    print(f"📊 Found {len(users)} users")
    
    # Get today's date
    tz = pytz.timezone(BotConfig.TIMEZONE)
    today = datetime.now(tz).date().isoformat()
    today_formatted = datetime.now(tz).strftime('%d-%m-%Y')
    
    success_count = 0
    
    for user in users:
        try:
            # Get today's totals
            totals = supabase_client.get_daily_totals(user['id'], today)
            
            # Compose message
            message = f"""⏰ **Dagelijkse Check** ({today_formatted})

Staat alles erin voor vandaag?

📊 **Je huidige stand:**
🍽️ Gegeten: {totals['total_calories']} kcal
🔥 Verbrand: {totals['total_burned']} kcal
📈 Netto: {totals['net_calories']} kcal

🎯 Doel: {user['daily_calories']} kcal
Verschil: {totals['net_calories'] - user['daily_calories']:+d} kcal

Heb je nog iets gegeten of getraind dat je wilt toevoegen?
Stuur gewoon een bericht! Over een uur krijg je je volledige dagoverzicht."""
            
            # Send via Telegram
            if send_telegram_message(bot_token, user['telegram_id'], message):
                print(f"✅ Sent check to user {user['telegram_id']}")
                success_count += 1
            else:
                print(f"❌ Failed to send to user {user['telegram_id']}")
                
        except Exception as e:
            print(f"❌ Error processing user {user['id']}: {e}")
            continue
    
    print("\n" + "=" * 50)
    print(f"🎯 Daily check completed: {success_count}/{len(users)} users notified")
    print(f"⏰ Next: Daily summary at 23:00")

if __name__ == "__main__":
    main()
