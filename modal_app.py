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

# =====================================================================
# THE 4 SCHEDULED CRON JOBS (Europe/Brussels Timezone)
# =====================================================================

@app.function(image=image, secrets=[augur_secret], schedule=modal.Cron("30 7 * * *", timezone="Europe/Brussels"))
def morning_reminder():
    """Notification 1 (07:30): Prompt user to sync watch over Bluetooth."""
    from pipeline import notify_morning_sync_reminder
    print("[07:30 Cron] Dispatching Morning Sync Reminder to phone...")
    notify_morning_sync_reminder()

@app.function(image=image, secrets=[augur_secret], schedule=modal.Cron("0 8 * * *", timezone="Europe/Brussels"), timeout=180)
def morning_sync():
    """Notification 2 (08:00): Run pipeline, calculate readiness & dispatch briefing."""
    from pipeline import process_day, notify_morning_readiness
    today_str = date.today().isoformat()
    print(f"[08:00 Cron] Running Daily Telemetry Pipeline for {today_str}...")
    summary = process_day(today_str)
    print(f"[08:00 Cron] Dispatching Daily Situation Briefing (Recovery: {summary.get('recovery')}%, Strain Target: {summary.get('target_strain_min')}-{summary.get('target_strain_max')})...")
    notify_morning_readiness(summary)

@app.function(image=image, secrets=[augur_secret], schedule=modal.Cron("30 20 * * *", timezone="Europe/Brussels"))
def evening_reminder():
    """Notification 3 (20:30): Prompt user to sync today's strain."""
    from pipeline import notify_evening_sync_reminder
    print("[20:30 Cron] Dispatching Evening Sync Reminder to phone...")
    notify_evening_sync_reminder()

@app.function(image=image, secrets=[augur_secret], schedule=modal.Cron("0 21 * * *", timezone="Europe/Brussels"), timeout=180)
def evening_sync():
    """Notification 4 (21:00): Calculate bedtime prescription & dispatch wind-down."""
    from pipeline import process_day, notify_evening_bedtime
    today_str = date.today().isoformat()
    print(f"[21:00 Cron] Running Bedtime Engine for {today_str}...")
    summary = process_day(today_str)
    print(f"[21:00 Cron] Dispatching Bedtime Prescription (Target Lights-Out: {summary.get('bedtime')})...")
    notify_evening_bedtime(summary)

# =====================================================================
# ON-DEMAND WEBHOOK API FOR THE "SYNC NOW" BUTTON IN AUGUR PWA
# =====================================================================

@app.function(image=image, secrets=[augur_secret], timeout=180)
@modal.fastapi_endpoint(method="POST")
def sync_now():
    """
    Public HTTPS Webhook endpoint triggered when tapping 'Sync Now' in AUGUR on iPhone.
    Fetches fresh Garmin endpoints, updates Supabase, and returns latest telemetry JSON.
    """
    from pipeline import process_day
    today_str = date.today().isoformat()
    print(f"[API Webhook] Received 'Sync Now' request for {today_str}...")
    summary = process_day(today_str, quiet=True)
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
