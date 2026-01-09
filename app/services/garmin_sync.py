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

                # Sync Body Battery
                bb_synced = self._sync_body_battery(garmin, user_id, date_str, verbose)
                if bb_synced:
                    synced_data.append(f"🔋 Body Battery ({date_str})")

                # Sync Daily Activity
                activity_synced = self._sync_daily_activity(garmin, user_id, date_str, verbose)
                if activity_synced:
                    synced_data.append(f"👣 Daily Activity ({date_str})")
            
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
                        summary = hrv_data['hrvSummary'] or {}
                        hrv_avg = summary.get('lastNightAvg')
                        
                        if hrv_avg is None and verbose:
                             print(f"   ⚠️ HRV data found but no lastNightAvg. Keys: {summary.keys()}")
                except Exception as e:
                    if verbose:
                        print(f"   ⚠️ HRV sync warning: {e}")
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

    def _sync_body_battery(self, garmin, user_id: int, date_str: str, verbose: bool) -> bool:
        """Sync Body Battery data for a specific date."""
        try:
            if verbose:
                print("\n🔋 Checking Body Battery data...")
            
            # Usually get_body_battery returns a list of values throughout the day
            # We want to extract summary stats if available, or calculate them
            bb_data = garmin.get_body_battery(date_str)
            
            if bb_data:
                # API structure variations handling
                stats = None
                
                # Check for direct summary stats (common in recent API versions)
                if isinstance(bb_data, list):
                    # If it's a list, it might be the timeline. We can calculate min/max
                    values = [x['value'] for x in bb_data if 'value' in x and x['value'] is not None]
                    if values:
                        stats = {
                            'highest': max(values),
                            'lowest': min(values),
                            'charged': None, # Hard to calc from raw list without events
                            'drained': None
                        }
                elif isinstance(bb_data, dict):
                    # Often comes as a dict with 'bodyBatteryValuesArray' and maybe 'bodyBatteryValueDescriptorDTOList'
                    # Or sometimes specific summary fields
                    if 'bodyBatteryValueDescriptorDTOList' in bb_data:
                        # Sometimes descriptors contain summary? No, usually not.
                        pass
                    
                    # Try to find array
                    values_arr = bb_data.get('bodyBatteryValuesArray', [])
                    if values_arr:
                         values = [x[1] for x in values_arr if x[1] is not None] # often [timestamp, value]
                         if values:
                            stats = {
                                'highest': max(values),
                                'lowest': min(values),
                                'charged': None, 
                                'drained': None
                            }

                # Better source: User Summary often contains BB max/min
                # But let's check if we can get it from specific BB endpoint data validation
                # Some API versions return e.g. 'charged': 55, 'drained': 40 at top level
                if isinstance(bb_data, dict):
                     if 'charged' in bb_data: stats['charged'] = bb_data['charged']
                     if 'drained' in bb_data: stats['drained'] = bb_data['drained']

                # Fallback: Try get_user_summary for authoritative max/min/charged/drained
                # It's cleaner to just call User Summary if we can, but let's try to stick to specific calls for now
                # or acknowledge we might need to mix them.
                # Actually, get_body_battery often returns just the timeseries. 
                # Let's try to fetch user summary for BB too.
                
                # ...Wait, best practice with garminconnect is often get_user_summary
                summary = garmin.get_user_summary(date_str)
                if summary:
                    # Summary usually has "bodyBatteryChargedValue", "bodyBatteryDrainedValue", 
                    # "bodyBatteryHighestValue", "bodyBatteryLowestValue"
                    if 'bodyBatteryHighestValue' in summary:
                        stats = {
                            'highest': summary.get('bodyBatteryHighestValue'),
                            'lowest': summary.get('bodyBatteryLowestValue'),
                            'charged': summary.get('bodyBatteryChargedValue'),
                            'drained': summary.get('bodyBatteryDrainedValue')
                        }

                if stats and (stats.get('highest') is not None or stats.get('charged') is not None):
                    result = self.supabase_client.add_body_battery_log(
                        user_id=user_id,
                        date=date_str,
                        highest=stats.get('highest'),
                        lowest=stats.get('lowest'),
                        charged=stats.get('charged'),
                        drained=stats.get('drained')
                    )
                    if result:
                        if verbose:
                            print(f"   ✅ Body Batt: High {stats.get('highest')}, Low {stats.get('lowest')} (⚡+{stats.get('charged')}/-{stats.get('drained')})")
                        return True
                else:
                    if verbose:
                        print("   ⏳ No Body Battery data yet")
            return False
            
        except Exception as e:
            if verbose:
                print(f"   ❌ Body Battery sync error: {e}")
            return False

    def _sync_daily_activity(self, garmin, user_id: int, date_str: str, verbose: bool) -> bool:
        """Sync daily activity (steps, intensity) for a specific date."""
        try:
            if verbose:
                print("\n👣 Checking Daily Activity data...")
            
            summary = garmin.get_user_summary(date_str)
            
            if summary:
                steps = summary.get('totalSteps')
                step_goal = summary.get('dailyStepGoal')
                floors = summary.get('floorsAscended')
                distance = summary.get('totalDistanceMeters')
                
                mod_min = summary.get('moderateIntensityMinutes')
                vig_min = summary.get('vigorousIntensityMinutes')
                intensity_goal = summary.get('intensityMinutesGoal')
                
                if steps is not None:
                    result = self.supabase_client.add_daily_activity_log(
                        user_id=user_id,
                        date=date_str,
                        steps=steps,
                        step_goal=step_goal,
                        floors_climbed=floors,
                        distance_meters=distance,
                        moderate_intensity_minutes=mod_min,
                        vigorous_intensity_minutes=vig_min,
                        intensity_minutes_goal=intensity_goal
                    )
                    
                    if result:
                        if verbose:
                            print(f"   ✅ Activity: {steps} steps (Goal: {step_goal})")
                            total_intensity = (mod_min or 0) + (vig_min or 0) * 2
                            if total_intensity > 0:
                                print(f"   🔥 Intensity: {total_intensity} intensity minutes")
                        return True
                else:
                    if verbose:
                        print("   ⏳ No activity data yet")
            return False
            
        except Exception as e:
            if verbose:
                print(f"   ❌ Activity sync error: {e}")
            return False
