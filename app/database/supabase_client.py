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
                protein: float, carbs: float, fat: float, date: str = None) -> dict | None:
        """Add a meal entry."""
        try:
            meal_data = {
                'user_id': user_id,
                'description': description,
                'calories': calories,
                'protein': protein,
                'carbs': carbs,
                'fat': fat
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
        
        return {
            'total_calories': total_calories,
            'total_protein': total_protein,
            'total_carbs': total_carbs,
            'total_fat': total_fat,
            'total_burned': total_burned,
            'net_calories': total_calories - total_burned,
            'meal_count': len(meals),
            'workout_count': len(workouts)
        }

    def get_all_users(self) -> list[dict]:
        """Get all users for batch operations."""
        try:
            response = self.client.table('users').select('*').execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching users: {e}")
            return []

# Maak een globale instance aan die in de rest van de app kan worden geïmporteerd
supabase_client = SupabaseClient()
