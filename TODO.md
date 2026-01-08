# MiniCal - Feature Roadmap

## 🔄 In Progress
- Conversation history (✅ Done)
- Intent classification improvements (✅ Done)
- Performance & Health Analyst personality (✅ Done)

## 🎯 High Priority - Next Steps

### Sleep Tracking
- [ ] Run database migration `003_sleep_tracking.sql` in Supabase
- [ ] Add sleep logging methods to `supabase_client.py`
- [ ] Update LLM parser to detect sleep entries ("8u geslapen", "7.5 hours sleep")
- [ ] Integrate Garmin API for automatic sleep sync
- [ ] Add sleep data to Q&A context (correlation with performance)

### Mindfulness & Mental Health 🧘‍♂️
- [ ] Create `mindfulness_logs` table (meditation, breathing, journaling)
- [ ] Track meditation sessions (duration, type, notes)
- [ ] Mood tracking (1-5 scale + notes: "stressed", "energetic", "calm")
- [ ] Gratitude journal entries
- [ ] Stress score tracking (from Garmin or manual)
- [ ] Parse entries: "10 min meditatie", "feeling stressed vandaag", "grateful for X"
- [ ] Correlate mental state with sleep/nutrition/performance
- [ ] Daily check-in: "Hoe voel je je vandaag?" (morning + evening)
- [ ] Streak tracking: "7 dagen achter elkaar gemediteerd 🔥"
- [ ] Integration: Headspace/Calm/Apple Health mindfulness minutes

### Workout Intelligence
- [ ] Run database migration `004_workout_intelligence.sql` in Supabase
- [ ] Add workout session + exercise set methods to `supabase_client.py`
- [ ] Build workout log parser (from text or photo)
- [ ] Support logboek upload (parse Notes format)
- [ ] Track volume per exercise (sets × reps × weight)
- [ ] PR detection ("Nieuw bench PR! 85kg 3x8 🎉")
- [ ] Progressive overload suggestions ("Vorige week 80kg → probeer 82.5kg")

### Garmin Integration
- [ ] Register Garmin Developer account
- [ ] Set up OAuth2 flow for Garmin Connect
- [ ] Implement daily sync for:
  - Sleep data (duration, quality, deep/light/REM stages)
  - Step count
  - Heart rate (resting, avg, max)
  - Workout auto-detection
  - Stress score
- [ ] Add webhook for real-time updates
- [ ] Fallback: manual sleep logging via Telegram

## 📊 Medium Priority - Nice to Have

### Trends & Visualizations
- [ ] Weekly/monthly charts (calories, protein, weight)
- [ ] Streak tracking ("7 dagen protein doel gehaald! 🔥")
- [ ] Pattern detection ("Je eet te weinig op maandag")
- [ ] Weekly PDF report met insights

### Smart Meal Planning
- [ ] Meal suggestions based on remaining macros
- [ ] Recipe database (save favorite meals)
- [ ] Quick log shortcuts (`/log chicken_rice`)
- [ ] Meal prep planning

### Photo Logging
- [ ] Upload meal photo → Gemini Vision estimates macros
- [ ] Progress photos (body tracking)
- [ ] Upload workout logboek screenshot → auto-parse

### Better UX
- [ ] Inline buttons (❌ Delete | ✏️ Edit | 📊 Stats)
- [ ] Daily checklist view (✅ Protein | ✅ Workout | ⏳ Water)
- [ ] Voice message support (transcribe → parse)
- [ ] Command shortcuts (`/stats`, `/week`, `/compare`)

## 🚀 Future / Advanced

### Recovery & Performance
- [ ] Recovery score (sleep + volume + stress + mood)
- [ ] Rest day suggestions ("5 dagen getraind, neem rust")
- [ ] HRV tracking (via Garmin/Whoop)
- [ ] Deload week detection
- [ ] Mental fatigue tracking (correlate with training volume)
- [ ] Burnout prevention alerts

### Hydration
- [ ] Water intake tracking
- [ ] Reminders ("Drink meer! Pas 1L vandaag")
- [ ] Correlation water vs energy

### Social Features
- [ ] Shared challenges met vrienden
- [ ] Leaderboards (wie haalt doelen meest consistent?)
- [ ] Coach mode (iemand anders kan je data zien)

### Other Integrations
- [ ] Apple Health / Google Fit sync
- [ ] Strava (hardlopen/fietsen)
- [ ] MyFitnessPal import
- [ ] Whoop/Oura ring support

---

## 🛠️ Technical Debt
- [ ] Add error handler to Telegram bot
- [ ] Add user authentication/multi-user support improvements
- [ ] Add data export (CSV/Excel)
- [ ] Add custom goals per day (training vs rest day)
- [ ] Add backup/restore functionality
