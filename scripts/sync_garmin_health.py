"""
Daily Garmin Health Sync
Runs every morning at 7:00 and 13:00 to sync health data:
- Sleep (total, deep, light, REM)
- Heart Rate (resting, avg, max, HRV)
- Stress (average, max, breakdown)
"""

import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.supabase_client import supabase_client
from app.services.garmin_sync import GarminSyncService

def main():
    """Sync yesterday and today's health data from Garmin."""
    user_id = 1  # TODO: Support multiple users
    
    # Initialize sync service
    sync_service = GarminSyncService(supabase_client)
    
    # Sync data (defaults to yesterday + today)
    result = sync_service.sync_health_data(user_id=user_id, verbose=True)
    
    if not result['success']:
        print(f"❌ {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from garminconnect import Garmin

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.supabase_client import supabase_client

load_dotenv()

def sync_health_data():
    """Sync yesterday's health data from Garmin to database."""
    
    print("🔗 Connecting to Garmin Connect...")
    
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    user_id = 1  # TODO: Support multiple users
    
    if not email or not password:
        print("❌ Error: GARMIN_EMAIL and GARMIN_PASSWORD must be set")
        return
    
    try:
        # Login to Garmin
        garmin = Garmin(email, password)
        garmin.login()
        print("✅ Connected to Garmin\n")
        
        # Sync both yesterday and today (today catches recent sleeps)
        dates_to_sync = [
            (datetime.now().date() - timedelta(days=1)).isoformat(),  # Yesterday
            datetime.now().date().isoformat()  # Today
        ]
        
        synced_count = 0
        
        for date_str in dates_to_sync:
            print(f"\n📅 Checking data for: {date_str}")
            date_synced = False
            date_synced = False
        
        # === SLEEP DATA ===
        print("\n😴 Checking sleep data...")
        try:
            sleep = garmin.get_sleep_data(date_str)
            if sleep and 'dailySleepDTO' in sleep:
                sleep_dto = sleep['dailySleepDTO']
                
                # Check if we have actual sleep data
                total_seconds = sleep_dto.get('sleepTimeSeconds')
                if total_seconds:
                    total_hours = total_seconds / 3600
                    deep_hours = (sleep_dto.get('deepSleepSeconds') or 0) / 3600
                    light_hours = (sleep_dto.get('lightSleepSeconds') or 0) / 3600
                    rem_hours = (sleep_dto.get('remSleepSeconds') or 0) / 3600
                    awake_hours = (sleep_dto.get('awakeSleepSeconds') or 0) / 3600
                    
                    # Get sleep score if available
                    quality_score = None
                    if 'sleepScores' in sleep_dto and sleep_dto['sleepScores']:
                        overall = sleep_dto['sleepScores'].get('overall', {})
                        if overall:
                            quality_score = overall.get('value')
                    
                    result = supabase_client.add_sleep_log(
                        user_id=user_id,
                        date=date_str,
                        total_hours=round(total_hours, 2),
                        deep_hours=round(deep_hours, 2) if deep_hours else None,
                        light_hours=round(light_hours, 2) if light_hours else None,
                        rem_hours=round(rem_hours, 2) if rem_hours else None,
                        awake_hours=round(awake_hours, 2) if awake_hours else None,
                        quality_score=quality_score,
                        source='garmin'
                    )
                    
                    if result:
                        print(f"   ✅ Sleep: {total_hours:.1f}h total (Deep: {deep_hours:.1f}h, Light: {light_hours:.1f}h, REM: {rem_hours:.1f}h)")
                        if quality_score:
                            print(f"   💯 Sleep Score: {quality_score}/100")
                        date_synced = True
                    else:
                        print("   ⚠️  Failed to save sleep data")
                else:
                    print("   ⏳ No sleep data yet (still null)")
            else:
                print("   ⏳ No sleep data available yet")
        except Exception as e:
            print(f"   ❌ Sleep sync error: {e}")
        
        # === HEART RATE DATA ===
        print("\n❤️  Checking heart rate data...")
        try:
            hr = garmin.get_heart_rates(date_str)
            if hr:
                resting_hr = hr.get('restingHeartRate')
                max_hr = hr.get('maxHeartRate')
                avg_hr = hr.get('averageHeartRate')
                min_hr = hr.get('minHeartRate')
                
                # HRV data (if available)
                hrv_avg = None
                try:
                    hrv_data = garmin.get_hrv_data(date_str)
                    if hrv_data and 'hrvSummary' in hrv_data:
                        hrv_avg = hrv_data['hrvSummary'].get('lastNightAvg')
                except:
                    pass  # HRV not available on all devices
                
                if resting_hr or avg_hr or max_hr:
                    result = supabase_client.add_heart_rate_log(
                        user_id=user_id,
                        date=date_str,
                        resting_hr=resting_hr,
                        avg_hr=avg_hr,
                        max_hr=max_hr,
                        min_hr=min_hr,
                        hrv_avg=hrv_avg
                    )
                    
                    if result:
                        print(f"   ✅ HR: Resting {resting_hr} bpm, Avg {avg_hr} bpm, Max {max_hr} bpm")
                        if hrv_avg:
                            print(f"   💓 HRV: {hrv_avg} ms")
                        date_synced = True
                    else:
                        print("   ⚠️  Failed to save heart rate data")
                else:
                    print("   ⏳ No heart rate data yet")
            else:
                print("   ⏳ No heart rate data available yet")
        except Exception as e:
            print(f"   ❌ Heart rate sync error: {e}")
        
        # === STRESS DATA ===
        print("\n😰 Checking stress data...")
        try:
            stress = garmin.get_stress_data(date_str)
            if stress:
                avg_stress = stress.get('avgStressLevel')
                max_stress = stress.get('maxStressLevel')
                
                # Breakdown of stress levels
                rest_minutes = stress.get('restStressDuration', 0) // 60 if stress.get('restStressDuration') else None
                low_minutes = stress.get('lowStressDuration', 0) // 60 if stress.get('lowStressDuration') else None
                medium_minutes = stress.get('mediumStressDuration', 0) // 60 if stress.get('mediumStressDuration') else None
                high_minutes = stress.get('highStressDuration', 0) // 60 if stress.get('highStressDuration') else None
                
                if avg_stress is not None:
                    result = supabase_client.add_stress_log(
                        user_id=user_id,
                        date=date_str,
                        avg_stress=avg_stress,
                        max_stress=max_stress,
                        rest_minutes=rest_minutes,
                        low_stress_minutes=low_minutes,
                        medium_stress_minutes=medium_minutes,
                        high_stress_minutes=high_minutes
                    )
                    
                    if result:
                        print(f"   ✅ Stress: Avg {avg_stress}/100, Max {max_stress}/100")
                        if rest_minutes:
                            print(f"   🧘 Rest: {rest_minutes} min, Low: {low_minutes} min, Med: {medium_minutes} min, High: {high_minutes} min")
                        date_synced = True
                    else:
                        print("   ⚠️  Failed to save stress data")
                else:
                    print("   ⏳ No stress data yet")
            else:
                print("   ⏳ No stress data available yet")
        except Exception as e:
            print(f"   ❌ Stress sync error: {e}")
            
            if date_synced:
                synced_count += 1
        
        print("\n" + "="*60)
        if synced_count > 0:
            print(f"✅ Garmin health sync complete! ({synced_count} dates with new data)")
        else:
            print("ℹ️  No new data available yet (check again later)")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Garmin sync failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sync_health_data()
