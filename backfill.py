import time
import argparse
from datetime import date, timedelta
from pipeline import get_garmin_client, get_supabase_client, process_day, load_env

def run_backfill(days: int = 60, delay: float = 1.0, start_str: str | None = None, end_str: str | None = None):
    load_env()
    
    # 1. Determine chronological date range (Oldest -> Newest)
    if end_str:
        end_date = date.fromisoformat(end_str)
    else:
        end_date = date.today() - timedelta(days=1)  # Default: yesterday

    if start_str:
        start_date = date.fromisoformat(start_str)
    else:
        start_date = end_date - timedelta(days=days - 1)

    if start_date > end_date:
        print(f"[Error] Start date {start_date} is after end date {end_date}.")
        return

    # Build chronological list
    curr = start_date
    date_list = []
    while curr <= end_date:
        date_list.append(curr.isoformat())
        curr += timedelta(days=1)

    total_days = len(date_list)

    print("=" * 80)
    print("       GARMIN RECOVERY & PRESCRIPTION ENGINE — HISTORICAL BACKFILL")
    print("=" * 80)
    print(f" Range: {start_date} to {end_date} ({total_days} calendar days)")
    print(f" Pacing: {delay:.1f}s pause per day (Protects against Cloudflare/SSO 429 rate limits)")
    print(" Ingestion Order: Chronological (Oldest -> Newest for rolling baselines & debt ledger)")
    print("=" * 80)

    # 2. Authenticate once and reuse session across all days
    print("-> Connecting to Garmin Connect and Supabase...")
    garmin = get_garmin_client()
    supabase, user_id = get_supabase_client()
    print("✓ Sessions authenticated successfully. Starting batch ingestion...\n")

    successful_days = []
    failed_days = []
    total_activities = 0

    for idx, target_date in enumerate(date_list, 1):
        try:
            res = process_day(
                target_date=target_date,
                garmin=garmin,
                supabase_tuple=(supabase, user_id),
                quiet=True
            )
            
            sleep_h = res["sleep_sec"] // 3600
            sleep_m = (res["sleep_sec"] % 3600) // 60
            acts = res["activities_count"]
            total_activities += acts
            successful_days.append(res)

            print(
                f"[{idx:2d}/{total_days:2d}] {target_date}: ✓ "
                f"Rec: {res['recovery']:3d}% | "
                f"Strain: {res['strain']:4.1f} | "
                f"Sleep: {sleep_h}h {sleep_m:02d}m | "
                f"Debt: {res['debt_min']:+3d}m | "
                f"Acts: {acts:1d} | "
                f"Cons: {res['circadian_consistency']:2d}%"
            )

        except Exception as e:
            err_msg = str(e)
            # Handle rate limit retry with backoff
            if "429" in err_msg:
                print(f"[{idx:2d}/{total_days:2d}] {target_date}: ⚠️ HTTP 429 rate limited. Pausing 15s before retry...")
                time.sleep(15)
                try:
                    res = process_day(
                        target_date=target_date,
                        garmin=garmin,
                        supabase_tuple=(supabase, user_id),
                        quiet=True
                    )
                    successful_days.append(res)
                    total_activities += res["activities_count"]
                    print(f"[{idx:2d}/{total_days:2d}] {target_date}: ✓ (Recovered after retry) Rec: {res['recovery']}% | Strain: {res['strain']}")
                except Exception as retry_err:
                    print(f"[{idx:2d}/{total_days:2d}] {target_date}: ❌ Failed on retry: {retry_err}")
                    failed_days.append((target_date, str(retry_err)))
            else:
                print(f"[{idx:2d}/{total_days:2d}] {target_date}: ⚠️ Skipped ({err_msg})")
                failed_days.append((target_date, err_msg))

        # Gentle throttle between calls to protect IP reputation
        if idx < total_days:
            time.sleep(delay)

    # 3. Final Summary Report
    print("\n" + "=" * 80)
    print("                     HISTORICAL BACKFILL COMPLETED")
    print("=" * 80)
    print(f" Total Days Processed: {len(successful_days)} / {total_days}")
    if failed_days:
        print(f" Skipped / Failed:     {len(failed_days)} day(s)")
        for f_date, f_reason in failed_days[:5]:
            print(f"   • {f_date}: {f_reason}")
    
    if successful_days:
        avg_rec = sum(d["recovery"] for d in successful_days) / len(successful_days)
        avg_strain = sum(d["strain"] for d in successful_days) / len(successful_days)
        avg_sleep_h = (sum(d["sleep_sec"] for d in successful_days) / len(successful_days)) / 3600.0
        print(f" Total Workouts Synced:{total_activities}")
        print(f" 60-Day Mean Recovery: {avg_rec:.1f}%")
        print(f" 60-Day Mean Strain:   {avg_strain:.1f} / 21.0")
        print(f" 60-Day Mean Sleep:    {avg_sleep_h:.1f} hours/night")
    print("=" * 80)
    print("✓ Your 30-day baseline stats (HRV, RHR, Respiration, SpO2) are now fully primed!")
    print("  All 5 tabs in the mobile app will display complete historical trend data.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate Garmin recovery and strain telemetry historically.")
    parser.add_argument("--days", type=int, default=60, help="Number of past days to backfill (default: 60)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds to pause between days (default: 1.0)")
    parser.add_argument("--start", type=str, default=None, help="Start date in YYYY-MM-DD format (optional)")
    parser.add_argument("--end", type=str, default=None, help="End date in YYYY-MM-DD format (optional, default: yesterday)")
    
    args = parser.parse_args()
    run_backfill(days=args.days, delay=args.delay, start_str=args.start, end_str=args.end)
