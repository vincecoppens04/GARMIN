import math
from datetime import date, timedelta
from pipeline import get_supabase_client, load_env

def fmt_dur(sec: int | float | None) -> str:
    if sec is None or sec <= 0:
        return "0h 00m"
    s = int(round(float(sec)))
    return f"{s // 3600}h {(s % 3600) // 60:02d}m"

def inspect_database():
    load_env()
    print("=" * 80)
    print("      GARMIN RECOVERY & PRESCRIPTION ENGINE — 60-DAY DATA INSPECTION")
    print("=" * 80)
    
    supabase, user_id = get_supabase_client()
    
    # 1. Fetch User Baselines
    b_res = supabase.table("user_baselines").select("*").eq("user_id", user_id).single().execute()
    baselines = b_res.data or {}
    
    # 2. Fetch Daily Summaries
    d_res = supabase.table("daily_summaries")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("date", desc=False)\
        .execute()
    daily_records = d_res.data or []
    
    # 3. Fetch Activities
    a_res = supabase.table("activities")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("date", desc=True)\
        .execute()
    activities = a_res.data or []
    
    total_days = len(daily_records)
    if total_days == 0:
        print("[!] No records found in daily_summaries table for this user.")
        return

    first_date = daily_records[0]["date"]
    last_date = daily_records[-1]["date"]
    
    # -------------------------------------------------------------
    # 1. CONTINUITY & OVERVIEW
    # -------------------------------------------------------------
    print(f"\n[1] DATA CONTINUITY & COVERAGE")
    print(f"  • Date Span:          {first_date}  to  {last_date} ({total_days} recorded days)")
    print(f"  • Total Workouts:     {len(activities)} activities logged")
    print(f"  • User Baseline Need: {baselines.get('baseline_sleep_need_min', 435) // 60}h {baselines.get('baseline_sleep_need_min', 435) % 60:02d}m")
    print(f"  • User Max HR:        {baselines.get('max_hr', 190)} bpm | Sex: {baselines.get('sex', 'male')}")

    # -------------------------------------------------------------
    # 2. RECOVERY SCORE DISTRIBUTION
    # -------------------------------------------------------------
    rec_scores = [r["recovery_score"] for r in daily_records if r.get("recovery_score") is not None]
    green_days = [s for s in rec_scores if s >= 67]
    yellow_days = [s for s in rec_scores if 34 <= s < 67]
    red_days = [s for s in rec_scores if s < 34]
    
    avg_rec = sum(rec_scores) / len(rec_scores) if rec_scores else 0
    recent_7_rec = sum(rec_scores[-7:]) / len(rec_scores[-7:]) if len(rec_scores) >= 7 else avg_rec
    
    print(f"\n[2] RECOVERY SCORE ANALYSIS")
    print(f"  • 60-Day Mean Recovery: {avg_rec:.1f}% (Recent 7-Day Mean: {recent_7_rec:.1f}%)")
    print(f"  • Range: Min {min(rec_scores)}% | Max {max(rec_scores)}%")
    print(f"  • Color Zones:")
    print(f"      🟢 Green  (>=67% - Primed):   {len(green_days):2d} days ({len(green_days)/total_days*100:4.1f}%)")
    print(f"      🟡 Yellow (34-66% - Normal):  {len(yellow_days):2d} days ({len(yellow_days)/total_days*100:4.1f}%)")
    print(f"      🔴 Red    (<34% - Fatigued):  {len(red_days):2d} days ({len(red_days)/total_days*100:4.1f}%)")

    # -------------------------------------------------------------
    # 3. SLEEP & DEBT DYNAMICS
    # -------------------------------------------------------------
    sleep_secs = [r["sleep_actual_sec"] for r in daily_records if r.get("sleep_actual_sec") is not None]
    effs = [r["sleep_efficiency"] for r in daily_records if r.get("sleep_efficiency") is not None]
    debts = [r["sleep_debt_min"] for r in daily_records if r.get("sleep_debt_min") is not None]
    consistencies = [r["circadian_consistency"] for r in daily_records if r.get("circadian_consistency") is not None]
    
    avg_sleep_s = sum(sleep_secs) / len(sleep_secs) if sleep_secs else 0
    avg_eff = sum(effs) / len(effs) if effs else 0
    current_debt = debts[-1] if debts else 0
    peak_debt = max(debts) if debts else 0
    days_with_debt = len([d for d in debts if d > 0])
    avg_cons = sum(consistencies) / len(consistencies) if consistencies else 0

    print(f"\n[3] SLEEP & DEBT LEDGER DYNAMICS")
    print(f"  • Average Actual Sleep:  {fmt_dur(avg_sleep_s)} / night")
    print(f"  • Average Efficiency:    {avg_eff:.1f}%")
    print(f"  • Circadian Regularity:  {avg_cons:.1f}% 7-day average")
    print(f"  • Current Sleep Debt:    {current_debt:+d} min (Latest night: {last_date})")
    print(f"  • Peak Sleep Debt:       {peak_debt:+d} min")
    print(f"  • Acute Debt Exposure:   {days_with_debt} of {total_days} days had acute debt ({days_with_debt/total_days*100:.1f}%)")

    # -------------------------------------------------------------
    # 4. CARDIOVASCULAR STRAIN
    # -------------------------------------------------------------
    strains = [float(r["day_strain"]) for r in daily_records if r.get("day_strain") is not None]
    avg_strain = sum(strains) / len(strains) if strains else 0
    max_strain = max(strains) if strains else 0
    recent_7_strain = sum(strains[-7:]) / len(strains[-7:]) if len(strains) >= 7 else avg_strain

    in_target = 0
    over_target = 0
    under_target = 0
    for r in daily_records:
        s = float(r.get("day_strain") or 0)
        t_min = float(r.get("target_strain_min") or 0)
        t_max = float(r.get("target_strain_max") or 21)
        if s < t_min:
            under_target += 1
        elif s <= t_max:
            in_target += 1
        else:
            over_target += 1

    print(f"\n[4] CARDIOVASCULAR STRAIN (0 - 21.0)")
    print(f"  • 60-Day Mean Strain:    {avg_strain:.1f} (Recent 7-Day Mean: {recent_7_strain:.1f})")
    print(f"  • Peak Day Strain:       {max_strain:.1f} / 21.0")
    print(f"  • Target Execution:      {in_target} in target bracket | {over_target} overreaching | {under_target} under target")

    # -------------------------------------------------------------
    # 5. ROLLING PHYSIOLOGICAL BASELINES
    # -------------------------------------------------------------
    hrv_vals = [r["hrv_rmssd"] for r in daily_records[-30:] if r.get("hrv_rmssd") is not None]
    rhr_vals = [r["rhr"] for r in daily_records[-30:] if r.get("rhr") is not None]
    resp_vals = [r["resp_rate"] for r in daily_records[-30:] if r.get("resp_rate") is not None]
    spo2_vals = [r["spo2"] for r in daily_records[-30:] if r.get("spo2") is not None]

    mu_hrv = sum(hrv_vals) / len(hrv_vals) if hrv_vals else 0
    std_hrv = (sum((x - mu_hrv) ** 2 for x in hrv_vals) / len(hrv_vals)) ** 0.5 if len(hrv_vals) > 1 else 0
    
    mu_rhr = sum(rhr_vals) / len(rhr_vals) if rhr_vals else 0
    std_rhr = (sum((x - mu_rhr) ** 2 for x in rhr_vals) / len(rhr_vals)) ** 0.5 if len(rhr_vals) > 1 else 0

    mu_resp = sum(resp_vals) / len(resp_vals) if resp_vals else 0
    mu_spo2 = sum(spo2_vals) / len(spo2_vals) if spo2_vals else 0

    print(f"\n[5] CURRENT 30-DAY CONVERGED BASELINES (Trailing 30 Days)")
    print(f"  • HRV (rMSSD):           μ = {mu_hrv:.1f} ms  |  σ = {std_hrv:.1f} ms  (Envelope: {mu_hrv - 1.5*std_hrv:.1f} – {mu_hrv + 1.5*std_hrv:.1f} ms)")
    print(f"  • Resting Heart Rate:    μ = {mu_rhr:.1f} bpm |  σ = {std_rhr:.1f} bpm  (Envelope: {mu_rhr - 1.5*std_rhr:.1f} – {mu_rhr + 1.5*std_rhr:.1f} bpm)")
    print(f"  • Respiration Rate:      μ = {mu_resp:.1f} brpm")
    print(f"  • Pulse Ox (SpO2):       μ = {mu_spo2:.1f}%")

    # Biological Age
    vo2_max = baselines.get("vo2_max")
    birth_year = baselines.get("birth_year", 2004)
    chrono_age = date.today().year - int(birth_year) if birth_year else 22
    if vo2_max and mu_rhr:
        exp_vo2 = 50.5 - (0.37 * chrono_age)
        raw_delta = ((float(vo2_max) - exp_vo2) / 0.37) + ((50.0 - float(mu_rhr)) / 5.0)
        # Biological maturity floor (18.0 years) - matching Garmin Fitness Age bounds
        cardio_age = max(18.0, round(chrono_age - raw_delta, 1))
        diff = round(chrono_age - cardio_age, 1)
        sign = "-" if diff > 0 else "+"
        word = "younger" if diff > 0 else "older"
        peak_tag = " (Optimal Biological Peak)" if cardio_age <= 18.0 and chrono_age >= 18 else ""
        print(f"  • Cardiovascular Age:    {cardio_age:.1f} yrs (Chronological: {chrono_age} yrs, {sign}{abs(diff):.1f} yrs {word}{peak_tag}) ★")

    # -------------------------------------------------------------
    # 6. TOP 5 HIGHEST STRAIN WORKOUTS
    # -------------------------------------------------------------
    print(f"\n[6] TOP 5 HIGHEST EXERTION WORKOUTS")
    sorted_acts = sorted(activities, key=lambda a: float(a.get("workout_strain") or 0), reverse=True)
    if not sorted_acts:
        print("  (No discrete activities found)")
    for i, act in enumerate(sorted_acts[:5], 1):
        name = act.get("name", "Workout")
        d_str = act.get("date", "--")
        strain = float(act.get("workout_strain") or 0)
        dur = fmt_dur(act.get("duration_sec"))
        dist_km = (act.get("distance_m") or 0) / 1000.0
        dist_str = f" | {dist_km:.2f} km" if dist_km > 0.1 else ""
        avg_h = act.get("avg_hr", "--")
        max_h = act.get("max_hr", "--")
        load = act.get("garmin_load", "--")
        te = act.get("aerobic_te", "--")
        print(f"  {i}. {d_str} — {name} [{strain:.1f} Strain]")
        print(f"     Duration: {dur}{dist_str} | HR: Avg {avg_h} / Max {max_h} | EPOC Load: {load} | TE: {te}")

    # -------------------------------------------------------------
    # 7. HEALTH ANOMALY AUDIT
    # -------------------------------------------------------------
    anomalies = [r for r in daily_records if r.get("health_alerts") and len(r["health_alerts"]) > 0]
    print(f"\n[7] PRE-SYMPTOMATIC HEALTH ANOMALY LOG")
    if not anomalies:
        print("  ✓ All 60 days had completely normal physiological metrics (0 anomaly events).")
    else:
        print(f"  Detected {len(anomalies)} day(s) with anomalous vital excursions:")
        for r in anomalies:
            d_str = r.get("date")
            alerts = r.get("health_alerts", [])
            print(f"  • {d_str}: {', '.join(alerts)}")

    print("\n" + "=" * 80)
    print("                     END OF DATA INSPECTION REPORT")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    inspect_database()
