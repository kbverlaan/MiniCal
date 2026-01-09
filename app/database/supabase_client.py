import os
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

class SupabaseClient:
    def __init__(self):
        load_dotenv()
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase URL and Key must be set in the environment variables.")
        self.client: Client = create_client(url, key)

    def test_connection(self) -> bool:
        """Tests the connection to Supabase."""
        try:
            self.client.table('users').select('id', head=True).limit(1).execute()
            return True
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")
            return False

    # === USERS ===
    
    def get_or_create_user(self, telegram_id: int, username: str = None) -> dict | None:
        """Get existing user or create new one."""
        try:
            # Check if user exists
            response = self.client.table('users') \
                .select('*') \
                .eq('telegram_id', telegram_id) \
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            
            # Create new user with defaults
            response = self.client.table('users').insert({
                'telegram_id': telegram_id,
                'username': username,
                'daily_calories': 2000,
                'daily_protein': 150,
                'daily_carbs': 200,
                'daily_fat': 65
            }).execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error in get_or_create_user: {e}")
            return None

    def update_user_goals(self, user_id: int, daily_calories: int, daily_protein: int = None, 
                         daily_carbs: int = None, daily_fat: int = None) -> dict | None:
        """Update user's daily goals."""
        try:
            update_data = {'daily_calories': daily_calories}
            if daily_protein is not None:
                update_data['daily_protein'] = daily_protein
            if daily_carbs is not None:
                update_data['daily_carbs'] = daily_carbs
            if daily_fat is not None:
                update_data['daily_fat'] = daily_fat
                
            response = self.client.table('users') \
                .update(update_data) \
                .eq('id', user_id) \
                .execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error updating user goals: {e}")
            return None

    # === MEALS ===
    
    def add_meal(self, user_id: int, description: str, calories: int, 
                protein: float, carbs: float, fat: float, date: str = None,
                fiber: float = 0, sugar: float = 0, saturated_fat: float = 0,
                vitamin_d: float = 0, vitamin_c: float = 0, vitamin_b12: float = 0,
                omega3_ala: float = 0, omega3_epa_dha: float = 0, magnesium: float = 0, calcium: float = 0,
                iron: float = 0, zinc: float = 0, creatine: float = 0) -> dict | None:
        """Add a meal entry with macros and micronutrients."""
        try:
            meal_data = {
                'user_id': user_id,
                'description': description,
                'calories': calories,
                'protein': protein,
                'carbs': carbs,
                'fat': fat,
                'fiber': fiber,
                'sugar': sugar,
                'saturated_fat': saturated_fat,
                'vitamin_d': vitamin_d,
                'vitamin_c': vitamin_c,
                'vitamin_b12': vitamin_b12,
                'omega3_ala': omega3_ala,
                'omega3_epa_dha': omega3_epa_dha,
                'magnesium': magnesium,
                'calcium': calcium,
                'iron': iron,
                'zinc': zinc,
                'creatine': creatine
            }
            if date:
                meal_data['date'] = date
            
            response = self.client.table('meals').insert(meal_data).execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error adding meal: {e}")
            return None

    def get_meals_for_date(self, user_id: int, date: str) -> list[dict]:
        """Get all meals for a specific date."""
        try:
            response = self.client.table('meals') \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('date', date) \
                .order('created_at', desc=False) \
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching meals: {e}")
            return []

    # === WORKOUTS ===
    
    def add_workout(self, user_id: int, activity: str, calories_burned: int, 
                   date: str = None) -> dict | None:
        """Add a workout entry."""
        try:
            workout_data = {
                'user_id': user_id,
                'activity': activity,
                'calories_burned': calories_burned
            }
            if date:
                workout_data['date'] = date
            
            response = self.client.table('workouts').insert(workout_data).execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error adding workout: {e}")
            return None

    def get_workouts_for_date(self, user_id: int, date: str) -> list[dict]:
        """Get all workouts for a specific date."""
        try:
            response = self.client.table('workouts') \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('date', date) \
                .order('created_at', desc=False) \
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching workouts: {e}")
            return []

    def get_workouts_for_range(self, user_id: int, start_date: str, end_date: str) -> list[dict]:
        """Get all workouts for a specific date range."""
        try:
            response = self.client.table('workouts') \
                .select('*') \
                .eq('user_id', user_id) \
                .gte('date', start_date) \
                .lte('date', end_date) \
                .order('date', desc=True) \
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching workouts for range: {e}")
            return []

    # === SUMMARY CALCULATIONS ===
    
    def get_daily_totals(self, user_id: int, date: str) -> dict:
        """Calculate totals for a specific date."""
        meals = self.get_meals_for_date(user_id, date)
        workouts = self.get_workouts_for_date(user_id, date)
        
        total_calories = sum(m['calories'] for m in meals)
        total_protein = sum(m['protein'] for m in meals)
        total_carbs = sum(m['carbs'] for m in meals)
        total_fat = sum(m['fat'] for m in meals)
        total_burned = sum(w['calories_burned'] for w in workouts)
        
        # Sum basic nutrients
        total_fiber = sum(m.get('fiber', 0) or 0 for m in meals)
        total_sugar = sum(m.get('sugar', 0) or 0 for m in meals)
        total_saturated_fat = sum(m.get('saturated_fat', 0) or 0 for m in meals)
        
        # Sum vitamins/minerals
        total_vitamin_d = sum(m.get('vitamin_d', 0) or 0 for m in meals)
        total_vitamin_c = sum(m.get('vitamin_c', 0) or 0 for m in meals)
        total_vitamin_b12 = sum(m.get('vitamin_b12', 0) or 0 for m in meals)
        total_omega3_ala = sum(m.get('omega3_ala', 0) or 0 for m in meals)
        total_omega3_epa_dha = sum(m.get('omega3_epa_dha', 0) or 0 for m in meals)
        total_omega3 = total_omega3_ala + total_omega3_epa_dha
        total_magnesium = sum(m.get('magnesium', 0) or 0 for m in meals)
        total_calcium = sum(m.get('calcium', 0) or 0 for m in meals)
        total_iron = sum(m.get('iron', 0) or 0 for m in meals)
        total_zinc = sum(m.get('zinc', 0) or 0 for m in meals)
        total_creatine = sum(m.get('creatine', 0) or 0 for m in meals)
        
        return {
            'total_calories': total_calories,
            'total_protein': total_protein,
            'total_carbs': total_carbs,
            'total_fat': total_fat,
            'fiber': total_fiber,
            'sugar': total_sugar,
            'saturated_fat': total_saturated_fat,
            'total_burned': total_burned,
            'net_calories': total_calories - total_burned,
            'meal_count': len(meals),
            'workout_count': len(workouts),
            'vitamin_d': total_vitamin_d,
            'vitamin_c': total_vitamin_c,
            'vitamin_b12': total_vitamin_b12,
            'omega3_ala': total_omega3_ala,
            'omega3_epa_dha': total_omega3_epa_dha,
            'omega3': total_omega3,
            'magnesium': total_magnesium,
            'calcium': total_calcium,
            'iron': total_iron,
            'zinc': total_zinc,
            'creatine': total_creatine
        }

    def get_all_users(self) -> list[dict]:
        """Get all users for batch operations."""
        try:
            response = self.client.table('users').select('*').execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching users: {e}")
            return []

    # === STATS & ANALYTICS ===
    
    def get_weekly_averages(self, user_id: int, start_date: str, end_date: str) -> dict:
        """Calculate weekly averages for all trackables."""
        try:
            # Get all meals for the week
            meals_response = self.client.table('meals') \
                .select('*') \
                .eq('user_id', user_id) \
                .gte('date', start_date) \
                .lte('date', end_date) \
                .execute()
            
            meals = meals_response.data if meals_response.data else []
            
            # Get all workouts for the week
            workouts_response = self.client.table('workouts') \
                .select('*') \
                .eq('user_id', user_id) \
                .gte('date', start_date) \
                .lte('date', end_date) \
                .execute()
            
            workouts = workouts_response.data if workouts_response.data else []
            
            # Calculate days with data
            from datetime import datetime, timedelta
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            days_in_range = (end - start).days + 1
            
            # Calculate totals - macros
            total_calories = sum(m['calories'] for m in meals)
            total_protein = sum(m['protein'] for m in meals)
            total_carbs = sum(m['carbs'] for m in meals)
            total_fat = sum(m['fat'] for m in meals)
            total_burned = sum(w['calories_burned'] for w in workouts)
            
            # Calculate totals - basic nutrients
            total_fiber = sum(m.get('fiber', 0) or 0 for m in meals)
            total_sugar = sum(m.get('sugar', 0) or 0 for m in meals)
            total_saturated_fat = sum(m.get('saturated_fat', 0) or 0 for m in meals)
            
            # Calculate totals - vitamins/minerals
            total_vitamin_d = sum(m.get('vitamin_d', 0) or 0 for m in meals)
            total_vitamin_c = sum(m.get('vitamin_c', 0) or 0 for m in meals)
            total_vitamin_b12 = sum(m.get('vitamin_b12', 0) or 0 for m in meals)
            total_omega3_ala = sum(m.get('omega3_ala', 0) or 0 for m in meals)
            total_omega3_epa_dha = sum(m.get('omega3_epa_dha', 0) or 0 for m in meals)
            total_omega3 = total_omega3_ala + total_omega3_epa_dha
            total_magnesium = sum(m.get('magnesium', 0) or 0 for m in meals)
            total_calcium = sum(m.get('calcium', 0) or 0 for m in meals)
            total_iron = sum(m.get('iron', 0) or 0 for m in meals)
            total_zinc = sum(m.get('zinc', 0) or 0 for m in meals)
            total_creatine = sum(m.get('creatine', 0) or 0 for m in meals)
            
            # Calculate averages
            avg_calories = total_calories / days_in_range if days_in_range > 0 else 0
            avg_protein = total_protein / days_in_range if days_in_range > 0 else 0
            avg_carbs = total_carbs / days_in_range if days_in_range > 0 else 0
            avg_fat = total_fat / days_in_range if days_in_range > 0 else 0
            avg_burned = total_burned / days_in_range if days_in_range > 0 else 0
            
            avg_fiber = total_fiber / days_in_range if days_in_range > 0 else 0
            avg_sugar = total_sugar / days_in_range if days_in_range > 0 else 0
            avg_saturated_fat = total_saturated_fat / days_in_range if days_in_range > 0 else 0
            
            avg_vitamin_d = total_vitamin_d / days_in_range if days_in_range > 0 else 0
            avg_vitamin_c = total_vitamin_c / days_in_range if days_in_range > 0 else 0
            avg_vitamin_b12 = total_vitamin_b12 / days_in_range if days_in_range > 0 else 0
            avg_omega3_ala = total_omega3_ala / days_in_range if days_in_range > 0 else 0
            avg_omega3_epa_dha = total_omega3_epa_dha / days_in_range if days_in_range > 0 else 0
            avg_omega3 = total_omega3 / days_in_range if days_in_range > 0 else 0
            avg_magnesium = total_magnesium / days_in_range if days_in_range > 0 else 0
            avg_calcium = total_calcium / days_in_range if days_in_range > 0 else 0
            avg_iron = total_iron / days_in_range if days_in_range > 0 else 0
            avg_zinc = total_zinc / days_in_range if days_in_range > 0 else 0
            avg_creatine = total_creatine / days_in_range if days_in_range > 0 else 0
            
            return {
                'days_in_range': days_in_range,
                'avg_calories': round(avg_calories, 1),
                'avg_protein': round(avg_protein, 1),
                'avg_carbs': round(avg_carbs, 1),
                'avg_fat': round(avg_fat, 1),
                'avg_fiber': round(avg_fiber, 1),
                'avg_sugar': round(avg_sugar, 1),
                'avg_saturated_fat': round(avg_saturated_fat, 1),
                'avg_burned': round(avg_burned, 1),
                'avg_net_calories': round(avg_calories - avg_burned, 1),
                'total_meals': len(meals),
                'total_workouts': len(workouts),
                'avg_vitamin_d': round(avg_vitamin_d, 1),
                'avg_vitamin_c': round(avg_vitamin_c, 1),
                'avg_vitamin_b12': round(avg_vitamin_b12, 2),
                'avg_omega3_ala': round(avg_omega3_ala, 1),
                'avg_omega3_epa_dha': round(avg_omega3_epa_dha, 1),
                'avg_omega3': round(avg_omega3, 1),
                'avg_magnesium': round(avg_magnesium, 1),
                'avg_calcium': round(avg_calcium, 1),
                'avg_iron': round(avg_iron, 1),
                'avg_zinc': round(avg_zinc, 1),
                'avg_creatine': round(avg_creatine, 1)
            }
        except Exception as e:
            print(f"Error calculating weekly averages: {e}")
            return {}

    # === HEALTH METRICS (Sleep, HR, Stress) ===
    
    def add_sleep_log(self, user_id: int, date: str, total_hours: float, 
                     deep_hours: float = None, light_hours: float = None,
                     rem_hours: float = None, awake_hours: float = None,
                     quality_score: int = None, subjective_quality: int = None,
                     source: str = 'manual', notes: str = None) -> dict | None:
        """Add or update sleep log."""
        try:
            data = {
                'user_id': user_id,
                'date': date,
                'total_hours': total_hours,
                'deep_hours': deep_hours,
                'light_hours': light_hours,
                'rem_hours': rem_hours,
                'awake_hours': awake_hours,
                'quality_score': quality_score,
                'subjective_quality': subjective_quality,
                'source': source,
                'notes': notes
            }
            
            response = self.client.table('sleep').upsert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error adding sleep log: {e}")
            return None
    
    def add_heart_rate_log(self, user_id: int, date: str, resting_hr: int = None,
                          avg_hr: int = None, max_hr: int = None, min_hr: int = None,
                          hrv_avg: int = None, source: str = 'garmin') -> dict | None:
        """Add or update heart rate log."""
        try:
            data = {
                'user_id': user_id,
                'date': date,
                'resting_hr': resting_hr,
                'avg_hr': avg_hr,
                'max_hr': max_hr,
                'min_hr': min_hr,
                'hrv_avg': hrv_avg,
                'source': source
            }
            
            response = self.client.table('heart_rate').upsert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error adding heart rate log: {e}")
            return None
    
    def add_stress_log(self, user_id: int, date: str, avg_stress: int = None,
                      max_stress: int = None, rest_minutes: int = None,
                      activity_minutes: int = None, low_stress_minutes: int = None,
                      medium_stress_minutes: int = None, high_stress_minutes: int = None,
                      source: str = 'garmin', notes: str = None) -> dict | None:
        """Add or update stress log."""
        try:
            data = {
                'user_id': user_id,
                'date': date,
                'avg_stress': avg_stress,
                'max_stress': max_stress,
                'rest_minutes': rest_minutes,
                'activity_minutes': activity_minutes,
                'low_stress_minutes': low_stress_minutes,
                'medium_stress_minutes': medium_stress_minutes,
                'high_stress_minutes': high_stress_minutes,
                'source': source,
                'notes': notes
            }
            
            response = self.client.table('stress').upsert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error adding stress log: {e}")
            return None

    def add_body_battery_log(self, user_id: int, date: str, highest: int = None,
                            lowest: int = None, charged: int = None, drained: int = None) -> dict | None:
        """Add or update body battery log."""
        try:
            data = {
                'user_id': user_id,
                'date': date,
                'highest': highest,
                'lowest': lowest,
                'charged': charged,
                'drained': drained
            }
            response = self.client.table('body_battery').upsert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error adding body battery log: {e}")
            return None

    def add_daily_activity_log(self, user_id: int, date: str, steps: int = None,
                              step_goal: int = None, floors_climbed: int = None,
                              distance_meters: float = None, moderate_intensity_minutes: int = None,
                              vigorous_intensity_minutes: int = None, intensity_minutes_goal: int = None) -> dict | None:
        """Add or update daily activity log."""
        try:
            data = {
                'user_id': user_id,
                'date': date,
                'steps': steps,
                'step_goal': step_goal,
                'floors_climbed': floors_climbed,
                'distance_meters': distance_meters,
                'moderate_intensity_minutes': moderate_intensity_minutes,
                'vigorous_intensity_minutes': vigorous_intensity_minutes,
                'intensity_minutes_goal': intensity_minutes_goal
            }
            response = self.client.table('daily_activity').upsert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error adding daily activity log: {e}")
            return None

    def get_health_metrics(self, user_id: int, start_date: str, end_date: str) -> dict:
        """Get all health data for date range."""
        try:
            sleep = self.client.table('sleep') \
                .select('*') \
                .eq('user_id', user_id) \
                .gte('date', start_date) \
                .lte('date', end_date) \
                .order('date', desc=True) \
                .execute()
            
            hr = self.client.table('heart_rate') \
                .select('*') \
                .eq('user_id', user_id) \
                .gte('date', start_date) \
                .lte('date', end_date) \
                .order('date', desc=True) \
                .execute()
            
            stress = self.client.table('stress') \
                .select('*') \
                .eq('user_id', user_id) \
                .gte('date', start_date) \
                .lte('date', end_date) \
                .order('date', desc=True) \
                .execute()

            body_battery = self.client.table('body_battery') \
                .select('*') \
                .eq('user_id', user_id) \
                .gte('date', start_date) \
                .lte('date', end_date) \
                .order('date', desc=True) \
                .execute()

            activity = self.client.table('daily_activity') \
                .select('*') \
                .eq('user_id', user_id) \
                .gte('date', start_date) \
                .lte('date', end_date) \
                .order('date', desc=True) \
                .execute()
            
            return {
                'sleep': sleep.data if sleep.data else [],
                'heart_rate': hr.data if hr.data else [],
                'stress': stress.data if stress.data else [],
                'body_battery': body_battery.data if body_battery.data else [],
                'daily_activity': activity.data if activity.data else []
            }
        except Exception as e:
            print(f"Error getting health metrics: {e}")
            return {'sleep': [], 'heart_rate': [], 'stress': [], 'body_battery': [], 'daily_activity': []}
    
    def get_recovery_score(self, user_id: int, date: str) -> dict | None:
        """Get recovery score for a specific date."""
        try:
            response = self.client.from_('recovery_scores') \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('date', date) \
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting recovery score: {e}")
            return None

# Maak een globale instance aan die in de rest van de app kan worden geïmporteerd
supabase_client = SupabaseClient()
