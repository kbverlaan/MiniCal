# MiniCal - Ultra Simpele Calorie Tracker

De simpelste calorie tracker ooit. Stuur gewoon een bericht met wat je hebt gegeten en workouts die je hebt gedaan.

## Features
- 📝 Vrije tekst input - schrijf gewoon wat je wilt
- 🤖 LLM parseert automatisch maaltijden en workouts
- 💊 Track vitamines en supplementen (automatisch uit voedsel + supplementen)
- ❓ Stel vragen en krijg antwoorden met je weekgemiddeldes en dagstats
- ⏰ Dagelijkse check om 22:00 - "Staat alles erin?"
- 📊 Automatische samenvatting om 23:00
- 🎯 Track calorieën, protein, carbs en vet

## Voorbeelden

**Maaltijden loggen:**
- "2 eieren met toast en een banaan"
- "bulgogi rijst met sla"
- "pizza met cola"

**Workouts loggen:**
- "uurtje hardlopen gedaan"
- "45 min krachttraining"
- "30 min fietsen"

**Supplementen loggen:**
- "vitamine D3 1000mcg genomen"
- "omega 3 visolie en magnesium"
- "creatine 5g"

**Vragen stellen:**
- "Hoe gaat het deze week?"
- "Haal ik genoeg protein?"
- "Hoeveel heb ik deze week gesport?"

## Setup

1. Maak een Telegram bot via @BotFather
2. Maak een Supabase project en run de SQL scripts
   - `database_schema.sql` (basis structuur)
   - `database_schema_supplements.sql` (voor vitamine tracking)
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

Voor de daily summaries en Garmin sync, voeg deze cronjobs toe in Railway:
- **07:00 & 13:00**: `python scripts/sync_garmin_health.py` (auto-sync sleep, HR, stress)
- **22:00**: `python scripts/daily_check.py` (reminder: "Staat alles erin?")
- **23:00**: `python scripts/daily_summary.py` (daily recap)

Cron syntax:
```
0 7,13 * * * python scripts/sync_garmin_health.py
0 22 * * * python scripts/daily_check.py
0 23 * * * python scripts/daily_summary.py
```

### Garmin Integration
Voeg deze variabelen toe aan `.env`:
```
GARMIN_EMAIL='your_garmin_email@example.com'
GARMIN_PASSWORD='your_garmin_password'
```

De sync draait 2x per dag en checkt voor nieuwe data:
- 😴 Sleep (total, deep, light, REM, quality score)
- ❤️ Heart Rate (resting, avg, max, HRV)
- 😰 Stress levels (avg, max, breakdown)

Data wordt automatisch opgeslagen in de database en is beschikbaar in Q&A!

### Bot Commands
- `/start` - Welkomstbericht en uitleg
- `/help` - Overzicht van alle features
- `/sync` - Handmatig Garmin data syncen

