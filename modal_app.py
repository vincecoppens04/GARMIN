"""
AUGUR Cloud Backend on Modal.com
- Automated 4x/day crons (Europe/Brussels timezone)
- High-priority health anomaly dispatch
- On-demand 'Sync Now' webhook API for the AUGUR iPhone PWA
"""

from datetime import date
import modal

# 1. Initialize Modal App
app = modal.App("augur-backend")

# 2. Build Serverless Container Image
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi",
        "garminconnect>=0.3.2",
        "curl_cffi>=0.7.0",
        "supabase>=2.0.0",
        "httpx>=0.25.0",
        "python-dotenv>=1.0.0",
        "scipy>=1.10.0"
    )
    .add_local_python_source("engine")
)

# 3. Mount Encrypted Secrets from Modal Vault
augur_secret = modal.Secret.from_name("augur-secrets")

# 4. Persistent Volume for Garmin Session Tokens (Prevents Re-Login Security Emails)
token_volume = modal.Volume.from_name("garmin-tokens", create_if_missing=True)
TOKENSTORE_PATH = "/root/.garminconnect"

# =====================================================================
# CORE ENGINE HELPERS
# =====================================================================

def _sync_and_backfill(garmin, supabase_tuple, lookback_days=7):
    """
    Checks the past `lookback_days` in Supabase daily_summaries.
    If any day is missing or lacks sleep/HR data (e.g. user didn't sync watch for a few days),
    fetches from Garmin and processes each day in strict chronological order (T-n -> T-1 -> T).
    Returns the summary for today.
    """
    from engine import process_day
    from datetime import date, timedelta

    supabase, user_id = supabase_tuple
    today = date.today()
    cutoff = (today - timedelta(days=lookback_days)).isoformat()

    try:
        existing_res = (
            supabase.table("daily_summaries")
            .select("date, sleep_actual_sec, hrv_rmssd, metrics_v2")
            .eq("user_id", user_id)
            .gte("date", cutoff)
            .execute()
        )
        existing_records = {r["date"]: r for r in (existing_res.data or [])}
    except Exception as e:
        print(f"[Backfill Engine] Warning fetching existing summaries: {e}")
        existing_records = {}

    days_to_process = set()
    # Always process today (live data) and yesterday (finalized sleep/strain)
    days_to_process.add(today.isoformat())
    days_to_process.add((today - timedelta(days=1)).isoformat())

    # Check days 2 through lookback_days: if missing or lacking V2 metrics, backfill
    for i in range(2, lookback_days + 1):
        d_str = (today - timedelta(days=i)).isoformat()
        rec = existing_records.get(d_str)
        if not rec or not rec.get("sleep_actual_sec") or not rec.get("hrv_rmssd") or not rec.get("metrics_v2"):
            days_to_process.add(d_str)

    sorted_days = sorted(list(days_to_process))
    print(f"[Backfill Engine] Synchronizing & backfilling {len(sorted_days)} day(s) in chronological order: {sorted_days}...")

    summary_today = None
    for d in sorted_days:
        is_today = (d == today.isoformat())
        try:
            res = process_day(d, garmin=garmin, supabase_tuple=supabase_tuple, quiet=not is_today)
            if is_today:
                summary_today = res
        except Exception as e:
            print(f"[Backfill Engine] Warning processing {d}: {e}")

    token_volume.commit()
    return summary_today

