# MiniCal - Ultra Simpele Calorie Tracker

De simpelste calorie tracker ooit. Stuur gewoon een bericht met wat je hebt gegeten en workouts die je hebt gedaan.

## Features
- 📝 Vrije tekst input - schrijf gewoon wat je wilt
- 🤖 LLM parseert automatisch maaltijden en workouts
- ⏰ Dagelijkse check om 22:00 - "Staat alles erin?"
- 📊 Automatische samenvatting om 23:00
- 🎯 Track calorieën, protein, carbs en vet

## Setup

1. Maak een Telegram bot via @BotFather
2. Maak een Supabase project en run de SQL scripts
3. Haal een OpenRouter API key
4. Maak `.env` file:
```
TELEGRAM_API_TOKEN='your_token'
SUPABASE_URL='your_url'
SUPABASE_KEY='your_key'
OPENROUTER_API_KEY='your_key'
```

## Lokaal draaien
```bash
pip install -r requirements.txt
python main.py
```

## Railway deployment
Push naar GitHub en connect met Railway. Voeg de env variabelen toe.

Voor de daily summaries, voeg een cronjob toe in Railway:
- 22:00: `python scripts/daily_check.py`
- 23:00: `python scripts/daily_summary.py`
