from datetime import datetime
from typing import Optional, Any

def calculate_activity_metabolic_and_recovery(
    act: dict[str, Any],
    max_hr: int = 202,
    rhr: int = 45,
    stress_raw: Optional[dict[str, Any]] = None,
    hr_raw: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Heart Rate Recovery (HRR), Glycogen Depletion & Stress Recovery Index.
    Extracts or derives HR drop (HRR 60s & 120s), calculates carb refuel target,
    and measures autonomic recovery duration.
    """
    calories = float(act.get("calories") or 0)
    dur_total = float(act.get("duration") or act.get("duration_sec") or 0)

    # Glycogen Depletion
    z3 = float(act.get("hrTimeInZone_3") or 0)
    z4 = float(act.get("hrTimeInZone_4") or 0)
    z5 = float(act.get("hrTimeInZone_5") or 0)
    f_glycolytic = (z3 + z4 + z5) / max(1.0, dur_total) if dur_total > 0 else 0.40

    glycogen_kcal = int(round(calories * (0.35 + 0.60 * f_glycolytic)))
    carb_refuel_g = int(round(glycogen_kcal / 4.0))

    # HR Recovery (HRR)
    avg_hr = float(act.get("averageHR") or act.get("avg_hr") or 140)
    peak_hr = float(act.get("maxHR") or act.get("max_hr") or 165)
    
    hrr_60s = act.get("heartRateRecovery") or act.get("hrr_60s")
    hrr_120s = act.get("hrr_120s")

    # If not explicitly recorded as a field, derive from continuous optical HR stream
    if hrr_60s is None and hr_raw and isinstance(hr_raw, dict):
        pts = hr_raw.get("heartRateValues") or []
        t_start = act.get("beginTimestamp")
        if not t_start and act.get("startTimeGMT"):
            try:
                t_start = datetime.fromisoformat(act["startTimeGMT"].replace("Z", "+00:00")).timestamp() * 1000
            except Exception:
                pass
        dur_s = float(act.get("elapsedDuration") or act.get("duration") or 0)
        if t_start and dur_s and pts and avg_hr:
            t_end = t_start + (dur_s * 1000)
            # Find ending/peak HR in the final 3 minutes of exercise
            pre_pts = [p for p in pts if (t_end - 180000) <= p[0] <= t_end and p[1] is not None]
            end_hr = max([p[1] for p in pre_pts]) if pre_pts else peak_hr or avg_hr
            
            # Find post-workout HR points within 20s - 240s of stopping
            post_pts = [p for p in pts if t_end < p[0] <= (t_end + 300000) and p[1] is not None]
            
            hr_60, hr_120 = None, None
            for p in post_pts:
                diff = (p[0] - t_end) / 1000.0
                if 20 <= diff <= 90 and hr_60 is None:
                    hr_60 = p[1]
                if 70 <= diff <= 190 and hr_120 is None:
                    hr_120 = p[1]
            
            if end_hr:
                if hr_60 is not None:
                    hrr_60s = max(0, int(round(end_hr - hr_60)))
                if hr_120 is not None:
                    hrr_120s = max(0, int(round(end_hr - hr_120)))
                # If 60s wasn't sampled exactly at 60s but 120s was, approximate 60s drop as ~60% of 120s
                if hrr_60s is None and hrr_120s is not None:
                    hrr_60s = int(round(hrr_120s * 0.60))

    if hrr_120s is not None or hrr_60s is not None:
        score = hrr_120s if hrr_120s is not None else (hrr_60s * 1.6)
        if score >= 30:
            hrr_bench = "Optimal (High Vagal Recovery)"
        elif score >= 18:
            hrr_bench = "Moderate (Normal Reactivation)"
        else:
            hrr_bench = "Suppressed (Dehydration / CNS Fatigue)"
    else:
        hrr_bench = None

    # Stress Resistance Index (post-workout recovery duration in minutes)
    stress_recovery_min = None
    if stress_raw and isinstance(stress_raw, dict):
        stress_pts = stress_raw.get("stressValuesArray") or []
        start_gmt = act.get("startTimeGMT")
        if start_gmt and stress_pts:
            try:
                t_end = datetime.fromisoformat(start_gmt.replace("Z", "+00:00")).timestamp() * 1000 + (dur_total * 1000)
                post_pts = [p for p in stress_pts if len(p) >= 2 and p[0] >= t_end and p[1] > 0]
                for i in range(len(post_pts) - 1):
                    if post_pts[i][1] < 25 and post_pts[i+1][1] < 25:
                        stress_recovery_min = max(5, int((post_pts[i][0] - t_end) / 60000))
                        break
            except Exception:
                pass

    return {
        "glycogen_depleted_kcal": glycogen_kcal,
        "carb_refuel_target_g": carb_refuel_g,
        "f_glycolytic": round(f_glycolytic, 2),
        "hrr_60s": hrr_60s,
        "hrr_120s": hrr_120s,
        "hrr_benchmark": hrr_bench,
        "stress_recovery_min": stress_recovery_min
    }

def calculate_alcohol_latency(
    sleep_raw: dict[str, Any],
    habit_entry: Optional[dict[str, Any]],
    baseline_rhr: float
) -> dict[str, Any]:
    """
    Alcohol Clearance & Sympathetic Delay Latency.
    Computes time required for overnight HR to drop to within baseline RHR + 2 bpm.
    """
    had_alcohol = bool(habit_entry and habit_entry.get("alcohol"))
    sleep_hr_list = sleep_raw.get("sleepHeartRate") or [] if isinstance(sleep_raw, dict) else []
    valid_items = [p for p in sleep_hr_list if isinstance(p, dict) and p.get("value") is not None and p.get("startGMT")]
    
    if not had_alcohol:
        return {
            "had_alcohol": False,
            "latency_hr": 1.2,
            "delta_latency_hr": 0.0,
            "status": "CLEAN",
            "desc": "Zero alcohol detected. Autonomic nervous system stabilized within normal physiological latency (~1.2h) with zero sympathetic penalty."
        }

    if not valid_items:
        return {
            "had_alcohol": True,
            "latency_hr": 4.5,
            "delta_latency_hr": 3.0,
            "status": "AWAITING_TELEMETRY",
            "desc": "Alcohol logged. Estimated sympathetic latency delay: +3.0 hours."
        }

    target_thresh = baseline_rhr + 2.0
    start_epoch = valid_items[0]["startGMT"]
    latency_ms = None

    streak = 0
    for item in valid_items:
        if item["value"] <= target_thresh:
            streak += 1
            if streak >= 6 and latency_ms is None:
                latency_ms = item["startGMT"] - start_epoch
                break
        else:
            streak = 0

    latency_hr = round((latency_ms / 3600000.0), 1) if latency_ms is not None else 5.5
    clean_baseline_latency = 1.2
    delta_latency = round(max(0.0, latency_hr - clean_baseline_latency), 1)

    return {
        "had_alcohol": True,
        "latency_hr": latency_hr,
        "delta_latency_hr": delta_latency,
        "status": "SYMPATHETIC_DELAY" if delta_latency > 1.0 else "CLEAN",
        "desc": f"Alcohol consumption delayed nocturnal parasympathetic stabilization by {delta_latency} hours past baseline."
    }

def calculate_caffeine_clearance(
    habit_entry: Optional[dict[str, Any]],
    bedtime_str: str = "23:00"
) -> dict[str, Any]:
    """
    Caffeine Half-Life Depletion Curve.
    Uses 5-hour physiological half-life to track adenosine receptor clearance before lights out.
    """
    had_late = bool(habit_entry and habit_entry.get("late_caffeine"))
    had_any = bool(habit_entry and habit_entry.get("any_caffeine"))

    if not had_any and not had_late:
        return {
            "active": False,
            "initial_dose_mg": 0,
            "intake_time": "None",
            "bedtime_time": bedtime_str,
            "remaining_mg_at_bedtime": 0.0,
            "exceeds_threshold": False,
            "curve_points": [{"t": f"{h:02d}:00", "mg": 0.0} for h in range(12)],
            "status": "CLEAR",
            "desc": "No caffeine logged today. Adenosine receptors unblocked, optimizing deep slow-wave stage 3/4 sleep."
        }

    c0 = 180 if (had_late and had_any) else (150 if had_late else 100)
    intake_hour = 15.5 if had_late else 11.0

    try:
        bh, bm = [int(x) for x in bedtime_str.split(":")]
        bedtime_hour = bh + (bm / 60.0)
    except Exception:
        bedtime_hour = 23.0

    delta_t = max(0.0, bedtime_hour - intake_hour)
    remaining_mg = round(c0 * ((0.5) ** (delta_t / 5.0)), 1)

    curve_points = []
    for h in range(13):
        t_h = intake_hour + h
        mg = round(c0 * ((0.5) ** (h / 5.0)), 1)
        h_mod = int(t_h % 24)
        curve_points.append({"t": f"{h_mod:02d}:00", "mg": mg})

    return {
        "active": True,
        "initial_dose_mg": c0,
        "intake_time": f"{int(intake_hour):02d}:{int((intake_hour%1)*60):02d}",
        "bedtime_time": bedtime_str,
        "remaining_mg_at_bedtime": remaining_mg,
        "exceeds_threshold": remaining_mg > 25.0,
        "curve_points": curve_points,
        "status": "EXCEEDS_THRESHOLD" if remaining_mg > 25.0 else "CLEAR",
        "desc": f"Residual caffeine ({remaining_mg}mg at lights-out) {'exceeds' if remaining_mg > 25.0 else 'clears'} the 25mg adenosine threshold."
    }