def _fetch_telemetry_payload(user_id=None, supabase=None):
    """
    Fetches the latest authenticated daily summary and historical records from Supabase,
    computing 30-day baseline envelopes for vitals, and packing activities, user baselines,
    and habit correlations into a complete telemetry JSON response.
    """
    from engine import get_supabase_client
    if supabase is None or user_id is None:
        supabase, user_id = get_supabase_client()

    res = (
        supabase.table("daily_summaries")
        .select("*")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .limit(90)
        .execute()
    )
    records = res.data or []
    if not records:
        return {}

    latest = dict(records[0])

    # Compute 30-day baseline envelopes (mu +- 1.5 sigma)
    vitals_baseline = {}
    for key, label, unit in [
        ("hrv_rmssd", "HRV (rMSSD)", "ms"),
        ("rhr", "Resting HR", "bpm"),
        ("resp_rate", "Respiration", "brpm"),
        ("spo2", "Pulse Ox (SpO2)", "%")
    ]:
        vals = [r[key] for r in records if r.get(key) is not None]
        if vals:
            mu = sum(vals) / len(vals)
            std = max(0.5, (sum((x - mu) ** 2 for x in vals) / len(vals)) ** 0.5)
            b_min = round(mu - 1.5 * std, 1)
            b_max = round(mu + 1.5 * std, 1)
            cur = vals[0]
            status = "OK" if b_min <= cur <= b_max else "OUTLIER"
            vitals_baseline[key] = {
                "label": label,
                "val": cur,
                "unit": unit,
                "baseline_min": b_min,
                "baseline_max": b_max,
                "status": status
            }

    latest["vitals_baseline"] = vitals_baseline

    # Fetch recent activities for Tab 3 (Activities & Strain) - Limited to 5
    act_res = (
        supabase.table("activities")
        .select("*")
        .eq("user_id", user_id)
        .order("start_time", desc=True)
        .limit(5)
        .execute()
    )
    latest["activities"] = act_res.data or []

    # Fetch user baselines for Tab 4 (Biological Age)
    try:
        base_res = supabase.table("user_baselines").select("*").eq("user_id", user_id).execute()
        latest["user_baselines"] = base_res.data[0] if base_res.data else {
            "max_hr": 202,
            "baseline_sleep_need_min": 435,
            "vo2_max": 51.5,
            "birth_year": 2004,
        }
    except Exception:
        latest["user_baselines"] = {"max_hr": 202, "baseline_sleep_need_min": 435, "vo2_max": 51.5, "birth_year": 2004}

    # Fetch habit correlations for Tab 4
    try:
        from engine import calculate_habit_correlations
        latest["habit_correlations"] = calculate_habit_correlations(supabase, user_id)
    except Exception:
        latest["habit_correlations"] = []

    # Promote recommended_bedtime and sleep_equation_str if present in metrics_v2
    if latest.get("metrics_v2") and isinstance(latest["metrics_v2"], dict):
        if not latest.get("recommended_bedtime") and "recommended_bedtime" in latest["metrics_v2"]:
            latest["recommended_bedtime"] = latest["metrics_v2"]["recommended_bedtime"]
        if not latest.get("sleep_equation_str") and "sleep_equation_str" in latest["metrics_v2"]:
            latest["sleep_equation_str"] = latest["metrics_v2"]["sleep_equation_str"]

    # Attach history records (up to 90 days) for Tab 5 Analytics
    latest["history_records"] = records

    return latest

@app.function(
    image=image, 
    secrets=[augur_secret], 
    volumes={TOKENSTORE_PATH: token_volume},
    schedule=modal.Cron("0 8 * * *", timezone="Europe/Brussels"), 
    retries=modal.Retries(max_retries=3, backoff_coefficient=2.0, initial_delay=3.0),
    timeout=180
)
def morning_sync():
    """Notification 2 (08:00): Run pipeline, calculate readiness & dispatch briefing."""
    from engine import notify_morning_readiness, get_garmin_client, get_supabase_client
    garmin = get_garmin_client()
    supabase, user_id = get_supabase_client()
    supabase_tuple = (supabase, user_id)

    print("[08:00 Cron] Checking backfill window and synchronizing daily data...")
    summary = _sync_and_backfill(garmin, supabase_tuple, lookback_days=7)
    if summary:
        print(f"[08:00 Cron] Dispatching Daily Situation Briefing (Recovery: {summary.get('recovery')}%, Strain Target: {summary.get('target_strain_min')}-{summary.get('target_strain_max')})...")
        notify_morning_readiness(summary)

@app.function(image=image, secrets=[augur_secret], schedule=modal.Cron("30 7 * * *", timezone="Europe/Brussels"))
def morning_reminder():
    """Notification 1 (07:30): Prompt user to sync watch over Bluetooth."""
    from engine import notify_morning_sync_reminder
    print("[07:30 Cron] Dispatching Morning Sync Reminder to phone...")
    notify_morning_sync_reminder()

@app.function(image=image, secrets=[augur_secret], schedule=modal.Cron("30 20 * * *", timezone="Europe/Brussels"))
def evening_reminder():
    """Notification 3 (20:30): Prompt user to sync today's strain."""
    from engine import notify_evening_sync_reminder
    print("[20:30 Cron] Dispatching Evening Sync Reminder to phone...")
    notify_evening_sync_reminder()

@app.function(
    image=image, 
    secrets=[augur_secret], 
    volumes={TOKENSTORE_PATH: token_volume},
    schedule=modal.Cron("0 21 * * *", timezone="Europe/Brussels"), 
    retries=modal.Retries(max_retries=3, backoff_coefficient=2.0, initial_delay=3.0),
    timeout=180
)
def evening_sync():
    """Notification 4 (21:00): Calculate bedtime prescription & dispatch wind-down with 2-day backfill."""
    from engine import get_garmin_client, get_supabase_client, process_day, notify_evening_bedtime
    from datetime import date
    today_str = date.today().isoformat()
    print(f"[21:00 Cron] Running Bedtime Engine for {today_str} with 2-day backfill...")
    garmin = get_garmin_client()
    supabase_tuple = get_supabase_client()
    summary = _sync_and_backfill(garmin, supabase_tuple, lookback_days=2)
    if not summary:
        summary = process_day(today_str, garmin=garmin, supabase_tuple=supabase_tuple)
    token_volume.commit()
    print(f"[21:00 Cron] Dispatching Bedtime Prescription (Target Lights-Out: {summary.get('bedtime')})...")
    notify_evening_bedtime(summary)

