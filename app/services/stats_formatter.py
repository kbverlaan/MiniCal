from datetime import datetime
import pytz
from app.config import BotConfig

class StatsFormatter:
    @staticmethod
    def format(daily_stats: dict, weekly_stats: dict, user_goals: dict, 
              recent_workouts: list, health_metrics: dict) -> str:
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
        context.append(f"🕒 **TIJDSTIP: {time_str} - {time_context}**")

        # --- SECTIE 1: VANDAAG vs DOELEN ---
        context.append("📊 **VANDAAG (Status vs Doel)**")
        context.append(f"- Calorieën: {daily_stats['total_calories']} / {goals['cal']} kcal ({cal_pct}%)")
        context.append(f"  → Netto: {daily_stats['net_calories']} kcal (na {daily_stats['total_burned']} burned)")
        context.append(f"- Eiwit:     {daily_stats['total_protein']:.1f} / {goals['pro']}g ({pro_pct}%)")
        context.append(f"- Koolh:     {daily_stats['total_carbs']:.1f} / {goals['carbs']}g ({pct(daily_stats['total_carbs'], goals['carbs'])}%)")
        context.append(f"- Vet:       {daily_stats['total_fat']:.1f} / {goals['fat']}g ({pct(daily_stats['total_fat'], goals['fat'])}%)")
        
        # --- SECTIE 2: TRENDS (VANDAAG vs WEEK GEMIDDELDE) ---
        context.append("\n📈 **TRENDS (Vandaag vs Weekgemiddelde)**")
        context.append(f"- Calorieën: {diff_symbol(cal_vs_avg)} kcal t.o.v. weekgemiddelde ({avg_cal:.0f})")
        context.append(f"- Eiwit:     {diff_symbol(pro_vs_avg)}g t.o.v. weekgemiddelde ({avg_pro:.1f})")
        context.append(f"- Activiteit: {weekly_stats.get('total_workouts', 0)} workouts deze week")
        
        # --- SECTIE 2.5: DAGELIJKSE ACTIVITEIT (Uitbreiding) ---
        activity_logs = health_metrics.get('daily_activity', [])
        if activity_logs:
            last_activity = activity_logs[0]
            steps = last_activity.get('steps', 0)
            goal = last_activity.get('step_goal', 0) or 1
            step_pct = (steps / goal) * 100
            
            context.append(f"- Stappen: {steps} / {goal} ({step_pct:.0f}%)")
            
            mod_min = last_activity.get('moderate_intensity_minutes', 0) or 0
            vig_min = last_activity.get('vigorous_intensity_minutes', 0) or 0
            intensity_total = mod_min + (vig_min * 2)
            if intensity_total > 0:
                context.append(f"- Intensiteit: {intensity_total} minuten (Mod: {mod_min}, Vig: {vig_min})")

        # --- SECTIE 3: MICRONUTRIËNTEN & SUPPS ---
        context.append("\n💊 **MICROS & SUPPLEMENTEN**")
        
        micros = [
            ("Omega-3 (EPA/DHA)", daily_stats.get('omega3_epa_dha', 0), weekly_stats.get('avg_omega3_epa_dha', 0), 2000, "mg"),
            ("Vitamine D", daily_stats.get('vitamin_d', 0), weekly_stats.get('avg_vitamin_d', 0), 50, "mcg"),
            ("Vitamine C", daily_stats.get('vitamin_c', 0), weekly_stats.get('avg_vitamin_c', 0), 100, "mg"),
            ("Magnesium", daily_stats.get('magnesium', 0), weekly_stats.get('avg_magnesium', 0), 350, "mg"),
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

            # Format: "Vitamine D: 0 (Weekgem: 45) / 50 mcg"
            context.append(f"- {name}: {current:.0f} (Week: {avg:.0f}) / {target}{unit} {status}")

        # --- SECTIE 4: RECENTE WORKOUTS (CONTEXT VOOR HERSTEL) ---
        if recent_workouts:
            context.append("\n🏋️ **WORKOUT CONTEXT (Laatste 7 dagen)**")
            for w in recent_workouts[:5]:
                context.append(f"- {w.get('date')}: {w.get('activity')} ({w.get('calories_burned')} kcal)")
        else:
            context.append("\n🏋️ **WORKOUT CONTEXT**: Geen recente trainingen.")

        # --- SECTIE 5: HERSTEL METRICS (GARMIN) ---
        context.append("\n🔋 **HERSTEL STATUS (Garmin Data)**")
        
        # Sleep analysis
        sleep_logs = health_metrics.get('sleep', [])
        if sleep_logs:
            last_sleep = sleep_logs[0] # Most recent
            qual = last_sleep.get('quality_score', 0) or 0
            if qual >= 80: sleep_icon = "🟢"
            elif qual >= 60: sleep_icon = "🟠"
            else: sleep_icon = "🔴"
            
            context.append(f"- Laatste slaap: {last_sleep.get('total_hours', 0):.1f}u (Score: {qual}/100 {sleep_icon})")
            
            # Deep sleep warning
            if last_sleep.get('deep_hours', 0) < 1.0:
                context.append(f"  ⚠️ Let op: Diepe slaap is laag ({last_sleep.get('deep_hours'):.1f}u). Fysiek herstel kan minder zijn.")
        else:
            context.append("- Slaap: Geen recente data")

        # Stress analysis
        stress_logs = health_metrics.get('stress', [])
        if stress_logs:
            last_stress = stress_logs[0]
            avg_stress = last_stress.get('avg_stress', 0)
            if avg_stress < 25: stress_msg = "Uitstekend (Laag)"
            elif avg_stress < 50: stress_msg = "Normaal (Gemiddeld)"
            else: stress_msg = "Hoog - Let op herstel!"
            context.append(f"- Stressniveau: {avg_stress}/100 ({stress_msg})")

        # Body Battery analysis
        bb_logs = health_metrics.get('body_battery', [])
        if bb_logs:
            last_bb = bb_logs[0]
            high = last_bb.get('highest')
            low = last_bb.get('lowest')
            charged = last_bb.get('charged')
            drained = last_bb.get('drained')
            
            bb_msg = f"- Body Battery: High {high} / Low {low}"
            if charged is not None and drained is not None:
                net_bb = charged - drained
                symbol = "+" if net_bb > 0 else ""
                bb_msg += f" (Netto: {symbol}{net_bb})"
            context.append(bb_msg)

        # HR analysis
        hr_logs = health_metrics.get('heart_rate', [])
        if hr_logs:
            last_hr = hr_logs[0]
            context.append(f"- Hartslag: Resting {last_hr.get('resting_hr')} bpm, HRV {last_hr.get('hrv_avg')} ms")

        return "\n".join(context)
