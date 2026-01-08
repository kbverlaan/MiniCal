import pytz
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

from app.database.supabase_client import supabase_client
from app.services.llm_service import llm_service
from app.config import BotConfig

# Store conversation context per user
# Format: {user_id: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
conversation_context = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    
    # Create or get user
    user = supabase_client.get_or_create_user(user_id, username)
    
    if user:
        welcome_msg = f"""👋 Welkom bij MiniCal!

Ik help je om je calorieën te tracken. Super simpel:

📝 **Hoe werkt het?**
Stuur gewoon een bericht met wat je hebt gegeten en/of welke workout je hebt gedaan.

Bijvoorbeeld:
"2 eieren met toast en een banaan"
"uurtje hardlopen gedaan"
"bulgogi rijst met sla, daarna 45 min krachttraining"

⏰ **Dagelijkse checks:**
• 22:00 - Ik vraag of alles erin staat
• 23:00 - Je krijgt je dagoverzicht

🎯 **Je huidige doelen:**
• Calorieën: {user['daily_calories']} kcal
• Protein: {user['daily_protein']}g
• Carbs: {user['daily_carbs']}g
• Vet: {user['daily_fat']}g

Gebruik /setgoals om je doelen aan te passen.
Gebruik /today voor je huidige stand van vandaag.

Let's go! 🚀"""
        await update.message.reply_text(welcome_msg)
    else:
        await update.message.reply_text("❌ Er ging iets fout. Probeer het opnieuw.")

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /today command - show current day stats."""
    telegram_id = update.message.from_user.id
    
    # Get user from database
    user = supabase_client.get_or_create_user(telegram_id)
    if not user:
        await update.message.reply_text("❌ Gebruiker niet gevonden. Gebruik /start eerst.")
        return
    
    # Get today's date in Amsterdam timezone
    tz = pytz.timezone(BotConfig.TIMEZONE)
    today = datetime.now(tz).date().isoformat()
    
    # Get totals
    totals = supabase_client.get_daily_totals(user['id'], today)
    
    # Format message
    msg = f"""📊 **Vandaag** ({datetime.now(tz).strftime('%d-%m-%Y')})

🍽️ **GEGETEN**
{totals['total_calories']} kcal
Protein: {totals['total_protein']:.1f}g
Carbs: {totals['total_carbs']:.1f}g
Vet: {totals['total_fat']:.1f}g

🔥 **VERBRAND**
{totals['total_burned']} kcal

📈 **NETTO**
{totals['net_calories']} kcal

🎯 **DOEL**
{user['daily_calories']} kcal
Verschil: {totals['net_calories'] - user['daily_calories']:+d} kcal

{'✅ Onder doel!' if totals['net_calories'] < user['daily_calories'] else '⚠️ Boven doel'}