# =====================================================================
# ON-DEMAND WEBHOOK API FOR THE "SYNC NOW" BUTTON IN AUGUR PWA
# =====================================================================

@app.function(
    image=image, 
    secrets=[augur_secret], 
    volumes={TOKENSTORE_PATH: token_volume},
    retries=modal.Retries(max_retries=3, backoff_coefficient=2.0, initial_delay=2.0),
    timeout=180
)
def run_pipeline_sync(lookback_days: int = 2):
    """Internal runner that syncs Garmin and Supabase and returns the telemetry payload."""
    from engine import get_garmin_client, get_supabase_client

    garmin = get_garmin_client()
    supabase, user_id = get_supabase_client()
    supabase_tuple = (supabase, user_id)

    _sync_and_backfill(garmin, supabase_tuple, lookback_days=lookback_days)
    token_volume.commit()
    return _fetch_telemetry_payload(user_id=user_id, supabase=supabase)

@app.function(
    image=image, 
    secrets=[augur_secret], 
    volumes={TOKENSTORE_PATH: token_volume},
    timeout=180
)
@modal.fastapi_endpoint(method="POST")
def sync_now():
    """
    Public HTTPS Webhook endpoint triggered when tapping 'Sync Now' in AUGUR on iPhone.
    Fetches fresh Garmin endpoints, updates Supabase, and returns latest telemetry JSON.
    Reuses persistent OAuth tokens stored in garmin-tokens volume to avoid sign-in emails.
    Automatically checks the past 7 days and backfills any days missed if the watch was not synced.
    """
    from engine import get_garmin_client, get_supabase_client

    garmin = get_garmin_client()
    supabase, user_id = get_supabase_client()
    supabase_tuple = (supabase, user_id)

    _sync_and_backfill(garmin, supabase_tuple, lookback_days=14)
    token_volume.commit()
    return _fetch_telemetry_payload(user_id=user_id, supabase=supabase)

@app.function(
    image=image, 
    secrets=[augur_secret], 
    volumes={TOKENSTORE_PATH: token_volume},
    timeout=600
)
@modal.fastapi_endpoint(method="POST")
def backfill_now(days: int = 14):
    """
    Explicitly forces a full backfill of the past N days from Garmin Connect,
    re-computing all 20 Version 2 metrics and overwriting existing rows in Supabase.
    """
    from engine import get_garmin_client, get_supabase_client, process_day
    from datetime import date, timedelta
    garmin = get_garmin_client()
    supabase, user_id = get_supabase_client()
    supabase_tuple = (supabase, user_id)
    today = date.today()
    results = []
    for i in range(days, -1, -1):
        d_str = (today - timedelta(days=i)).isoformat()
        try:
            print(f"[Forced Backfill] Repopulating {d_str}...")
            res = process_day(d_str, garmin=garmin, supabase_tuple=supabase_tuple, quiet=True)
            results.append({"date": d_str, "status": "ok"})
        except Exception as e:
            print(f"[Forced Backfill] Error {d_str}: {e}")
            results.append({"date": d_str, "status": "error", "error": str(e)})
    token_volume.commit()
    return {"repopulated_days": results, "latest": _fetch_telemetry_payload(user_id=user_id, supabase=supabase)}

@app.function(image=image, secrets=[augur_secret], timeout=30)
@modal.fastapi_endpoint(method="GET")
def get_telemetry():
    """
    Public fast-read HTTPS endpoint for the AUGUR PWA frontend.
    Fetches the latest authenticated daily summary from Supabase and returns JSON,
    including rolling 30-day baseline envelopes for HRV, RHR, Respiration, and SpO2.
    """
    return _fetch_telemetry_payload()

@app.function(image=image, secrets=[augur_secret], timeout=30)
@modal.fastapi_endpoint(method="POST")
def log_habits(data: dict):
    """Logs yesterday's habits into Supabase habit_logs table"""
    from engine import get_supabase_client
    supabase, user_id = get_supabase_client()
    row = {
        "user_id": user_id,
        "date": data.get("date"),
        "alcohol": bool(data.get("alcohol", False)),
        "party": bool(data.get("party", False)),
        "late_meal": bool(data.get("late_meal", False)),
        "late_caffeine": bool(data.get("late_caffeine", False)),
        "any_caffeine": bool(data.get("any_caffeine", False)),
        "screen_in_bed": bool(data.get("screen_in_bed", False)),
        "travel_day": bool(data.get("travel_day", False)),
    }
    try:
        res = supabase.table("habit_logs").upsert(row, on_conflict="user_id,date").execute()
        return {"status": "success", "data": res.data}
    except Exception as e:
        # Graceful fallback if party column is not yet migrated in Supabase
        if "party" in str(e).lower():
            row.pop("party", None)
            res = supabase.table("habit_logs").upsert(row, on_conflict="user_id,date").execute()
            return {"status": "success", "data": res.data, "note": "party column pending"}
        raise e

