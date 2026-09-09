from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Any
from garminconnect import Garmin
from supabase import Client

from engine.config import USER_TIMEZONE, APP_USER_EMAIL, safe_round
from engine.models.day_record import DayRecord
from engine.models.activity_record import ActivityRecord
from engine.models.user_baselines import UserBaselines
from engine.connectors.garmin import GarminConnector
from engine.connectors.supabase import SupabaseConnector
from engine.calculators.sleep import (
    calculate_sleep_ledger_and_bedtime,
    calculate_circadian_consistency,
    calculate_sleep_restoration_and_restlessness,
    calculate_social_jetlag,
    calculate_circadian_windows,
)
from engine.calculators.strain import (
    calculate_activity_strain,
    calculate_strain_and_curve,
    check_hr_sync_freshness,
    calculate_target_strain_window,
    calculate_chronic_strain_debt,
    calculate_acwr,
    calculate_training_monotony,
    calculate_load_polarization,
    calculate_sport_strain_penalties,
)
from engine.calculators.recovery import (
    calculate_recovery_and_health_stress,
    calculate_workout_prescriber,
    calculate_immune_strain_index,
    calculate_daytime_stress_balance,
)
from engine.calculators.autonomic import (
    calculate_autonomic_sleep_profile,
    calculate_hrv_trend_slope,
)
from engine.calculators.metabolic import (
    calculate_activity_metabolic_and_recovery,
    calculate_alcohol_latency,
    calculate_caffeine_clearance,
)
from engine.calculators.habits import (
    calculate_habit_correlations_from_records,
    calculate_weather_sleep_correlation,
)
from engine.services.ai_coach import AICoach
from engine.presentation import print_app_dashboard