📝 {totals['meal_count']} maaltijd(en) • 💪 {totals['workout_count']} workout(s)"""
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def setgoals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /setgoals command."""
    telegram_id = update.message.from_user.id
    
    # Get user
    user = supabase_client.get_or_create_user(telegram_id)
    if not user:
        await update.message.reply_text("❌ Gebruiker niet gevonden. Gebruik /start eerst.")
        return
    
    # Simple version: just calories for MVP
    msg = """🎯 **Stel je doelen in**

Stuur je dagelijkse caloriedoel in kcal.

Bijvoorbeeld: `2000`

Je kunt later ook protein, carbs en vet instellen met:
`2000 150 200 65` (cal protein carbs vet)"""
    
    await update.message.reply_text(msg, parse_mode='Markdown')
    # Note: We'll handle the actual goal setting in the message handler

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages."""
    text = update.message.text
    telegram_id = update.message.from_user.id
    
    # Get or create user
    user = supabase_client.get_or_create_user(telegram_id, update.message.from_user.username)
    if not user:
        await update.message.reply_text("❌ Er ging iets fout. Probeer /start.")
        return
    
    # Check if this is a goal setting (numbers only)
    if text.strip().replace(' ', '').isdigit():
        # Parse goals
        numbers = [int(x) for x in text.split()]
        
        if len(numbers) == 1:
            # Just calories
            supabase_client.update_user_goals(user['id'], numbers[0])
            await update.message.reply_text(f"✅ Doel ingesteld: {numbers[0]} kcal/dag")
            # Clear conversation context after goal setting
            if telegram_id in conversation_context:
                del conversation_context[telegram_id]
            return
        elif len(numbers) == 4:
            # All macros
            supabase_client.update_user_goals(user['id'], numbers[0], numbers[1], numbers[2], numbers[3])
            await update.message.reply_text(
                f"✅ Doelen ingesteld:\n"
                f"Calorieën: {numbers[0]} kcal\n"
                f"Protein: {numbers[1]}g\n"
                f"Carbs: {numbers[2]}g\n"
                f"Vet: {numbers[3]}g"
            )
            # Clear conversation context after goal setting
            if telegram_id in conversation_context:
                del conversation_context[telegram_id]
            return
    
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    # Get conversation history for this user
    if telegram_id not in conversation_context:
        conversation_context[telegram_id] = []
    
    # Add current user message to context
    conversation_context[telegram_id].append({"role": "user", "content": text})
    
    # Keep only last 10 messages (5 exchanges) to avoid token limits
    if len(conversation_context[telegram_id]) > 10:
        conversation_context[telegram_id] = conversation_context[telegram_id][-10:]
    
    # Parse with LLM including conversation history
    parsed = llm_service.parse_food_and_workouts(text, conversation_context[telegram_id][:-1])  # Exclude current message as it's added in the function
    
    # Get today's date
    tz = pytz.timezone(BotConfig.TIMEZONE)
    today = datetime.now(tz).date().isoformat()
    
    # Handle different statuses
    status = parsed.get('status', 'complete')
    
    if status == 'no_data':
        # No meal or workout detected
        response_text = (
            "🤔 Ik kon geen maaltijd of workout herkennen in je bericht.\n\n"
            "Wat wil je loggen? Bijvoorbeeld:\n"
            "• \"2 eieren met toast\"\n"
            "• \"30 minuten hardlopen\"\n"
            "• \"pasta carbonara met een salade\""
        )
        conversation_context[telegram_id].append({"role": "assistant", "content": response_text})
        await update.message.reply_text(response_text)
        return
    
    elif status == 'needs_clarification':
        # Need more info for accurate estimation
        clarification = parsed.get('clarification_question', 'Kun je wat meer details geven?')
        conversation_context[telegram_id].append({"role": "assistant", "content": clarification})
        await update.message.reply_text(f"❓ {clarification}")
        return
    
    elif status == 'complete':
        # Information is complete, save everything
        meal_count = 0
        total_meal_cal = 0
        meal_details = []
        
        for meal in parsed['meals']:
            result = supabase_client.add_meal(
                user_id=user['id'],
                description=meal['description'],
                calories=meal['calories'],
                protein=meal['protein'],
                carbs=meal['carbs'],
                fat=meal['fat'],
                date=today
            )
            if result:
                meal_count += 1
                total_meal_cal += meal['calories']
                meal_details.append(f"  • {meal['description']}: {meal['calories']} kcal")
        
        workout_count = 0
        total_burned = 0
        workout_details = []
        
        for workout in parsed['workouts']:
            result = supabase_client.add_workout(
                user_id=user['id'],
                activity=workout['description'],
                calories_burned=workout['calories_burned'],
                date=today
            )
            if result:
                workout_count += 1
                total_burned += workout['calories_burned']
                workout_details.append(f"  • {workout['description']}: {workout['calories_burned']} kcal")
        
        # Send confirmation with summary
        if meal_count > 0 or workout_count > 0:
            msg = "✅ **Opgeslagen!**\n\n"
            
            if meal_count > 0:
                msg += f"🍽️ **Maaltijden ({meal_count}x)** - {total_meal_cal} kcal\n"
                msg += "\n".join(meal_details) + "\n\n"
            
            if workout_count > 0:
                msg += f"💪 **Workouts ({workout_count}x)** - {total_burned} kcal verbrand\n"
                msg += "\n".join(workout_details) + "\n\n"
            
            # Add LLM summary if provided
            if 'summary' in parsed and parsed['summary']:
                msg += f"📝 {parsed['summary']}"
            
            conversation_context[telegram_id].append({"role": "assistant", "content": msg})
            await update.message.reply_text(msg, parse_mode='Markdown')
            
            # Clear conversation context after successful save
            conversation_context[telegram_id] = []
        else:
            response_text = "❌ Er ging iets fout bij het opslaan. Probeer het opnieuw."
            conversation_context[telegram_id].append({"role": "assistant", "content": response_text})
            await update.message.reply_text(response_text)
    else:
        # Unknown status
        response_text = "🤔 Ik begreep je bericht niet helemaal. Probeer het opnieuw of gebruik /start voor hulp."
        conversation_context[telegram_id].append({"role": "assistant", "content": response_text})
        await update.message.reply_text(response_text)

def setup_telegram_bot(bot_token: str) -> Application:
    """Setup the Telegram bot with handlers."""
    application = Application.builder().token(bot_token).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("setgoals", setgoals_command))
    
    # Message handler (should be last)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return application