@app.function(image=image, secrets=[augur_secret], timeout=30)
@modal.fastapi_endpoint(method="POST")
def send_test_notification():
    """Triggers an immediate test push notification with today's live telemetry to the user's phone via OneSignal."""
    import os
    from engine import get_supabase_client, send_phone_notification

    supabase, user_id = get_supabase_client()
    res = (
        supabase.table("daily_summaries")
        .select("*")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )

    if res.data:
        today = res.data[0]
        rec = round(today.get("recovery_score") or 0)
        driver = today.get("recovery_driver") or "Autonomic tone optimal"
        hrv = round(today.get("hrv_rmssd") or 0)
        rhr = round(today.get("rhr") or 0)
        strain = round(float(today.get("day_strain") or 0), 1)
        t_min = round(float(today.get("target_strain_min") or 12.0), 1)
        t_max = round(float(today.get("target_strain_max") or 14.5), 1)
        date_str = today.get("date") or "Today"
        title = f"AUGUR • {date_str} Live Telemetry"
        message = f"Recovery: {rec}% ({driver}) | HRV: {hrv}ms • RHR: {rhr}bpm | Strain: {strain} (Target {t_min}–{t_max})"
    else:
        title = "AUGUR • System Notification"
        message = "AUGUR system connected and operational. Awaiting first telemetry sync."

    delivered, details = send_phone_notification(
        title=title,
        message=message,
        priority="high",
        tags=["zap", "muscle"],
        return_details=True
    )

    return {
        "status": "success" if delivered else "warning",
        "delivered": delivered,
        "recipients": details.get("recipients", 0),
        "onesignal_id": details.get("id"),
        "title": title,
        "message": message,
        "errors": details.get("errors"),
    }

@app.function(image=image, secrets=[augur_secret], timeout=30)
@modal.fastapi_endpoint(method="POST")
def save_settings(data: dict):
    """Saves user physiological baselines (Max HR, Sleep Need, Wake Time, Debt Payback, etc.) into Supabase user_baselines table"""
    from engine import get_supabase_client
    supabase, user_id = get_supabase_client()
    row = {
        "user_id": user_id,
        "max_hr": int(data.get("max_hr", 202)),
        "baseline_sleep_need_min": int(data.get("sleep_need_min", 435)),
        "target_wake_time": str(data.get("target_wake_time", "07:00")),
        "debt_payback_rate": float(data.get("debt_payback_rate", 0.33)),
        "vo2_max": float(data.get("vo2_max", 51.5)),
        "birth_year": int(data.get("birth_year", 2004)),
    }
    try:
        res = supabase.table("user_baselines").upsert(row, on_conflict="user_id").execute()
        return {"status": "success", "data": res.data}
    except Exception as e:
        # Graceful fallback if target_wake_time or debt_payback_rate columns have not yet been added in Supabase
        if "target_wake_time" in str(e).lower():
            row.pop("target_wake_time", None)
        if "debt_payback_rate" in str(e).lower():
            row.pop("debt_payback_rate", None)
        try:
            res = supabase.table("user_baselines").upsert(row, on_conflict="user_id").execute()
            return {"status": "success", "data": res.data, "note": "fallback schema applied"}
        except Exception as inner_e:
            raise inner_e

# =====================================================================
# LOCAL ENTRYPOINT FOR TESTING ON MODAL WITHOUT DEPLOYING
# =====================================================================

@app.local_entrypoint()
def main(action: str = "sync"):
    """
    Test the new engine on Modal serverless cloud using local branch code without deploying to production.
    Usage:
        modal run modal_app.py
        modal run modal_app.py --action morning
        modal run modal_app.py --action evening
    """
    print(f"🚀 Running ephemeral test on Modal cloud (action='{action}')...")
    if action == "morning":
        morning_sync.remote()
        print("✓ Morning sync completed successfully on Modal!")
    elif action == "evening":
        evening_sync.remote()
        print("✓ Evening sync completed successfully on Modal!")
    else:
        res = run_pipeline_sync.remote(lookback_days=2)
        print("✓ Sync executed successfully on Modal cloud!")
        print(f"  Record Date : {res.get('date')}")
        print(f"  Recovery    : {res.get('recovery_score')}% ({res.get('recovery_driver')})")
        print(f"  Day Strain  : {res.get('day_strain')}")
        print(f"  HRV RMSSD   : {res.get('hrv_rmssd')} ms")
        print(f"  Bedtime     : {res.get('bedtime')}")

