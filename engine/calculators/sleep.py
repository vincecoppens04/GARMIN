from datetime import date, datetime, timedelta, time
from typing import Optional, Any
from engine.config import USER_TIMEZONE

def calculate_sleep_ledger_and_bedtime(
    base_sleep_need_min: int,
    debt_payback_rate: float,
    prev_summary: Optional[dict[str, Any]],
    day_strain: float,
    target_date_str: str,
    target_wake_time: str = "07:00",
    sleep_latency_min: int = 15,
    deadband_min: int = 30,
    max_debt_ceiling_min: int = 120
) -> tuple[int, int, str, str]:
    """
    Smart acute sleep debt ledger with biological tolerance deadband:
    - Normal Night (within 30m of personal baseline): 0 new debt, existing debt decays.
    - Oversleeping (> personal baseline): Surplus actively reduces remaining debt.
    - Acute Deprivation (< personal baseline - 30m): Acute debt accumulates (capped at 120m).
    """
    if prev_summary:
        prev_debt = prev_summary.get("sleep_debt_min", 0)
        prev_actual_min = (prev_summary.get("sleep_actual_sec") or (base_sleep_need_min * 60)) // 60
        
        # Existing debt naturally decays with daily half-life
        decayed_debt = prev_debt * (1.0 - debt_payback_rate)
        
        effective_floor = base_sleep_need_min - deadband_min
        
        if prev_actual_min >= base_sleep_need_min:
            # Overslept personal baseline -> surplus actively reduces remaining debt
            surplus = prev_actual_min - base_sleep_need_min
            current_debt = max(0, int(round(decayed_debt - surplus)))
        elif prev_actual_min >= effective_floor:
            # Within natural biological variation (e.g. 6h 45m - 7h 15m) -> zero new debt
            current_debt = int(round(decayed_debt))
        else:
            # Acute deprivation below tolerance floor (e.g. night out or short sleep)
            acute_deficit = effective_floor - prev_actual_min
            current_debt = min(max_debt_ceiling_min, int(round(decayed_debt + acute_deficit)))
    else:
        current_debt = 0

    # Additional demand from today's strain (+4.8 mins per strain point above 10.0)
    strain_demand = int(max(0.0, (day_strain - 10.0) * 4.8))
    
    # Tonight's target sleep duration: Base + Strain + (Debt * Payback Rate)
    # Cap debt payback demand at +45m/night so sleep goals remain achievable
    debt_payback_demand = int(min(45, round(current_debt * debt_payback_rate)))
    target_sleep_min = base_sleep_need_min + strain_demand + debt_payback_demand

    # Target tomorrow morning's wake time relative to target_date_str
    target_day = date.fromisoformat(target_date_str)
    tomorrow = target_day + timedelta(days=1)
    wake_h, wake_m = map(int, target_wake_time.split(":"))
    wake_dt = datetime.combine(tomorrow, time(wake_h, wake_m), tzinfo=USER_TIMEZONE)

    target_bedtime_dt = wake_dt - timedelta(minutes=(target_sleep_min + sleep_latency_min))
    recommended_bedtime_str = target_bedtime_dt.strftime("%H:%M")
    sleep_equation_str = f"{base_sleep_need_min // 60}h {base_sleep_need_min % 60:02d}m (Base) + {strain_demand}m (Strain Demand) + {debt_payback_demand}m (Debt Payback)"

    return current_debt, target_sleep_min, recommended_bedtime_str, sleep_equation_str

def calculate_circadian_consistency(
    recent_summaries: list[dict[str, Any]],
    today_onset: str | datetime | None,
    today_wake: str | datetime | None
) -> int:
    """
    Computes circadian consistency % (0-100) based on rolling standard deviation
    of sleep onset and wake times relative to midnight over trailing 7 days.
    """
    onsets_min = []
    wakes_min = []

    records = []
    for r in recent_summaries[:6]:
        if r.get("sleep_onset") and r.get("sleep_wake"):
            records.append((r["sleep_onset"], r["sleep_wake"]))
    if today_onset and today_wake:
        records.append((today_onset, today_wake))

    if len(records) < 2:
        return 85  # Default baseline for cold start

    for onset_val, wake_val in records:
        try:
            if not onset_val or not wake_val:
                continue
            onset_dt = onset_val if isinstance(onset_val, datetime) else datetime.fromisoformat(str(onset_val)).astimezone(USER_TIMEZONE)
            wake_dt = wake_val if isinstance(wake_val, datetime) else datetime.fromisoformat(str(wake_val)).astimezone(USER_TIMEZONE)

            onset_m = (onset_dt.hour - 24) * 60 + onset_dt.minute if onset_dt.hour >= 12 else onset_dt.hour * 60 + onset_dt.minute
            wake_m = (wake_dt.hour - 24) * 60 + wake_dt.minute if wake_dt.hour >= 18 else wake_dt.hour * 60 + wake_dt.minute

            onsets_min.append(onset_m)
            wakes_min.append(wake_m)
        except Exception:
            continue

    if len(onsets_min) < 2:
        return 85

    try:
        mu_onset = sum(onsets_min) / len(onsets_min)
        std_onset = (sum((x - mu_onset) ** 2 for x in onsets_min) / len(onsets_min)) ** 0.5

        mu_wake = sum(wakes_min) / len(wakes_min)
        std_wake = (sum((x - mu_wake) ** 2 for x in wakes_min) / len(wakes_min)) ** 0.5

        sigma_total = (std_onset + std_wake) / 2.0
        consistency = max(0, min(100, round(100.0 - max(0.0, sigma_total - 15.0) * 1.5)))
        return int(consistency)
    except Exception:
        return 85

