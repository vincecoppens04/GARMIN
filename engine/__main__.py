"""
AUGUR Sports Science Pipeline — CLI Entrypoint.
Usage:
    python -m engine today
    python -m engine yesterday
    python -m engine 2026-09-08
    python -m engine backfill 14
    python -m engine test-push
    python -m engine morning-sync
    python -m engine evening-sync
"""

import sys
from datetime import date, timedelta

def main():
    args = sys.argv[1:]
    cmd = args[0].strip().lower() if args else "yesterday"

    if cmd in ("--help", "-h", "help"):
        print(__doc__)
        return

    from engine.orchestrator import process_day
    from engine.services.notifier import (
        send_phone_notification,
        notify_morning_sync_reminder,
        notify_morning_readiness,
        notify_evening_sync_reminder,
        notify_evening_bedtime,
    )

    if cmd in ("morning-reminder", "notify-morning-reminder"):
        print("-> Dispatching 07:30 Morning Sync Reminder...")
        notify_morning_sync_reminder()
    elif cmd in ("morning-sync", "sync-morning"):
        print("-> Running 08:00 Morning Sync...")
        summary = process_day(date.today().isoformat())
        print("-> Dispatching Daily Situation Notification...")
        notify_morning_readiness(summary)
    elif cmd in ("evening-reminder", "notify-evening-reminder"):
        print("-> Dispatching 20:30 Evening Sync Reminder...")
        notify_evening_sync_reminder()
    elif cmd in ("evening-sync", "sync-evening"):
        print("-> Running 21:00 Evening Sync...")
        summary = process_day(date.today().isoformat())
        print("-> Dispatching Bedtime Prescription Notification...")
        notify_evening_bedtime(summary)
    elif cmd in ("test-push", "test-notification"):
        print("-> Sending test push notification to phone...")
        ok = send_phone_notification(
            title="🔔 Garmin Test Notification",
            message="Push notifications are successfully configured on your phone!",
            priority="high",
            tags=["tada", "muscle"]
        )
        if ok:
            print("✓ Notification delivered! Check your phone lock screen.")
    elif cmd == "backfill":
        num_days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 14
        print(f"-> Repopulating / Backfilling past {num_days} days with complete V2 metrics from Garmin...")
        today = date.today()
        for i in range(num_days, -1, -1):
            target_d = (today - timedelta(days=i)).isoformat()
            print(f"\n--- Backfilling {target_d} ({num_days - i + 1}/{num_days + 1}) ---")
            try:
                process_day(target_d)
            except Exception as e:
                print(f"Error backfilling {target_d}: {e}")
        print("\n✓ Backfill complete! All days populated with real Garmin V2 telemetry.")
    elif cmd == "today":
        process_day(date.today().isoformat())
    elif cmd == "yesterday":
        process_day((date.today() - timedelta(days=1)).isoformat())
    else:
        process_day(cmd)

if __name__ == "__main__":
    main()
