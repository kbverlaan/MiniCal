from datetime import datetime
import pytz
from app.config import BotConfig

class StatsFormatter:
    @staticmethod
    def format(daily_stats: dict, weekly_stats: dict, user_goals: dict, 
              recent_workouts: list, health_metrics: dict, recent_meals: list = None) -> str:
        """
        Gegenereert een rijke, geanalyseerde context string voor de LLM.
        Berekent percentages, verschillen en groepeert data logisch.
        """
        
        # Huidige tijd ophalen voor context
        tz = pytz.timezone(BotConfig.TIMEZONE)
        now = datetime.now(tz)
        current_hour = now.hour
        time_str = now.strftime("%H:%M")
        
        # Bepaal dagdeel voor context
        if current_hour < 12:
            time_context = "Ochtend (Focus: Opstarten)"
            is_early = True
        elif current_hour < 18:
            time_context = "Middag (Focus: Voortgang)"
            is_early = False
        else:
            time_context = "Avond (Focus: Afronden)"
            is_early = False

        # 1. DOELEN & ADHERENCE
        goals = {
            'cal': user_goals.get('daily_calories', 2000),
            'pro': user_goals.get('daily_protein', 150),
            'carbs': user_goals.get('daily_carbs', 200),
            'fat': user_goals.get('daily_fat', 65)
        }
        
        def pct(val, target):
            if not target: return 0
            return round((val / target) * 100)
            
        def diff_symbol(val):
            return f"+{val:.0f}" if val > 0 else f"{val:.0f}"

        # Vandaag analyse
        cal_pct = pct(daily_stats['total_calories'], goals['cal'])
        pro_pct = pct(daily_stats['total_protein'], goals['pro'])
        
        # Week trend analyse
        avg_cal = weekly_stats.get('avg_calories', 0)
        avg_pro = weekly_stats.get('avg_protein', 0)
        
        cal_vs_avg = daily_stats['total_calories'] - avg_cal
        pro_vs_avg = daily_stats['total_protein'] - avg_pro
        
        context = []
        
        # --- HEADER: TIJD & CONTEXT ---
        context.append(f"🕒 *TIJDSTIP: {time_str} - {time_context}*")

        # --- SECTIE 1: VANDAAG vs DOELEN ---
        context.append("📊 *VANDAAG (Status vs Doel)*")
        context.append(f"- Calorieën: {daily_stats['total_calories']} / {goals['cal']} kcal ({cal_pct}%)")
        context.append(f"  → Netto: {daily_stats['net_calories']} kcal (na {daily_stats['total_burned']} burned)")
        context.append(f"- Eiwit:     {daily_stats['total_protein']:.1f} / {goals['pro']}g ({pro_pct}%)")
        context.append(f"- Koolh:     {daily_stats['total_carbs']:.1f} / {goals['carbs']}g ({pct(daily_stats['total_carbs'], goals['carbs'])}%)")
        context.append(f"- Vet:       {daily_stats['total_fat']:.1f} / {goals['fat']}g ({pct(daily_stats['total_fat'], goals['fat'])}%)")
        
        # --- SECTIE 2: TRENDS (VANDAAG vs WEEK GEMIDDELDE) ---
        context.append("\n📈 *TRENDS (Vandaag vs Weekgemiddelde)*")
        context.append(f"- Calorieën: {diff_symbol(cal_vs_avg)} kcal t.o.v. weekgemiddelde ({avg_cal:.0f})")
        context.append(f"- Eiwit:     {diff_symbol(pro_vs_avg)}g t.o.v. weekgemiddelde ({avg_pro:.1f})")
        context.append(f"- Activiteit: {weekly_stats.get('total_workouts', 0)} workouts deze week")

        # --- SECTIE 3: MICRONUTRIËNTEN & SUPPS ---
        context.append("\n💊 *MICROS & SUPPLEMENTEN*")
        
        micros = [
            ("Omega-3 (EPA/DHA)", daily_stats.get('omega3_epa_dha', 0), weekly_stats.get('avg_omega3_epa_dha', 0), 2000, "mg"),
            ("Vitamine D", daily_stats.get('vitamin_d', 0), weekly_stats.get('avg_vitamin_d', 0), 50, "mcg"),
            ("Vitamine B12", daily_stats.get('vitamin_b12', 0), weekly_stats.get('avg_vitamin_b12', 0), 2.8, "mcg"),
            ("Vitamine C", daily_stats.get('vitamin_c', 0), weekly_stats.get('avg_vitamin_c', 0), 100, "mg"),
            ("Calcium", daily_stats.get('calcium', 0), weekly_stats.get('avg_calcium', 0), 1000, "mg"),
            ("Magnesium", daily_stats.get('magnesium', 0), weekly_stats.get('avg_magnesium', 0), 350, "mg"),
            ("Ijzer", daily_stats.get('iron', 0), weekly_stats.get('avg_iron', 0), 14, "mg"),
            ("Zink", daily_stats.get('zinc', 0), weekly_stats.get('avg_zinc', 0), 15, "mg"),
            ("Creatine", daily_stats.get('creatine', 0), weekly_stats.get('avg_creatine', 0), 5, "g")
        ]
        
        for name, current, avg, target, unit in micros:
            # Check status op basis van weekgemiddelde als dagwaarde laag is (in de ochtend)
            # Maar toon beide waarden voor context
            
            status = ""
            if current >= target * 0.8:
                status = "✅"
            elif avg >= target * 0.9: # Als weekgemiddelde goed is, is het ook prima
                status = "✅ (Week OK)"
            elif not is_early:
                status = "⚠️ Laag"

            # Format: "Vitamine D: 0 (Weekgm: 45) / 50 mcg"
            context.append(f"- {name}: {current:.0f} (Weekgem: {avg:.0f}) / {target}{unit} {status}")

        # --- SECTIE 3.5: RECENTE MAALTIJDEN ---
        if recent_meals and len(recent_meals) > 0:
            context.append("\n🍽️ *RECENTE MAALTIJDEN (Laatste 3 dagen)*")
            # Group by date
            from collections import defaultdict
            meals_by_date = defaultdict(list)
            for meal in recent_meals:
                meals_by_date[meal['date']].append(meal)
            
            # Show most recent 3 days
            for date in sorted(meals_by_date.keys(), reverse=True)[:3]:
                context.append(f"\n*{date}:*")
                for meal in meals_by_date[date][:5]:  # Max 5 meals per day
                    context.append(f"  • {meal['description']} ({meal['calories']} kcal, {meal['protein']:.0f}g eiwit)")

        # --- SECTIE 4: RECENTE WORKOUTS (CONTEXT VOOR HERSTEL) ---
        if recent_workouts:
            context.append("\n🏋️ *WORKOUT CONTEXT (Laatste 7 dagen)*")
            for w in recent_workouts[:5]:
                context.append(f"- {w.get('date')}: {w.get('activity')} ({w.get('calories_burned')} kcal)")
        else:
            context.append("\n🏋️ *WORKOUT CONTEXT*: Geen recente trainingen.")

        # --- SECTIE 5: HERSTEL METRICS (GARMIN) ---
        context.append("\n🔋 *HERSTEL STATUS (Garmin Data)*")
        
        # Sleep analysis - ONLY show data from previous night (yesterday's date)
        sleep_logs = health_metrics.get('sleep', [])
        if sleep_logs and len(sleep_logs) > 0:
            # Get yesterday's date to find the previous night's sleep
            from datetime import timedelta
            yesterday = (datetime.now(tz).date() - timedelta(days=1)).isoformat()
            
            # Find sleep entry for yesterday
            prev_night_sleep = None
            for sleep in sleep_logs:
                if sleep.get('date') == yesterday:
                    prev_night_sleep = sleep
                    break
            
            if prev_night_sleep:
                total = prev_night_sleep.get('total_hours', 0)
                deep = prev_night_sleep.get('deep_hours', 0) or 0
                light = prev_night_sleep.get('light_hours', 0) or 0
                rem = prev_night_sleep.get('rem_hours', 0) or 0
                qual = prev_night_sleep.get('quality_score', 0) or 0
                
                if qual >= 80: sleep_icon = "🟢"
                elif qual >= 60: sleep_icon = "🟠"
                else: sleep_icon = "🔴"
                
                context.append(f"- Afgelopen nacht: {total:.1f}u totaal (Score: {qual}/100 {sleep_icon})")
                context.append(f"  Stages: Diep {deep:.1f}u | Licht {light:.1f}u | REM {rem:.1f}u")
                
                # Calculate sleep trends for last 3 DAYS (not most recent 3 entries)
                # Get dates for last 3 days
                last_3_days = [(datetime.now(tz).date() - timedelta(days=i)).isoformat() for i in range(1, 4)]
                sleep_last_3_days = [s for s in sleep_logs if s.get('date') in last_3_days]
                
                if len(sleep_last_3_days) >= 2:  # At least 2 days for meaningful trend
                    recent_total = sum(s.get('total_hours', 0) for s in sleep_last_3_days) / len(sleep_last_3_days)
                    recent_deep = sum(s.get('deep_hours', 0) or 0 for s in sleep_last_3_days) / len(sleep_last_3_days)
                    recent_qual = sum(s.get('quality_score', 0) or 0 for s in sleep_last_3_days) / len(sleep_last_3_days)
                    
                    context.append(f"  Trend (laatste {len(sleep_last_3_days)} nachten): Ø {recent_total:.1f}u | Ø Diep {recent_deep:.1f}u | Ø Score {recent_qual:.0f}")
                
                # Deep sleep warning
                if deep < 1.0:
                    context.append(f"  ⚠️ Let op: Diepe slaap laag. Fysiek herstel suboptimaal.")
            else:
                context.append("- Slaap: Geen data van afgelopen nacht")
        else:
            context.append("- Slaap: Geen recente data")

        # HR analysis with HRV trend
        hr_logs = health_metrics.get('heart_rate', [])
        if hr_logs and len(hr_logs) > 0:
            last_hr = hr_logs[0]
            rhr = last_hr.get('resting_hr')
            hrv = last_hr.get('hrv_avg')
            
            # Calculate HRV trend if we have multiple days
            hrv_trend = ""
            if len(hr_logs) >= 2 and hrv:
                prev_hrv = hr_logs[1].get('hrv_avg')
                if prev_hrv:
                    hrv_diff = hrv - prev_hrv
                    if hrv_diff > 5:
                        hrv_trend = " 📈 (Stijgend - Goed herstel)"
                    elif hrv_diff < -5:
                        hrv_trend = " 📉 (Dalend - Mogelijk overtraining/stress)"
                    else:
                        hrv_trend = " ➡️ (Stabiel)"
            
            context.append(f"- Hartslag: Resting {rhr} bpm | HRV: {hrv} ms{hrv_trend}")
        else:
            context.append("- Hartslag: Geen recente data")

        return "\n".join(context)
