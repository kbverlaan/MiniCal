#!/usr/bin/env python3
"""
Daily summary script - runs at 23:00
Sends complete day overview to all users
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

def format_summary_message(user: dict, totals: dict, today_formatted: str) -> str:
    """Format the daily summary message."""
    net_cal = totals['net_calories']
    goal = user['daily_calories']
    diff = net_cal - goal
    
    # Status emoji
    if diff < -200:
        status = "⚠️ Ver onder doel"
    elif diff < 0:
        status = "✅ Onder doel"
    elif diff <= 100:
        status = "🎯 Perfect!"
    else:
        status = "⚠️ Boven doel"
    
    message = f"""📊 **Dagoverzicht** ({today_formatted})

🍽️ **GEGETEN**
{totals['total_calories']} kcal
Protein: {totals['total_protein']:.1f}g
Carbs: {totals['total_carbs']:.1f}g
Vet: {totals['total_fat']:.1f}g

🔥 **VERBRAND**
{totals['total_burned']} kcal

📈 **NETTO**
{net_cal} kcal

🎯 **DOEL vs WERKELIJK**
Doel: {goal} kcal
Verschil: {diff:+d} kcal
{status}

📝 **OVERZICHT**
{totals['meal_count']} maaltijd(en) • {totals['workout_count']} workout(s)

Morgen is er weer een dag! 💪"""

    return message

def main():
    """Daily summary at 23:00 - send complete overview to all users."""
    print("🕚 DAILY SUMMARY - 23:00")
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
            
            # Format summary message
            message = format_summary_message(user, totals, today_formatted)
            
            # Send via Telegram
            if send_telegram_message(bot_token, user['telegram_id'], message):
                print(f"✅ Sent summary to user {user['telegram_id']} (net: {totals['net_calories']} kcal)")
                success_count += 1
            else:
                print(f"❌ Failed to send to user {user['telegram_id']}")
                
        except Exception as e:
            print(f"❌ Error processing user {user['id']}: {e}")
            continue
    
    print("\n" + "=" * 50)
    print(f"🎯 Daily summary completed: {success_count}/{len(users)} users notified")
    print(f"🌙 Good night! See you tomorrow at 22:00")

if __name__ == "__main__":
    main()
