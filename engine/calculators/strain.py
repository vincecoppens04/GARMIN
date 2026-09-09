import math
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Any
from engine.config import USER_TIMEZONE

def calculate_activity_strain(
    avg_hr: Optional[float],
    duration_sec: int,
    rhr: int,
    max_hr: int,
    sex: str = "male"
) -> float:
    """
    Computes standalone cardiovascular strain (0-21) for a single workout window.
    Uses Banister TRIMP exponential formulation calibrated to the 0-21 scale.
    """
    if not avg_hr or duration_sec <= 0:
        return 0.0

    hr_reserve = max(20, max_hr - rhr)
    y = max(0.0, min(1.0, (avg_hr - rhr) / hr_reserve))
    if y < 0.20:
        return 0.0

    dt_min = duration_sec / 60.0
    b_coeff = 1.92 if sex.lower() == "male" else 1.67
    a_coeff = 0.64 if sex.lower() == "male" else 0.86

    trimp = dt_min * y * a_coeff * math.exp(b_coeff * y)
    strain = round(21.0 * (1.0 - math.exp(-0.0055 * trimp)), 1)
    return min(21.0, strain)

def calculate_strain_and_curve(
    hr_data: dict[str, Any], 
    rhr: int, 
    max_hr: int, 
    target_date_str: str,
    sex: str = "male"
) -> tuple[float, list[dict[str, Any]]]:
    """
    Computes cumulative cardio strain using continuous Banister formulation
    with an exertion threshold (y >= 0.15) and builds an exact 96-bucket 
    15-minute curve in local time.
    """
    hr_values = hr_data.get("heartRateValues", []) if isinstance(hr_data, dict) else []
    if not hr_values:
        return 0.0, []

    # Filter nulls and sort chronologically
    valid_points = sorted(
        [p for p in hr_values if len(p) >= 2 and p[1] is not None],
        key=lambda x: x[0]
    )
    if not valid_points:
        return 0.0, []

    hr_reserve = max(20, max_hr - rhr)
    total_trimp = 0.0

    # Sex-specific Banister coefficients
    b_coeff = 1.92 if sex.lower() == "male" else 1.67
    a_coeff = 0.64 if sex.lower() == "male" else 0.86

    # Setup 96 fifteen-minute buckets (00:00 to 23:45 local time)
    buckets = [{"hr_sum": 0, "count": 0, "cum_strain": 0.0} for _ in range(96)]
    
    for i in range(len(valid_points)):
        ts_ms, bpm = valid_points[i]
        
        # Calculate Banister TRIMP contribution
        if i > 0:
            prev_ts, _ = valid_points[i - 1]
            dt_min = (ts_ms - prev_ts) / 60000.0
            # Clamp gaps (e.g. watch off wrist) to max 5 mins
            if 0 < dt_min <= 5.0:
                y = max(0.0, min(1.0, (bpm - rhr) / hr_reserve))
                # Cardiac exertion above 15% of HR reserve accumulates strain
                if y >= 0.15:
                    delta_trimp = dt_min * y * a_coeff * math.exp(b_coeff * y)
                    total_trimp += delta_trimp

        # Local Timezone Conversion for Bucketing
        dt_local = datetime.fromtimestamp(ts_ms / 1000.0, tz=ZoneInfo("UTC")).astimezone(USER_TIMEZONE)
        
        # Ensure data point belongs to target date in local time
        if dt_local.strftime("%Y-%m-%d") == target_date_str:
            b_idx = (dt_local.hour * 60 + dt_local.minute) // 15
            if 0 <= b_idx < 96:
                buckets[b_idx]["hr_sum"] += bpm
                buckets[b_idx]["count"] += 1
                current_strain = round(21.0 * (1.0 - math.exp(-0.0055 * total_trimp)), 1)
                buckets[b_idx]["cum_strain"] = min(21.0, current_strain)

    # Format complete 96-bucket curve with forward-fill for smooth presentation
    strain_curve_96 = []
    last_known_hr = rhr
    last_known_strain = 0.0

    for idx in range(96):
        hh = (idx * 15) // 60
        mm = (idx * 15) % 60
        t_str = f"{hh:02d}:{mm:02d}"

        if buckets[idx]["count"] > 0:
            last_known_hr = int(buckets[idx]["hr_sum"] / buckets[idx]["count"])
            last_known_strain = buckets[idx]["cum_strain"]
        
        strain_curve_96.append({
            "t": t_str,
            "hr": last_known_hr,
            "cum_strain": round(last_known_strain, 1)
        })

    final_day_strain = round(21.0 * (1.0 - math.exp(-0.0055 * total_trimp)), 1)
    return min(21.0, final_day_strain), strain_curve_96