def calculate_sleep_restoration_and_restlessness(daily_sleep: dict[str, Any], sleep_raw: dict[str, Any]) -> dict[str, Any]:
    """
    Sleep Restoration Ratio & Restlessness Index.
    Evaluates deep + REM restorative sleep proportions against clinical athletic baselines.
    """
    actual_sec = daily_sleep.get("sleepTimeSeconds") or 0
    deep_sec = daily_sleep.get("deepSleepSeconds") or 0
    rem_sec = daily_sleep.get("remSleepSeconds") or 0
    light_sec = daily_sleep.get("lightSleepSeconds") or max(0, actual_sec - deep_sec - rem_sec)
    awake_sec = daily_sleep.get("awakeSleepSeconds") or 0
    
    if actual_sec <= 0:
        return {
            "restoration_pct": None,
            "target_range": "40–50%",
            "is_optimal": False,
            "restlessness_index": None,
            "restless_moments": None,
            "awake_min": None,
            "sleep_stages": None
        }

    restless_count = sleep_raw.get("restlessMomentsCount")
    if restless_count is None:
        movements = sleep_raw.get("sleepMovement") or []
        restless_count = len(movements)

    restoration_pct = round(((deep_sec + rem_sec) / actual_sec) * 100, 1)
    sleep_hours = actual_sec / 3600.0
    awake_min = awake_sec / 60.0
    
    restlessness_index = round((awake_min + (restless_count or 0)) / sleep_hours, 1)

    return {
        "restoration_pct": restoration_pct,
        "target_range": "40–50%",
        "is_optimal": 40.0 <= restoration_pct <= 55.0,
        "restlessness_index": restlessness_index,
        "restless_moments": restless_count or 0,
        "awake_min": round(awake_min, 1),
        "sleep_stages": {
            "deep_sec": deep_sec,
            "rem_sec": rem_sec,
            "light_sec": light_sec,
            "awake_sec": awake_sec
        }
    }

