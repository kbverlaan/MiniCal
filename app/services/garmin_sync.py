"""
Garmin Health Sync Service
Shared sync logic for both cron job and Telegram command
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from garminconnect import Garmin

load_dotenv()

class GarminSyncService:
    """Service for syncing Garmin health data."""
    
    def __init__(self, supabase_client):
        self.supabase_client = supabase_client
        self.email = os.getenv("GARMIN_EMAIL")
        self.password = os.getenv("GARMIN_PASSWORD")
    
    def sync_health_data(self, user_id: int, dates_to_sync: list[str] = None, verbose: bool = True) -> dict:
        """
        Sync health data from Garmin for specified dates.
        
        Args:
            user_id: Database user ID
            dates_to_sync: List of date strings (YYYY-MM-DD). If None, syncs yesterday + today
            verbose: Whether to print detailed output
        
        Returns:
            Dict with sync results: {
                'success': bool,
                'synced_data': list of synced items,
                'error': str (if failed)
            }
        """
        if not self.email or not self.password:
            return {
                'success': False,
                'synced_data': [],
                'error': 'Garmin credentials not configured'
            }
        
        # Default to yesterday + today
        if dates_to_sync is None:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            dates_to_sync = [yesterday.isoformat(), today.isoformat()]
        
        if verbose:
            print("🔗 Connecting to Garmin Connect...")
        
        try:
            # Login to Garmin
            garmin = Garmin(self.email, self.password)
            garmin.login()
            
            if verbose:
                print("✅ Connected to Garmin\n")
            
            synced_data = []
            
            for date_str in dates_to_sync:
                if verbose:
                    print(f"📅 Checking data for: {date_str}")
                
                # Sync Sleep
                sleep_synced = self._sync_sleep(garmin, user_id, date_str, verbose)
                if sleep_synced:
                    synced_data.append(f"😴 Sleep ({date_str})")
                
                # Sync Heart Rate
                hr_synced = self._sync_heart_rate(garmin, user_id, date_str, verbose)
                if hr_synced:
                    synced_data.append(f"❤️ Heart Rate ({date_str})")
                
                # Sync Stress
                stress_synced = self._sync_stress(garmin, user_id, date_str, verbose)
                if stress_synced:
                    synced_data.append(f"😰 Stress ({date_str})")
            
            if verbose:
                print("\n" + "="*60)
                if synced_data:
                    print(f"✅ Garmin health sync complete! ({len(synced_data)} items)")
                else:
                    print("ℹ️  No new data available yet (check again later)")
                print("="*60)
            
            return {
                'success': True,
                'synced_data': synced_data,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Garmin sync failed: {str(e)}"
            if verbose:
                print(f"\n❌ {error_msg}")
            return {
                'success': False,
                'synced_data': [],
                'error': error_msg
            }
    
    def _sync_sleep(self, garmin, user_id: int, date_str: str, verbose: bool) -> bool:
        """Sync sleep data for a specific date. Returns True if data was synced."""
        try:
            if verbose:
                print("\n😴 Checking sleep data...")
            
            sleep = garmin.get_sleep_data(date_str)
            if sleep and 'dailySleepDTO' in sleep:
                sleep_dto = sleep['dailySleepDTO']
                total_seconds = sleep_dto.get('sleepTimeSeconds')
                
                if total_seconds:
                    total_hours = total_seconds / 3600
                    deep_hours = (sleep_dto.get('deepSleepSeconds') or 0) / 3600
                    light_hours = (sleep_dto.get('lightSleepSeconds') or 0) / 3600
                    rem_hours = (sleep_dto.get('remSleepSeconds') or 0) / 3600
                    awake_hours = (sleep_dto.get('awakeSleepSeconds') or 0) / 3600
                    
                    quality_score = None
                    if 'sleepScores' in sleep_dto and sleep_dto['sleepScores']:
                        overall = sleep_dto['sleepScores'].get('overall', {})
                        if overall:
                            quality_score = overall.get('value')
                    
                    result = self.supabase_client.add_sleep_log(
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
                        if verbose:
                            print(f"   ✅ Sleep: {total_hours:.1f}h total (Deep: {deep_hours:.1f}h, Light: {light_hours:.1f}h, REM: {rem_hours:.1f}h)")
                            if quality_score:
                                print(f"   💯 Sleep Score: {quality_score}/100")
                        return True
                else:
                    if verbose:
                        print("   ⏳ No sleep data yet")
            return False
        except Exception as e:
            if verbose:
                print(f"   ❌ Sleep sync error: {e}")
            return False
    
    def _sync_heart_rate(self, garmin, user_id: int, date_str: str, verbose: bool) -> bool:
        """Sync heart rate data for a specific date. Returns True if data was synced."""
        try:
            if verbose:
                print("\n❤️  Checking heart rate data...")
            
            hr = garmin.get_heart_rates(date_str)
            if hr:
                resting_hr = hr.get('restingHeartRate')
                max_hr = hr.get('maxHeartRate')
                avg_hr = hr.get('averageHeartRate')
                min_hr = hr.get('minHeartRate')
                
                hrv_avg = None
                try:
                    hrv_data = garmin.get_hrv_data(date_str)
                    if hrv_data and 'hrvSummary' in hrv_data:
                        hrv_avg = hrv_data['hrvSummary'].get('lastNightAvg')
                except:
                    pass
                
                if resting_hr or avg_hr or max_hr:
                    result = self.supabase_client.add_heart_rate_log(
                        user_id=user_id,
                        date=date_str,
                        resting_hr=resting_hr,
                        avg_hr=avg_hr,
                        max_hr=max_hr,
                        min_hr=min_hr,
                        hrv_avg=hrv_avg
                    )
                    
                    if result:
                        if verbose:
                            print(f"   ✅ HR: Resting {resting_hr} bpm, Avg {avg_hr} bpm, Max {max_hr} bpm")
                            if hrv_avg:
                                print(f"   💓 HRV: {hrv_avg} ms")
                        return True
                else:
                    if verbose:
                        print("   ⏳ No heart rate data yet")
            return False
        except Exception as e:
            if verbose:
                print(f"   ❌ Heart rate sync error: {e}")
            return False
    
    def _sync_stress(self, garmin, user_id: int, date_str: str, verbose: bool) -> bool:
        """Sync stress data for a specific date. Returns True if data was synced."""
        try:
            if verbose:
                print("\n😰 Checking stress data...")
            
            stress = garmin.get_stress_data(date_str)
            if stress:
                avg_stress = stress.get('avgStressLevel')
                max_stress = stress.get('maxStressLevel')
                
                rest_minutes = stress.get('restStressDuration', 0) // 60 if stress.get('restStressDuration') else None
                low_minutes = stress.get('lowStressDuration', 0) // 60 if stress.get('lowStressDuration') else None
                medium_minutes = stress.get('mediumStressDuration', 0) // 60 if stress.get('mediumStressDuration') else None
                high_minutes = stress.get('highStressDuration', 0) // 60 if stress.get('highStressDuration') else None
                
                if avg_stress is not None:
                    result = self.supabase_client.add_stress_log(
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
                        if verbose:
                            print(f"   ✅ Stress: Avg {avg_stress}/100, Max {max_stress}/100")
                            if rest_minutes:
                                print(f"   🧘 Rest: {rest_minutes} min, Low: {low_minutes} min, Med: {medium_minutes} min, High: {high_minutes} min")
                        return True
                else:
                    if verbose:
                        print("   ⏳ No stress data yet")
            return False
        except Exception as e:
            if verbose:
                print(f"   ❌ Stress sync error: {e}")
            return False
