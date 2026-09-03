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
        "python-dotenv>=1.0.0",
        "scipy>=1.10.0"
    )
    .add_local_file("pipeline.py", remote_path="/root/pipeline.py")
)

# 3. Mount Encrypted Secrets from Modal Vault
augur_secret = modal.Secret.from_name("augur-secrets")

# 4. Persistent Volume for Garmin Session Tokens (Prevents Re-Login Security Emails)
token_volume = modal.Volume.from_name("garmin-tokens", create_if_missing=True)
TOKENSTORE_PATH = "/root/.garminconnect"

# =====================================================================
# THE 4 SCHEDULED CRON JOBS (Europe/Brussels Timezone)
# =====================================================================

@app.function(image=image, secrets=[augur_secret], schedule=modal.Cron("30 7 * * *", timezone="Europe/Brussels"))
def morning_reminder():
    """Notification 1 (07:30): Prompt user to sync watch over Bluetooth."""
    from pipeline import notify_morning_sync_reminder
    print("[07:30 Cron] Dispatching Morning Sync Reminder to phone...")
    notify_morning_sync_reminder()

@app.function(
    image=image, 
    secrets=[augur_secret], 
    volumes={TOKENSTORE_PATH: token_volume},
    schedule=modal.Cron("0 8 * * *", timezone="Europe/Brussels"), 
    timeout=180
)
def morning_sync():
    """Notification 2 (08:00): Run pipeline, calculate readiness & dispatch briefing."""
    from pipeline import process_day, notify_morning_readiness
    today_str = date.today().isoformat()
    print(f"[08:00 Cron] Running Daily Telemetry Pipeline for {today_str}...")
    summary = process_day(today_str)
    token_volume.commit()
    print(f"[08:00 Cron] Dispatching Daily Situation Briefing (Recovery: {summary.get('recovery')}%, Strain Target: {summary.get('target_strain_min')}-{summary.get('target_strain_max')})...")
    notify_morning_readiness(summary)

@app.function(image=image, secrets=[augur_secret], schedule=modal.Cron("30 20 * * *", timezone="Europe/Brussels"))
def evening_reminder():
    """Notification 3 (20:30): Prompt user to sync today's strain."""
    from pipeline import notify_evening_sync_reminder
    print("[20:30 Cron] Dispatching Evening Sync Reminder to phone...")
    notify_evening_sync_reminder()

@app.function(
    image=image, 
    secrets=[augur_secret], 
    volumes={TOKENSTORE_PATH: token_volume},
    schedule=modal.Cron("0 21 * * *", timezone="Europe/Brussels"), 
    timeout=180
)
def evening_sync():
    """Notification 4 (21:00): Calculate bedtime prescription & dispatch wind-down."""
    from pipeline import process_day, notify_evening_bedtime
    today_str = date.today().isoformat()
    print(f"[21:00 Cron] Running Bedtime Engine for {today_str}...")
    summary = process_day(today_str)
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
    timeout=180
)
@modal.fastapi_endpoint(method="POST")
def sync_now():
    """
    Public HTTPS Webhook endpoint triggered when tapping 'Sync Now' in AUGUR on iPhone.
    Fetches fresh Garmin endpoints, updates Supabase, and returns latest telemetry JSON.
    Reuses persistent OAuth tokens stored in garmin-tokens volume to avoid sign-in emails.
    """
    from pipeline import process_day
    today_str = date.today().isoformat()
    print(f"[API Webhook] Received 'Sync Now' request for {today_str}...")
    summary = process_day(today_str, quiet=True)
    token_volume.commit()
    return {
        "status": "success",
        "date": summary.get("date"),
        "recovery": summary.get("recovery"),
        "strain": summary.get("strain"),
        "target_strain_min": summary.get("target_strain_min"),
        "target_strain_max": summary.get("target_strain_max"),
        "sleep_need_min": summary.get("sleep_need_min"),
        "bedtime": summary.get("bedtime"),
        "ai_briefing": summary.get("ai_briefing"),
        "health_status": summary.get("health_status"),
        "health_alerts": summary.get("health_alerts"),
    }

@app.function(image=image, secrets=[augur_secret], timeout=30)
@modal.fastapi_endpoint(method="GET")
def get_telemetry():
    """
    Public fast-read HTTPS endpoint for the AUGUR PWA frontend.
    Fetches the latest authenticated daily summary from Supabase and returns JSON,
    including rolling 30-day baseline envelopes for HRV, RHR, Respiration, and SpO2.
    """
    from pipeline import get_supabase_client
    supabase, user_id = get_supabase_client()
    res = (
        supabase.table("daily_summaries")
        .select("*")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .limit(30)
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

    # Fetch recent activities for Tab 3 (Activities & Strain)
    act_res = (
        supabase.table("activities")
        .select("*")
        .eq("user_id", user_id)
        .order("start_time", desc=True)
        .limit(10)
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
        from pipeline import compute_habit_correlations
        latest["habit_correlations"] = compute_habit_correlations(supabase, user_id)
    except Exception:
        latest["habit_correlations"] = []

    # Attach history records (up to 90 days) for Tab 5 Analytics
    latest["history_records"] = records

    return latest

@app.function(image=image, secrets=[augur_secret], timeout=30)
@modal.fastapi_endpoint(method="POST")
def log_habits(data: dict):
    """Logs yesterday's habits into Supabase habit_logs table"""
    from pipeline import get_supabase_client
    supabase, user_id = get_supabase_client()
    row = {
        "user_id": user_id,
        "date": data.get("date"),
        "alcohol": bool(data.get("alcohol", False)),
        "late_meal": bool(data.get("late_meal", False)),
        "late_caffeine": bool(data.get("late_caffeine", False)),
        "any_caffeine": bool(data.get("any_caffeine", False)),
        "screen_in_bed": bool(data.get("screen_in_bed", False)),
        "travel_day": bool(data.get("travel_day", False)),
    }
    res = supabase.table("habit_logs").upsert(row).execute()
    return {"status": "success", "data": res.data}