def calculate_social_jetlag(history: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Social Jetlag Calculator.
    Measures circadian phase disruption between workdays and free days (MSF vs MSW).
    Standard chronobiology formulation (Wittmann & Roenneberg):
    Midpoint of Sleep (MS) = onset + (wake - onset)/2.
    """
    weekday_midpoints = []
    weekend_midpoints = []

    for rec in history:
        date_str = rec.get("date")
        onset_val = rec.get("sleep_onset")
        wake_val = rec.get("sleep_wake")
        actual_sec = rec.get("sleep_actual_sec") or 0
        bed_sec = rec.get("sleep_bed_sec") or actual_sec

        if not date_str or not onset_val:
            continue
        try:
            d = date.fromisoformat(date_str)
            
            # Parse onset into USER_TIMEZONE
            if isinstance(onset_val, datetime):
                onset_dt = onset_val.astimezone(USER_TIMEZONE)
            else:
                onset_dt = datetime.fromisoformat(str(onset_val))
                if onset_dt.tzinfo is None:
                    onset_dt = onset_dt.replace(tzinfo=USER_TIMEZONE)
                else:
                    onset_dt = onset_dt.astimezone(USER_TIMEZONE)

            # Determine sleep midpoint
            if wake_val:
                if isinstance(wake_val, datetime):
                    wake_dt = wake_val.astimezone(USER_TIMEZONE)
                else:
                    wake_dt = datetime.fromisoformat(str(wake_val))
                    if wake_dt.tzinfo is None:
                        wake_dt = wake_dt.replace(tzinfo=USER_TIMEZONE)
                    else:
                        wake_dt = wake_dt.astimezone(USER_TIMEZONE)
                midpoint_dt = onset_dt + (wake_dt - onset_dt) / 2
            elif bed_sec and bed_sec > 0:
                midpoint_dt = onset_dt + timedelta(seconds=bed_sec / 2.0)
            elif actual_sec and actual_sec > 0:
                midpoint_dt = onset_dt + timedelta(seconds=actual_sec / 2.0)
            else:
                continue

            # Circular minutes relative to 12:00 PM (noon) to avoid midnight wrap discontinuities
            h = midpoint_dt.hour
            m = midpoint_dt.minute
            rel_min = (h - 12) * 60 + m if h >= 12 else (h + 12) * 60 + m

            if d.weekday() in (5, 6):
                weekend_midpoints.append(rel_min)
            else:
                weekday_midpoints.append(rel_min)
        except Exception:
            continue

    def rel_to_str(rel_val):
        h = int((rel_val - 720) // 60) if rel_val >= 720 else int((rel_val + 720) // 60)
        m = int((rel_val - 720) % 60) if rel_val >= 720 else int((rel_val + 720) % 60)
        return f"{h:02d}:{m:02d}"

    if not weekday_midpoints or not weekend_midpoints:
        if weekday_midpoints and not weekend_midpoints:
            mean_wd = sum(weekday_midpoints) / len(weekday_midpoints)
            return {
                "social_jetlag_min": 18,
                "tier": "Synchronized (Optimal)",
                "status": "SYNCHRONIZED",
                "weekday_mean_str": rel_to_str(mean_wd),
                "weekend_mean_str": rel_to_str(mean_wd + 18),
                "note": "Provisional (Awaiting weekend sync)"
            }
        return {"social_jetlag_min": None, "tier": "NO DATA", "status": "NO_DATA", "weekday_mean_str": "--:--", "weekend_mean_str": "--:--"}

    mean_weekend_rel = sum(weekend_midpoints) / len(weekend_midpoints)
    mean_weekday_rel = sum(weekday_midpoints) / len(weekday_midpoints)
    diff = round(abs(mean_weekend_rel - mean_weekday_rel))

    if diff <= 30:
        tier = "Synchronized (Optimal)"
        key = "SYNCHRONIZED"
    elif diff <= 60:
        tier = "Moderate Shift"
        key = "MODERATE"
    else:
        tier = "Circadian Jetlag"
        key = "JETLAG"

    return {
        "social_jetlag_min": diff,
        "tier": tier,
        "status": key,
        "weekday_mean_str": rel_to_str(mean_weekday_rel),
        "weekend_mean_str": rel_to_str(mean_weekend_rel)
    }

def calculate_circadian_windows(wake_time_str: str = "07:00", bedtime_str: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Personalized Chronotype & Circadian Performance Windows.
    Generates biological timing recommendations aligned with lights-out and wake routines.
    """
    try:
        parts = wake_time_str.split(":")
        wh, wm = int(parts[0]), int(parts[1])
    except Exception:
        wh, wm = 7, 0

    base = datetime(2026, 1, 1, wh, wm)
    def fmt_w(start_min, end_min):
        s = base + timedelta(minutes=start_min)
        e = base + timedelta(minutes=end_min)
        return f"{s.strftime('%H:%M')} – {e.strftime('%H:%M')}"

    # Calculate caffeine cutoff directly anchored to lights-out bedtime: Bedtime - 10 hours
    if bedtime_str:
        try:
            bh, bm = map(int, bedtime_str.split(":"))
            bed_dt = datetime(2026, 1, 2 if bh < wh else 1, bh, bm)
            caff_cutoff_dt = bed_dt - timedelta(hours=10)
            caff_time_str = caff_cutoff_dt.strftime('%H:%M')
        except Exception:
            caff_time_str = (base + timedelta(hours=6)).strftime('%H:%M')
    else:
        # Fallback assuming ~16h waking day: wake + 6h = bedtime - 10h
        caff_time_str = (base + timedelta(hours=6)).strftime('%H:%M')

    return [
        {
            "id": "cortisol",
            "name": "Morning Cortisol & Sunlight Exposure",
            "time_window": fmt_w(0, 45),
            "directive": "Get direct sunlight within 45m of waking to anchor circadian clock.",
            "color": "cyan"
        },
        {
            "id": "cognitive",
            "name": "Peak Cognitive Alertness Window",
            "time_window": fmt_w(120, 270),
            "directive": "Prefrontal cortex alertness optimal. Prime focus for strategic deep work.",
            "color": "green"
        },
        {
            "id": "physical",
            "name": "Peak Strength & VO2 Max Window",
            "time_window": fmt_w(540, 690),
            "directive": "Core body temperature and neuromuscular coordination at physical peak.",
            "color": "yellow"
        },
        {
            "id": "caffeine",
            "name": "Caffeine Clearance Cutoff",
            "time_window": caff_time_str,
            "directive": "Enforces ~10h clearance before lights out to prevent adenosine binding inhibition.",
            "color": "rose"
        },
        {
            "id": "melatonin",
            "name": "Endogenous Melatonin Onset Window",
            "time_window": fmt_w(840, 900),
            "directive": "Dim ambient lights, eliminate blue screens, begin wind-down routine.",
            "color": "purple"
        }
    ]
