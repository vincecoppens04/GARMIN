import textwrap
from typing import Optional, Any

def print_app_dashboard(
    target_date: str,
    user_email: str,
    recovery_score: int,
    driver: str,
    alerts: list[str],
    health_status: str,
    conf: str,
    vitals_stats: dict[str, Any],
    day_strain: float,
    target_strain_min: float,
    target_strain_max: float,
    strain_curve: list[dict[str, Any]],
    sleep_actual_sec: Optional[int],
    sleep_bed_sec: Optional[int],
    sleep_efficiency: Optional[float],
    daily_sleep: dict[str, Any],
    last_night_target_min: int,
    current_debt: int,
    target_tonight_min: int,
    bedtime_str: str,
    sleep_equation_str: str,
    circadian_consistency: int,
    activities_list: list[dict[str, Any]],
    cardio_age_info: dict[str, Any],
    ai_briefing: str = "",
    habit_correlations: Optional[list[dict[str, Any]]] = None,
) -> None:
    def fmt_dur(sec: int | float | None) -> str:
        if sec is None or sec <= 0:
            return "0h 00m"
        s = int(round(float(sec)))
        return f"{s // 3600}h {(s % 3600) // 60:02d}m"

    # 1. Recovery Badge
    if recovery_score >= 67:
        rec_badge = "GREEN — PRIMED / OPTIMAL"
    elif recovery_score >= 34:
        rec_badge = "YELLOW — ADEQUATE"
    else:
        rec_badge = "RED — REST REQUIRED"

    # 2. Strain Progress Bar
    bar_len = 20
    filled = int(round((min(day_strain, 21.0) / 21.0) * bar_len))
    strain_bar = "█" * filled + "░" * (bar_len - filled)

    if day_strain < target_strain_min:
        strain_status = "Under Target Bracket"
    elif day_strain <= target_strain_max:
        strain_status = "In Target Bracket"
    else:
        strain_status = "Overreaching (High Overload)"

    # 3. Health status badge
    if health_status == "NORMAL":
        health_badge = "ALL VITALS NORMAL [✓]"
    elif health_status == "WATCH":
        health_badge = "PHYSIOLOGICAL STRESS ELEVATED [! WATCH]"
    else:
        health_badge = "CRITICAL ANOMALY [! HIGH STRAIN / SICKNESS]"

    # 4. Sleep stages
    deep_sec = daily_sleep.get("deepSleepSeconds") or 0
    rem_sec = daily_sleep.get("remSleepSeconds") or 0
    light_sec = daily_sleep.get("lightSleepSeconds") or 0
    awake_sec = daily_sleep.get("awakeSleepSeconds") or 0
    actual_sec = sleep_actual_sec if sleep_actual_sec and sleep_actual_sec > 0 else 1

    deep_pct = round((deep_sec / actual_sec) * 100, 1)
    rem_pct = round((rem_sec / actual_sec) * 100, 1)
    light_pct = round((light_sec / actual_sec) * 100, 1)

    # 5. Peak HR from curve
    peak_hr_pt = max(strain_curve, key=lambda x: x.get("hr", 0)) if strain_curve else {"t": "--", "hr": 0}

    # 6. 4-Quadrant Balance
    if recovery_score >= 60 and day_strain >= 12.0:
        quadrant_title = "OPTIMAL OVERLOAD"
        quadrant_desc = "High Recovery + High Strain = Productive athletic adaptation"
    elif recovery_score < 60 and day_strain >= 12.0:
        quadrant_title = "OVERREACHING"
        quadrant_desc = "Low Recovery + High Strain = Elevated injury/fatigue risk"
    elif recovery_score >= 60 and day_strain < 12.0:
        quadrant_title = "RESTORING / PRIMED"
        quadrant_desc = "High Recovery + Moderate Strain = Tapering or deloading"
    else:
        quadrant_title = "DETRAINING / SYSTEMIC STRESS"
        quadrant_desc = "Low Recovery + Low Strain = Sickness or life stress"

    print("\n" + "=" * 78)
    print("       GARMIN RECOVERY & PRESCRIPTION ENGINE — MOBILE APP DASHBOARD")
    print("=" * 78)
    print(f" Target Date: {target_date}  |  User: {user_email}  |  Timezone: Europe/Brussels")
    print("=" * 78)

    print("\n┌────────────────────────────────────────────────────────────────────────────┐")
    print("│ TAB 1: TODAY (THE COMMAND CENTER)                                          │")
    print("├────────────────────────────────────────────────────────────────────────────┤")
    print(f"│  RECOVERY HERO: {recovery_score}%  [{rec_badge}]")
    print(f"│    • Driver: {driver}")
    print(f"│    • Baseline Confidence: {conf}")
    print("│")
    print("│  CARDIOVASCULAR STRAIN vs. TARGET BRACKET")
    print(f"│    • Day Strain:    {day_strain:.1f} / 21.0  [{strain_bar}]")
    print(f"│    • Target Window: {target_strain_min:.1f} – {target_strain_max:.1f}  ({strain_status})")
    print("│")
    print("│  SLEEP & REPAIR SNAPSHOT")
    print(f"│    • Actual Slept: {fmt_dur(sleep_actual_sec)}  |  Target Need: {last_night_target_min // 60}h {last_night_target_min % 60:02d}m  |  Eff: {sleep_efficiency or 0:.1f}%")
    print(f"│    • Accumulated Sleep Debt: {current_debt:+d} min")
    print("│")
    print(f"│  HEALTH MONITOR STATUS: {health_badge}")
    if alerts:
        for a in alerts:
            print(f"    ! {a}")
    if ai_briefing:
        print("│")
        print("│  AI MORNING COACHING BRIEFING")
        for line in textwrap.wrap(ai_briefing, width=70):
            print(f"│    {line}")
    print("└────────────────────────────────────────────────────────────────────────────┘")

    print("\n┌────────────────────────────────────────────────────────────────────────────┐")
    print("│ TAB 2: SLEEP & HEALTH (VITALS & READINESS)                                 │")
    print("├────────────────────────────────────────────────────────────────────────────┤")
    print("│  TONIGHT'S SLEEP TARGET PRESCRIPTION")
    print(f"│    • Prescribed Target: {target_tonight_min // 60}h {target_tonight_min % 60:02d}m")
    print(f"│    • Equation: {sleep_equation_str}")
    print(f"│    • Recommended Lights-Out Bedtime: {bedtime_str} (for 07:00 wake, 15m latency)")
    print("│")
    print("│  SLEEP ARCHITECTURE & STAGING (Last Night)")
    print(f"│    • Actual Sleep: {fmt_dur(sleep_actual_sec)}  |  Time in Bed: {fmt_dur(sleep_bed_sec)}  |  Eff: {sleep_efficiency or 0:.1f}%")
    print(f"│    • Deep:  {fmt_dur(deep_sec):>7} ({deep_pct:4.1f}%)  [{'█' * int(deep_pct // 5):<12}]")
    print(f"│    • REM:   {fmt_dur(rem_sec):>7} ({rem_pct:4.1f}%)  [{'█' * int(rem_pct // 5):<12}]")
    print(f"│    • Light: {fmt_dur(light_sec):>7} ({light_pct:4.1f}%)  [{'█' * int(light_pct // 5):<12}]")
    if awake_sec > 0:
        print(f"│    • Awake: {fmt_dur(awake_sec):>7}")
    print(f"│    • Circadian Consistency: {circadian_consistency}%")
    print("│")
    print("│  PRE-SYMPTOMATIC HEALTH MONITOR (30-Day Baselines)")
    print("│    Metric           Last Night   30-Day Normal Envelope      Status        │")
    print("│    ─────────────────────────────────────────────────────────────────────── │")
    for key, name in [("hrv", "HRV (rMSSD)"), ("rhr", "Resting HR"), ("resp", "Respiration"), ("spo2", "Pulse Ox (SpO2)")]:
        info = vitals_stats.get(key, {})
        raw_val = info.get('val')
        val_str = f"{raw_val} {info.get('unit', '')}" if raw_val is not None else "--"
        low = info.get("low", 0.0)
        high = info.get("high", 0.0)
        env_str = f"{low:.1f} – {high:.1f} {info.get('unit', '')}"
        status_tag = "[ ! OUTLIER ]" if info.get("alert") else "[ NORMAL ✓ ]"
        print(f"│    {name:<16} {val_str:<12} {env_str:<27} {status_tag:<13} │")
    print("└────────────────────────────────────────────────────────────────────────────┘")

    print("\n┌────────────────────────────────────────────────────────────────────────────┐")
    print("│ TAB 3: ACTIVITIES & STRAIN (EXERTION & WORKOUTS)                           │")
    print("├────────────────────────────────────────────────────────────────────────────┤")
    print("│  24-HOUR CUMULATIVE CARDIOVASCULAR LOAD")
    print(f"│    • Day Strain: {day_strain:.1f} / 21.0  |  Peak HR: {peak_hr_pt.get('hr', '--')} bpm (at {peak_hr_pt.get('t', '--')})")
    print(f"│    • 96-Bucket 15m Curve: Synced to Supabase JSONB (Instant PWA render)")
    print("│")
    print(f"│  WORKOUT FEED ({len(activities_list)} recorded)")
    if not activities_list:
        print("│    (No discrete workouts recorded for this day)")
    for i, act in enumerate(activities_list, 1):
        name = act.get("name", "Workout")
        act_type = act.get("activity_type", "workout").capitalize()
        dist_km = (act.get("distance_m") or 0) / 1000.0
        dur_s = act.get("duration_sec") or 0
        cal = act.get("calories", 0)
        avg_h = act.get("avg_hr", "--")
        max_h = act.get("max_hr", "--")
        strain = act.get("workout_strain", 0.0)
        te = act.get("aerobic_te", "--")
        load = act.get("garmin_load", "--")
        pace_str = ""
        if dist_km > 0.2 and dur_s > 0:
            spk = dur_s / dist_km
            pace_str = f" | Pace: {int(spk // 60)}:{int(spk % 60):02d} /km"
        print(f"│   {i}. [{act_type}] {name}")
        print(f"│      • Duration: {fmt_dur(dur_s)} | Dist: {dist_km:.2f} km{pace_str} | Energy: {cal} kcal")
        print(f"│      • Heart Rate: Avg {avg_h} bpm | Max {max_h} bpm")
        print(f"│      • Standalone Workout Strain: {strain:.1f} / 21.0")
        print(f"│      • Garmin Training Effect: {te} (Aerobic) | EPOC Load: {load}")
    print("└────────────────────────────────────────────────────────────────────────────┘")

    print("\n┌────────────────────────────────────────────────────────────────────────────┐")
    print("│ TAB 4: TRENDS & INSIGHTS (PHYSIOLOGICAL ADAPTATION)                        │")
    print("├────────────────────────────────────────────────────────────────────────────┤")
    print("│  CARDIOVASCULAR BIOLOGICAL AGE (Jackson / HUNT Model)")
    if cardio_age_info.get("cardio_age") is not None:
        c_age = cardio_age_info["chrono_age"]
        b_age = cardio_age_info["cardio_age"]
        diff = round(c_age - b_age, 1)
        sign = "-" if diff > 0 else "+"
        word = "years younger" if diff > 0 else "years older"
        peak_tag = " (Optimal Biological Peak)" if b_age <= 18.0 and c_age >= 18 else ""
        print(f"│    • Chronological Calendar Age: {c_age} yrs  |  Garmin VO2 Max: {cardio_age_info.get('vo2_max', '--')} ml/kg/min")
        print(f"│    • Baseline Sleeping RHR: {cardio_age_info.get('rhr', '--')} bpm")
        print(f"│    • Biological Cardiovascular Age: {b_age:.1f} yrs ({sign}{abs(diff):.1f} {word}{peak_tag}) ★")
    else:
        print("│    • Insufficient VO2 Max / baseline data to compute cardiovascular age.")
    print("│")
    print("│  STRAIN vs. RECOVERY BALANCE")
    print(f"│    • Current Quadrant: [ {quadrant_title} ]")
    print(f"│      ({quadrant_desc})")
    print("│")
    print("│  HABIT IMPACT ANALYSIS (60-Day Journal Insights)")
    if habit_correlations:
        for h in habit_correlations:
            sign_h = "+" if h["delta_hrv"] >= 0 else ""
            sign_r = "+" if h["delta_rhr"] >= 0 else ""
            print(f"│    • {h['label']:<24}: ΔHRV {sign_h}{h['delta_hrv']:4.1f} ms  |  ΔRHR {sign_r}{h['delta_rhr']:4.1f} bpm  ({h['count']} logs)")
    else:
        print("│    • Insufficient habit journal entries (log at least 3 occurrences in the app to unlock).")
    print("└────────────────────────────────────────────────────────────────────────────┘")

    print("\n┌────────────────────────────────────────────────────────────────────────────┐")
    print("│ SYSTEM & SYNC DIAGNOSTICS                                                  │")
    print("├────────────────────────────────────────────────────────────────────────────┤")
    print(f"│  ✓ daily_summaries: UPSERT successful ({target_date})")
    print(f"│  ✓ activities: {len(activities_list)} record(s) synced")
    if cardio_age_info.get("vo2_max"):
        print(f"│  ✓ user_baselines: VO2 Max ({cardio_age_info['vo2_max']}) updated")
    print("└────────────────────────────────────────────────────────────────────────────┘\n")