def check_hr_sync_freshness(hr_raw: Optional[dict[str, Any]], target_date_str: str) -> dict[str, Any]:
    """
    Checks if today's heart rate data from Garmin is up to date (synced within last 90 minutes).
    Returns dict with is_today, is_stale, last_sync_time, and age_min.
    """
    now = datetime.now(USER_TIMEZONE)
    today_iso = now.date().isoformat()
    if target_date_str != today_iso:
        return {"is_today": False, "is_stale": False, "last_sync_time": None, "age_min": 0}

    hr_values = hr_raw.get("heartRateValues", []) if isinstance(hr_raw, dict) else []
    valid = [p for p in hr_values if len(p) >= 2 and p[1] is not None]
    if not valid:
        return {
            "is_today": True,
            "is_stale": True,
            "last_sync_time": None,
            "age_min": 9999,
        }

    last_ts_ms = max(p[0] for p in valid)
    last_dt = datetime.fromtimestamp(last_ts_ms / 1000.0, tz=ZoneInfo("UTC")).astimezone(USER_TIMEZONE)
    age_min = max(0.0, (now - last_dt).total_seconds() / 60.0)
    is_stale = (age_min > 90.0)
    time_str = last_dt.strftime("%H:%M")

    return {
        "is_today": True,
        "is_stale": is_stale,
        "last_sync_time": time_str,
        "age_min": round(age_min, 1),
    }

def calculate_target_strain_window(recovery_score: int, health_status: str) -> tuple[float, float]:
    """
    Saturating target curve: Target = 21 * (Recovery / 100) ** 0.65.
    Forces active recovery if sickness or elevated stress is detected.
    """
    if health_status == "HIGH_STRAIN_SICKNESS":
        return 0.0, 6.0
    elif health_status == "WATCH":
        return 4.0, 9.0

    midpoint = round(21.0 * ((recovery_score / 100.0) ** 0.65), 1)
    return max(0.0, round(midpoint - 1.5, 1)), min(21.0, round(midpoint + 1.5, 1))

