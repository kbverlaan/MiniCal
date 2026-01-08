import os
from dotenv import load_dotenv
from app.telegram.handler import setup_telegram_bot
from app.database.supabase_client import supabase_client

def main() -> None:
    """Start the MiniCal bot."""
    load_dotenv()

    # Test database connection
    print("--- Testing Supabase Connection ---")
    if supabase_client.test_connection():
        print("✅ Successfully connected to Supabase.")
    else:
        print("❌ Failed to connect to Supabase. Check credentials.")
        return
    print("-------------------------------------")

    # Setup and run Telegram bot
    bot_token = os.getenv("TELEGRAM_API_TOKEN")
    if not bot_token:
        raise ValueError("TELEGRAM_API_TOKEN not found in .env file")

    application = setup_telegram_bot(bot_token)
    print("🚀 Starting MiniCal Telegram bot...")
    application.run_polling()

if __name__ == "__main__":
    main()