def process_day(
    target_date: str,
    garmin: Optional[Garmin] = None,
    supabase_tuple: Optional[tuple[Client, str]] = None,
    quiet: bool = False
) -> dict[str, Any]:
    """
    Main pipeline execution:
    Coordinates Garmin extraction -> Model instantiation -> Sports Science Calculators -> Supabase Upserts.
    """
    if not quiet:
        print(f"\n========================================================")
        print(f" Processing V2 Garmin Telemetry Engine for: {target_date}")
        print(f"========================================================")

    # 1. Connect
    garmin_conn = GarminConnector()
    garmin_client = garmin or garmin_conn.get_client()

    if supabase_tuple:
        client, user_id = supabase_tuple
        supabase_conn = SupabaseConnector(client=client, user_id=user_id)
    else:
        supabase_conn = SupabaseConnector()
        client, user_id = supabase_conn.authenticate()

    # 2. Fetch User Baselines
    baselines = supabase_conn.get_user_baselines()
    max_hr = baselines.max_hr
    base_sleep_need = baselines.baseline_sleep_need_min
    debt_payback_rate = baselines.debt_payback_rate
    user_sex = baselines.sex
    target_wake_time = baselines.target_wake_time

    # 3. Pull Garmin Endpoints with Exact Multi-Path Extraction
    print("-> Fetching Garmin endpoints...")
    sleep_raw = {}
    try:
        sleep_raw = garmin_client.get_sleep_data(target_date) or {}
    except Exception as e:
        print(f"  [Garmin Warning] Sleep endpoint: {e}")

    hrv_raw = {}
    try:
        hrv_raw = garmin_client.get_hrv_data(target_date) or {}
    except Exception as e:
        print(f"  [Garmin Warning] HRV endpoint: {e}")

    hr_raw = {}
    try:
        hr_raw = garmin_client.get_heart_rates(target_date) or {}
    except Exception as e:
        print(f"  [Garmin Warning] Heart rates endpoint: {e}")

    rhr_raw = None
    try:
        rhr_raw = garmin_client.get_rhr_day(target_date)
    except Exception as e:
        print(f"  [Garmin Warning] RHR day endpoint: {e}")

    # Multi-path Resting Heart Rate (RHR) extraction
    today_rhr = None
    if isinstance(rhr_raw, dict):
        # 1. Try Garmin metricsMap structure: allMetrics -> metricsMap -> WELLNESS_RESTING_HEART_RATE
        metrics_list = (
            rhr_raw.get("allMetrics", {})
            .get("metricsMap", {})
            .get("WELLNESS_RESTING_HEART_RATE", [])
        )
        if metrics_list and isinstance(metrics_list, list) and len(metrics_list) > 0:
            val = metrics_list[0].get("value")
            if val is not None:
                today_rhr = int(round(float(val)))

        # 2. Try direct root keys
        if today_rhr is None:
            val = (
                rhr_raw.get("restingHeartRate") or 
                rhr_raw.get("allDayMetDTO", {}).get("restingHeartRate") or 
                rhr_raw.get("statistics", {}).get("restingHeartRate")
            )
            if val is not None:
                today_rhr = int(round(float(val)))

    # 3. Fallback to intraday heart rate root property
    if today_rhr is None and isinstance(hr_raw, dict):
        val = hr_raw.get("restingHeartRate")
        if val is not None:
            today_rhr = int(round(float(val)))

    # Sleep Vitals Extraction
    daily_sleep = sleep_raw.get("dailySleepDTO") or {}
    sleep_actual_sec = daily_sleep.get("sleepTimeSeconds")

    is_today = (target_date == date.today().isoformat())
    if is_today and (not sleep_actual_sec or sleep_actual_sec <= 0):
        print(f"\n  [Sync Notice] Today's sleep data ({target_date}) has not yet synced from your Garmin watch.")
        print("  -> Open Garmin Connect on your phone to complete the Bluetooth sync.")
        print("  -> Calculating provisional readiness from available telemetry...\n")

    sleep_bed_sec = None
    if daily_sleep.get("sleepStartTimestampGMT") and daily_sleep.get("sleepEndTimestampGMT"):
        sleep_bed_sec = int((daily_sleep["sleepEndTimestampGMT"] - daily_sleep["sleepStartTimestampGMT"]) / 1000)

    sleep_efficiency = round((sleep_actual_sec / sleep_bed_sec) * 100, 1) if sleep_actual_sec and sleep_bed_sec else None

    today_resp = daily_sleep.get("avgRespirationValue") or daily_sleep.get("averageRespirationValue")
    today_spo2 = daily_sleep.get("avgSpO2") or daily_sleep.get("averageSpO2Value")

    hrv_summary = hrv_raw.get("hrvSummary") or {}
    today_hrv = hrv_summary.get("lastNightAvg")

    stages_timeline = []
    if "sleepLevelsMap" in daily_sleep and daily_sleep["sleepLevelsMap"]:
        for stage_name, intervals in daily_sleep["sleepLevelsMap"].items():
            for entry in intervals:
                stages_timeline.append({
                    "stage": stage_name,
                    "start": entry.get("startGMT"),
                    "end": entry.get("endGMT")
                })

    # 4. Compute Strain & 96-Bucket Curve
    print("-> Calculating Timezone-Aware Cardiovascular Strain...")
    day_strain, strain_curve = calculate_strain_and_curve(
        hr_raw, today_rhr or 50, max_hr, target_date, sex=user_sex
    )
    sync_freshness = check_hr_sync_freshness(hr_raw, target_date)

    # 5. Fetch Multi-day History & Yesterday's Target
    print("-> Pulling baseline history & multi-day records...")
    history = supabase_conn.get_daily_history(target_date, limit=60)
    activities_14d = supabase_conn.get_trailing_activities(target_date, days=14)

    stress_raw = None
    try:
        stress_raw = garmin_client.get_all_day_stress(target_date)
    except Exception:
        try:
            stress_raw = garmin_client.get_stress_data(target_date)
        except Exception:
            pass

    prev_summary = supabase_conn.get_previous_day_summary(target_date)
    yesterday_habit = supabase_conn.get_recent_habit(target_date)

    last_night_target = prev_summary.get("sleep_need_min", base_sleep_need) if prev_summary else base_sleep_need

    # 6. Run Core Physiological Engines
    recovery_score, driver, alerts, health_status, conf, vitals_stats = calculate_recovery_and_health_stress(
        today_hrv, today_rhr, today_resp, today_spo2, sleep_actual_sec, last_night_target, history
    )

    current_debt, target_tonight_min, bedtime_str, sleep_equation_str = calculate_sleep_ledger_and_bedtime(
        base_sleep_need, debt_payback_rate, prev_summary, day_strain, target_date, target_wake_time=target_wake_time
    )

    target_strain_min, target_strain_max = calculate_target_strain_window(recovery_score, health_status)

    start_gmt = daily_sleep.get("sleepStartTimestampGMT")
    end_gmt = daily_sleep.get("sleepEndTimestampGMT")
    today_onset_dt = datetime.fromtimestamp(start_gmt / 1000, tz=ZoneInfo("UTC")).astimezone(USER_TIMEZONE) if start_gmt else None
    today_wake_dt = datetime.fromtimestamp(end_gmt / 1000, tz=ZoneInfo("UTC")).astimezone(USER_TIMEZONE) if end_gmt else None
    today_onset_iso = today_onset_dt.isoformat() if today_onset_dt else None
    today_wake_iso = today_wake_dt.isoformat() if today_wake_dt else None

    circadian_consistency = calculate_circadian_consistency(history, today_onset_dt, today_wake_dt)

    # 7. Compute Version 2 Sports Science & Autonomic Matrix
    print("-> Computing Version 2 Sports Science & Autonomic Matrix...")
    workout_prescriber = calculate_workout_prescriber(recovery_score)
    immune_info = calculate_immune_strain_index(today_hrv, today_rhr, today_resp, today_spo2, history)
    sleep_profile = calculate_autonomic_sleep_profile(sleep_raw, today_rhr)
    hrv_slope = calculate_hrv_trend_slope(hrv_raw)
    sleep_restoration = calculate_sleep_restoration_and_restlessness(daily_sleep, sleep_raw)
    social_jetlag = calculate_social_jetlag(history)
    circadian_windows = calculate_circadian_windows(target_wake_time, bedtime_str)

    combined_7d = [{"day_strain": day_strain, "target_strain_max": target_strain_max}] + history[:6]
    chronic_debt = calculate_chronic_strain_debt(combined_7d)
    alcohol_latency = calculate_alcohol_latency(sleep_raw, yesterday_habit, 45.0)
    caffeine_info = calculate_caffeine_clearance(yesterday_habit, bedtime_str)

    combined_28d = [{"day_strain": day_strain, "recovery_score": recovery_score, "date": target_date, "sleep_efficiency": sleep_efficiency}] + history
    sport_penalties = calculate_sport_strain_penalties(activities_14d, combined_28d)
    weather_corr = calculate_weather_sleep_correlation(combined_28d)
    acwr_info = calculate_acwr(combined_28d)
    monotony_info = calculate_training_monotony(combined_7d)
    polarization_info = calculate_load_polarization(activities_14d, max_hr, today_rhr or 50)
    stress_balance = calculate_daytime_stress_balance(stress_raw)

    metrics_v2 = {
        "workout_prescriber": workout_prescriber,
        "immune_info": immune_info,
        "immune_strain": immune_info,
        "sleep_profile": sleep_profile,
        "autonomic_profile": sleep_profile,
        "hrv_slope": hrv_slope,
        "sleep_restoration": sleep_restoration,
        "sleep_stages": sleep_restoration.get("sleep_stages") if sleep_restoration else None,
        "social_jetlag": social_jetlag,
        "circadian_windows": circadian_windows,
        "chronic_debt": chronic_debt,
        "chronic_strain_debt": chronic_debt,
        "alcohol_latency": alcohol_latency,
        "alcohol_clearance": alcohol_latency,
        "caffeine_info": caffeine_info,
        "caffeine_clearance": caffeine_info,
        "sport_penalties": sport_penalties,
        "sport_strain_penalties": sport_penalties,
        "weather_corr": weather_corr,
        "weather_sleep": weather_corr,
        "acwr_info": acwr_info,
        "acwr": acwr_info,
        "monotony_info": monotony_info,
        "training_monotony": monotony_info,
        "polarization_info": polarization_info,
        "load_polarization": polarization_info,
        "stress_balance": stress_balance,
        "daytime_stress_balance": stress_balance,
        "recommended_bedtime": bedtime_str,
        "sleep_equation_str": sleep_equation_str,
        "sync_freshness": sync_freshness,
    }

    # 8. Generate AI Morning Coaching Briefing
    ai_briefing = AICoach.generate_briefing(
        recovery_score=recovery_score,
        day_strain=day_strain,
        target_strain_min=target_strain_min,
        target_strain_max=target_strain_max,
        current_debt=current_debt,
        health_status=health_status,
        alerts=alerts,
        driver=driver,
    )

    # 9. Compute Trailing 60-Day Habit Impact Analytics
    habit_logs_60d = supabase_conn.get_habit_logs(target_date, lookback=60)
    habit_correlations = calculate_habit_correlations_from_records(habit_logs_60d, history)

    # 10. Instantiate Strongly-Typed DayRecord Object
    day_record = DayRecord(
        user_id=user_id,
        date=target_date,
        recovery_score=recovery_score,
        recovery_driver=driver,
        hrv_rmssd=today_hrv,
        rhr=today_rhr,
        resp_rate=today_resp,
        spo2=today_spo2,
        day_strain=day_strain,
        target_strain_min=target_strain_min,
        target_strain_max=target_strain_max,
        strain_curve_15m=strain_curve,
        sleep_actual_sec=sleep_actual_sec,
        sleep_bed_sec=sleep_bed_sec,
        sleep_efficiency=sleep_efficiency,
        sleep_onset=today_onset_iso,
        sleep_wake=today_wake_iso,
        sleep_need_min=target_tonight_min,
        sleep_debt_min=current_debt,
        recommended_bedtime=bedtime_str,
        sleep_equation_str=sleep_equation_str,
        circadian_consistency=circadian_consistency,
        sleep_stages_timeline=stages_timeline,
        health_alerts=alerts,
        ai_briefing=ai_briefing,
        immune_strain_index=immune_info.get("immune_strain_index"),
        immune_tier=immune_info.get("tier"),
        nocturnal_dip_pct=sleep_profile.get("dip_pct"),
        sleep_curve_type=sleep_profile.get("curve_shape"),
        hrv_trend_slope=hrv_slope.get("slope"),
        restoration_pct=sleep_restoration.get("restoration_pct"),
        restlessness_index=sleep_restoration.get("restlessness_index"),
        social_jetlag_min=social_jetlag.get("social_jetlag_min"),
        chronic_strain_debt=chronic_debt.get("runway_debt"),
        alcohol_latency_hr=alcohol_latency.get("latency_hr"),
        stress_balance_ratio=stress_balance.get("stress_balance_ratio"),
        metrics_v2=metrics_v2,
    )

    print("-> Upserting daily summary record to Supabase via DayRecord model...")
    supabase_conn.upsert_day_record(day_record)

    # 11. Sync Activities with HR Recovery & Glycogen Depletion
    print("-> Syncing activities with metabolic & autonomic metrics...")
    synced_activity_records = []
    try:
        activities = garmin_client.get_activities_by_date(target_date, target_date) or []
        for act in activities:
            act_id = act.get("activityId")
            avg_hr = safe_round(act.get("averageHR"))
            max_hr_val = safe_round(act.get("maxHR"))
            calories_val = safe_round(act.get("calories"), default=0)
            duration = safe_round(act.get("duration"), default=0)
            distance_val = safe_round(act.get("distance"), decimals=2, default=0.0)
            load_val = safe_round(act.get("activityTrainingLoad"), decimals=1)
            te_val = safe_round(act.get("aerobicTrainingEffect"), decimals=1)

            workout_strain = calculate_activity_strain(
                avg_hr=avg_hr,
                duration_sec=duration,
                rhr=today_rhr or 50,
                max_hr=max_hr,
                sex=user_sex,
            )

            act_v2 = calculate_activity_metabolic_and_recovery(act, max_hr, today_rhr or 50, stress_raw, hr_raw)

            act_record = ActivityRecord(
                id=act_id,
                user_id=user_id,
                date=target_date,
                activity_type=act.get("activityType", {}).get("typeKey", "unknown"),
                name=act.get("activityName", "Workout"),
                start_time=act.get("startTimeGMT"),
                duration_sec=duration,
                avg_hr=avg_hr,
                max_hr=max_hr_val,
                distance_m=distance_val,
                calories=calories_val,
                garmin_load=load_val,
                aerobic_te=te_val,
                workout_strain=workout_strain,
                hrr_60s=act_v2.get("hrr_60s"),
                hrr_120s=act_v2.get("hrr_120s"),
                hrr_benchmark=act_v2.get("hrr_benchmark"),
                glycogen_depleted_kcal=act_v2.get("glycogen_depleted_kcal"),
                carb_refuel_target_g=act_v2.get("carb_refuel_target_g"),
                stress_recovery_min=act_v2.get("stress_recovery_min"),
                metrics_v2=act_v2,
            )
            supabase_conn.upsert_activity_record(act_record)
            synced_activity_records.append(act_record)
    except Exception as e:
        print(f"  [Notice] Activity sync skipped or empty: {e}")

    # 12. Check VO2 Max & Biological Age
    print("-> Checking VO2 Max in training status...")
    vo2_max_val = None
    try:
        training_raw = garmin_client.get_training_status(target_date)
        if isinstance(training_raw, dict):
            vo2_data = training_raw.get("mostRecentVO2Max", {}).get("generic", {})
            vo2_max_val = vo2_data.get("vo2MaxPreciseValue") or vo2_data.get("vo2MaxValue")
        
        if vo2_max_val:
            supabase_conn.update_vo2_max(float(vo2_max_val))
    except Exception:
        pass

    current_vo2 = vo2_max_val or baselines.vo2_max
    chrono_age = date.today().year - baselines.birth_year
    cardio_age = None
    if current_vo2:
        expected_vo2 = 50.5 - (0.37 * chrono_age)
        raw_delta = ((float(current_vo2) - expected_vo2) / 0.37) + ((50.0 - float(today_rhr or 50.0)) / 5.0)
        cardio_age = max(18.0, round(chrono_age - raw_delta, 1))

    cardio_age_info = {
        "chrono_age": chrono_age,
        "vo2_max": current_vo2,
        "rhr": today_rhr,
        "cardio_age": cardio_age,
    }

    # 13. Presentation Dashboard
    if not quiet:
        print_app_dashboard(
            target_date=target_date,
            user_email=APP_USER_EMAIL or baselines.email or "user@garmin.com",
            recovery_score=recovery_score,
            driver=driver,
            alerts=alerts,
            health_status=health_status,
            conf=conf,
            vitals_stats=vitals_stats,
            day_strain=day_strain,
            target_strain_min=target_strain_min,
            target_strain_max=target_strain_max,
            strain_curve=strain_curve,
            sleep_actual_sec=sleep_actual_sec,
            sleep_bed_sec=sleep_bed_sec,
            sleep_efficiency=sleep_efficiency,
            daily_sleep=daily_sleep,
            last_night_target_min=last_night_target,
            current_debt=current_debt,
            target_tonight_min=target_tonight_min,
            bedtime_str=bedtime_str,
            sleep_equation_str=sleep_equation_str,
            circadian_consistency=circadian_consistency,
            activities_list=[a.to_supabase_dict() for a in synced_activity_records],
            cardio_age_info=cardio_age_info,
            ai_briefing=ai_briefing,
            habit_correlations=habit_correlations,
        )

    summary = day_record.to_summary_dict()
    summary.update({
        "activities_count": len(synced_activity_records),
        "vo2_max": current_vo2,
        "health_status": health_status,
    })
    return summary