def calculate_chronic_strain_debt(history_7d: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Cumulative Chronic Strain Debt (Overtraining Runway).
    Tracks acute overload accumulating above daily optimal tolerance ceilings.
    """
    runway_debt = 0.0
    excess_days_count = 0
    for h in history_7d:
        actual = float(h.get("day_strain") or 0)
        target_max = float(h.get("target_strain_max") or 14.0)
        diff = actual - target_max
        if diff > 0:
            runway_debt += diff
            excess_days_count += 1

    runway_debt = round(runway_debt, 1)
    mandatory_rest_alert = (runway_debt > 6.0 and excess_days_count >= 4)

    return {
        "runway_debt": runway_debt,
        "excess_days_count": excess_days_count,
        "mandatory_rest_alert": mandatory_rest_alert,
        "status": "DELOAD_RECOMMENDED" if mandatory_rest_alert else ("ACCUMULATING" if runway_debt > 3.0 else "OPTIMAL")
    }

def calculate_acwr(history_28d: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Acute-to-Chronic Workload Ratio (ACWR).
    Compares 7-day acute workload against 28-day chronic training base.
    """
    valid_strains = [float(d.get("day_strain")) for d in history_28d if d.get("day_strain") is not None]
    if len(valid_strains) < 7:
        return {
            "acwr": None,
            "acute_load": round(sum(valid_strains) / len(valid_strains), 1) if valid_strains else None,
            "chronic_load": None,
            "zone": "Awaiting 7+ days of strain data",
            "zone_key": "NO_DATA",
            "color": "zinc"
        }

    acute_load = sum(valid_strains[:7]) / 7.0
    chronic_slice = valid_strains[:28]
    chronic_load = sum(chronic_slice) / float(len(chronic_slice))
    acwr = round(acute_load / max(0.5, chronic_load), 2)

    if acwr < 0.80:
        zone = "Under-training / Fitness Loss"
        zone_key = "UNDER"
        color = "cyan"
    elif acwr <= 1.30:
        zone = "The Sweet Spot (Optimal Adaptation)"
        zone_key = "SWEET_SPOT"
        color = "green"
    elif acwr <= 1.50:
        zone = "High Overload Window"
        zone_key = "OVERLOAD"
        color = "yellow"
    else:
        zone = "Danger Zone (High Injury Risk)"
        zone_key = "DANGER"
        color = "rose"

    return {
        "acwr": acwr,
        "acute_load": round(acute_load, 1),
        "chronic_load": round(chronic_load, 1),
        "zone": zone,
        "zone_key": zone_key,
        "color": color
    }

def calculate_training_monotony(history_7d: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Training Monotony & Strain Index (Foster’s Model).
    Monotony = Mean Strain / SD Strain. High monotony indicates excessive plateauing.
    """
    strains = [float(d.get("day_strain")) for d in history_7d if d.get("day_strain") is not None]
    if len(strains) < 3:
        return {
            "mean_strain": None,
            "sd_strain": None,
            "training_monotony": None,
            "strain_index": None,
            "is_monotonous": False,
            "status": "Awaiting 3+ days of strain data"
        }

    mean_s = sum(strains) / len(strains)
    var = sum((s - mean_s) ** 2 for s in strains) / len(strains)
    sd = max(0.5, math.sqrt(var))
    
    monotony = round(mean_s / sd, 2)
    strain_index = round(mean_s * monotony * 7, 1)
    is_monotonous = (monotony > 2.0 and mean_s > 11.0)

    return {
        "mean_strain": round(mean_s, 1),
        "sd_strain": round(sd, 1),
        "training_monotony": monotony,
        "strain_index": strain_index,
        "is_monotonous": is_monotonous,
        "status": "ALERT: Lacks Workout Variation" if is_monotonous else "BALANCED: Healthy Load Variance"
    }

def calculate_load_polarization(activities_14d: list[dict[str, Any]], max_hr: int, rhr: int) -> dict[str, Any]:
    """
    Cardiovascular Load Polarization (Seiler 3-Zone 80/20 Breakdown).
    Low (Z1-2) vs Moderate/Threshold (Z3) vs High (Z4-5).
    """
    z_low, z_mod, z_high = 0.0, 0.0, 0.0

    for act in activities_14d:
        z1 = float(act.get("hrTimeInZone_1") or 0)
        z2 = float(act.get("hrTimeInZone_2") or 0)
        z3 = float(act.get("hrTimeInZone_3") or 0)
        z4 = float(act.get("hrTimeInZone_4") or 0)
        z5 = float(act.get("hrTimeInZone_5") or 0)
        
        z_low += (z1 + z2) / 60.0
        z_mod += (z3) / 60.0
        z_high += (z4 + z5) / 60.0

    total = z_low + z_mod + z_high
    if total <= 0:
        return {
            "total_min": 0,
            "pct_low": None,
            "pct_mod": None,
            "pct_high": None,
            "target": "80% Low (Z1-2) / 10% Mod (Z3) / 10% High (Z4-5)",
            "is_polarized": None,
            "status": "Awaiting HR zone activities"
        }

    pct_low = round((z_low / total) * 100, 1)
    pct_mod = round((z_mod / total) * 100, 1)
    pct_high = round((z_high / total) * 100, 1)
    is_polarized = (pct_low >= 75.0 and pct_mod <= 12.0)

    return {
        "total_min": round(total, 1),
        "pct_low": pct_low,
        "pct_mod": pct_mod,
        "pct_high": pct_high,
        "target": "80% Low (Z1-2) / 10% Mod (Z3) / 10% High (Z4-5)",
        "is_polarized": is_polarized,
        "status": "POLARIZED (80/20 Optimal)" if is_polarized else "TOO MUCH THRESHOLD (Zone 3 Black Hole)"
    }

def calculate_sport_strain_penalties(activities_history: list[dict[str, Any]], daily_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Next-Day Readiness Impact per Sport Type.
    Evaluates eccentric load & recovery penalty associated with running vs cycling vs strength.
    """
    daily_by_date = {d["date"]: d for d in daily_history if d.get("date")}
    sport_data = {"running": [], "cycling": [], "swimming": [], "strength": []}

    for act in activities_history:
        act_date = act.get("date")
        act_type = (act.get("activity_type") or "").lower()
        strain = float(act.get("workout_strain") or 0)
        if not act_date or strain < 3.0:
            continue
        try:
            next_date = (date.fromisoformat(act_date) + timedelta(days=1)).isoformat()
            if next_date in daily_by_date:
                next_rec = float(daily_by_date[next_date].get("recovery_score") or 60)
                s_key = "running" if "run" in act_type else ("cycling" if "cycl" in act_type or "bike" in act_type else ("swimming" if "swim" in act_type else "strength"))
                penalty = (70.0 - next_rec) / max(1.0, strain)
                sport_data[s_key].append(penalty)
        except Exception:
            continue

    benchmarks = {
        "running": 1.85,
        "strength": 1.42,
        "cycling": 0.88,
        "swimming": 0.68,
    }

    results = []
    labels = {
        "running": "Running (Impact)",
        "strength": "Strength & CNS",
        "cycling": "Cycling (Non-Impact)",
        "swimming": "Swimming (Whole Body)"
    }
    for k, name in labels.items():
        vals = sport_data.get(k) or []
        if vals:
            avg_penalty = round(sum(vals) / len(vals), 2)
            is_bench = False
        else:
            avg_penalty = benchmarks[k]
            is_bench = True
        results.append({
            "sport_key": k,
            "label": name,
            "penalty_per_strain": avg_penalty,
            "sample_count": len(vals),
            "is_benchmark": is_bench
        })

    return results
