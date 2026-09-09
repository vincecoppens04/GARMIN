import math
from typing import Optional, Any
from engine.config import norm_cdf

def calculate_recovery_and_health_stress(
    today_hrv: Optional[float],
    today_rhr: Optional[int],
    today_resp: Optional[float],
    today_spo2: Optional[float],
    sleep_actual_sec: Optional[int],
    last_night_target_min: int,
    history: list[dict[str, Any]]
) -> tuple[int, str, list[str], str, str, dict[str, Any]]:
    """
    Computes recovery score with dynamic weight re-normalization,
    and runs a multi-signal pre-symptomatic illness/stress evaluation.
    """
    alerts = []
    
    # 1. Extract historical baselines (up to 30 days)
    hrv_hist = [float(h["hrv_rmssd"]) for h in history if h.get("hrv_rmssd") is not None]
    rhr_hist = [float(h["rhr"]) for h in history if h.get("rhr") is not None]
    resp_hist = [float(h["resp_rate"]) for h in history if h.get("resp_rate") is not None]
    spo2_hist = [float(h["spo2"]) for h in history if h.get("spo2") is not None]

    # Tag baseline confidence
    n_records = len(hrv_hist)
    if n_records < 7:
        confidence = "PROVISIONAL (<7 days)"
    elif n_records < 14:
        confidence = "MODERATE (7-13 days)"
    else:
        confidence = "HIGH (14+ days)"

    # Compute Rolling Statistics with Minimum Variation Clamps
    mu_hrv = sum(hrv_hist) / len(hrv_hist) if hrv_hist else 60.0
    std_hrv = max(3.0, (sum((x - mu_hrv) ** 2 for x in hrv_hist) / len(hrv_hist)) ** 0.5) if len(hrv_hist) > 1 else 6.0

    mu_rhr = sum(rhr_hist) / len(rhr_hist) if rhr_hist else 50.0
    std_rhr = max(1.5, (sum((x - mu_rhr) ** 2 for x in rhr_hist) / len(rhr_hist)) ** 0.5) if len(rhr_hist) > 1 else 2.5

    mu_resp = sum(resp_hist) / len(resp_hist) if resp_hist else 14.0
    std_resp = max(0.6, (sum((x - mu_resp) ** 2 for x in resp_hist) / len(resp_hist)) ** 0.5) if len(resp_hist) > 1 else 0.8

    mu_spo2 = sum(spo2_hist) / len(spo2_hist) if spo2_hist else 96.0
    std_spo2 = max(1.0, (sum((x - mu_spo2) ** 2 for x in spo2_hist) / len(spo2_hist)) ** 0.5) if len(spo2_hist) > 1 else 1.2

    # 2. Anomaly Counter (Multi-signal illness detection)
    stress_signals = 0
    if today_hrv is not None and today_hrv < (mu_hrv - 1.5 * std_hrv):
        alerts.append("Suppressed HRV")
        stress_signals += 1
    if today_rhr is not None and today_rhr > (mu_rhr + 1.5 * std_rhr):
        alerts.append("Elevated RHR")
        stress_signals += 1
    if today_resp is not None and today_resp > (mu_resp + 1.5 * std_resp):
        alerts.append("Elevated Respiration")
        stress_signals += 1
    if today_spo2 is not None and today_spo2 < (mu_spo2 - 1.5 * std_spo2):
        alerts.append("Depressed SpO2")
        stress_signals += 1

    # Illness Classification
    if stress_signals >= 3:
        health_status = "HIGH_STRAIN_SICKNESS"
        alerts.insert(0, "CRITICAL: Multiple vital anomalies suggest infection or severe exhaustion")
    elif stress_signals >= 2:
        health_status = "WATCH"
        alerts.insert(0, "WATCH: Physiological stress elevated")
    else:
        health_status = "NORMAL"

    # 3. Dynamic Weight Re-normalization for Recovery
    # Calibrated CDF with +0.60 offset so that normal baseline (z=0) maps to ~73% (Solid Green),
    # mild post-workout dip (z=-0.5) maps to 54% (Yellow), and severe anomaly (z<=-1.5) drops into Red.
    components = []
    if today_hrv is not None:
        z_hrv = (today_hrv - mu_hrv) / std_hrv
        readiness_hrv = norm_cdf(z_hrv + 0.60)
        components.append(("hrv", readiness_hrv, 0.50))
    if today_rhr is not None:
        z_rhr = (mu_rhr - today_rhr) / std_rhr  # Lower RHR is better
        readiness_rhr = norm_cdf(z_rhr + 0.60)
        components.append(("rhr", readiness_rhr, 0.30))
    if sleep_actual_sec is not None and last_night_target_min > 0:
        sleep_ratio = min(1.0, (sleep_actual_sec / 60.0) / last_night_target_min)
        components.append(("sleep", sleep_ratio, 0.20))

    if not components:
        recovery_score = 50  # Neutral fallback if watch was off
    else:
        total_weight = sum(c[2] for c in components)
        normalized_score = sum(val * (weight / total_weight) for _, val, weight in components)
        raw_score = int(max(1, min(100, round(normalized_score * 100.0))))
        
        # Clinical overrides: enforce ceilings when health anomalies are detected
        if health_status == "HIGH_STRAIN_SICKNESS":
            recovery_score = min(33, raw_score)
        elif health_status == "WATCH":
            recovery_score = min(60, raw_score)
        else:
            recovery_score = raw_score

    # Recovery Driver String
    hrv_pct = int(((today_hrv - mu_hrv) / mu_hrv) * 100) if today_hrv and mu_hrv else 0
    sign = "+" if hrv_pct >= 0 else ""
    driver = f"HRV {sign}{hrv_pct}% vs 30d baseline | RHR {'elevated' if 'Elevated RHR' in alerts else 'stable'}"

    vitals_stats = {
        "hrv": {"val": today_hrv, "unit": "ms", "mean": mu_hrv, "std": std_hrv, "low": mu_hrv - 1.5 * std_hrv, "high": mu_hrv + 1.5 * std_hrv, "alert": "Suppressed HRV" in alerts},
        "rhr": {"val": today_rhr, "unit": "bpm", "mean": mu_rhr, "std": std_rhr, "low": mu_rhr - 1.5 * std_rhr, "high": mu_rhr + 1.5 * std_rhr, "alert": "Elevated RHR" in alerts},
        "resp": {"val": today_resp, "unit": "brpm", "mean": mu_resp, "std": std_resp, "low": mu_resp - 1.5 * std_resp, "high": mu_resp + 1.5 * std_resp, "alert": "Elevated Respiration" in alerts},
        "spo2": {"val": today_spo2, "unit": "%", "mean": mu_spo2, "std": std_spo2, "low": mu_spo2 - 1.5 * std_spo2, "high": mu_spo2 + 1.5 * std_spo2, "alert": "Depressed SpO2" in alerts},
    }

    return recovery_score, driver, alerts, health_status, confidence, vitals_stats

def calculate_workout_prescriber(recovery_score: float) -> dict[str, Any]:
    """
    HRV Autoregulated Workout Prescriber.
    Translates morning readiness into a tangible training stimulus directive.
    """
    if recovery_score >= 67:
        zone = "GREEN"
        directive = "Neuromuscular & High Glycolytic Power"
        focus = "Threshold intervals, maximum power sprints, heavy CNS strength lifts (>85% 1RM), or race pace efforts."
        modalities = ["VO2 Max Intervals", "Heavy Compound Lifts", "Anaerobic Repeats"]
    elif recovery_score >= 34:
        zone = "YELLOW"
        directive = "Aerobic Base & Muscular Endurance"
        focus = "Zone 2 base endurance, steady-state aerobic recovery, moderate hypertrophy (65–75% 1RM). Restrict cardiac output from crossing anaerobic threshold."
        modalities = ["Zone 2 Long Ride/Run", "Tempo Pace (<LT1)", "Hypertrophy 65-75%"]
    else:
        zone = "RED"
        directive = "Active Restorative & Parasympathetic Flow"
        focus = "Zone 1 walking, mobility/myofascial work, cold water immersion, or total physical rest."
        modalities = ["Zone 1 Recovery Walk", "Mobility / Yoga", "Full Nervous System Rest"]

    return {
        "zone": zone,
        "directive": directive,
        "focus": focus,
        "modalities": modalities,
    }

def calculate_immune_strain_index(
    today_hrv: Optional[float],
    today_rhr: Optional[float],
    today_resp: Optional[float],
    today_spo2: Optional[float],
    history: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Pre-Symptomatic Illness Score (0–100 Immune Severity Index).
    Weighted composite severity score tracking autonomic stress across all 4 overnight vitals.
    """
    def get_stats(key, default_mu, default_sd):
        vals = [float(h[key]) for h in history if h.get(key) is not None]
        if len(vals) < 3:
            return default_mu, default_sd
        mu = sum(vals) / len(vals)
        var = sum((x - mu) ** 2 for x in vals) / len(vals)
        sd = max(0.5, math.sqrt(var))
        return mu, sd

    mu_hrv, sd_hrv = get_stats("hrv_rmssd", 85.0, 10.0)
    mu_rhr, sd_rhr = get_stats("rhr", 45.0, 3.0)
    mu_resp, sd_resp = get_stats("resp_rate", 12.0, 1.0)
    mu_spo2, sd_spo2 = get_stats("spo2", 97.0, 1.0)

    z_hrv = max(0.0, (mu_hrv - float(today_hrv or mu_hrv)) / sd_hrv) if today_hrv is not None else 0.0
    z_rhr = max(0.0, (float(today_rhr or mu_rhr) - mu_rhr) / sd_rhr) if today_rhr is not None else 0.0
    z_resp = max(0.0, (float(today_resp or mu_resp) - mu_resp) / sd_resp) if today_resp is not None else 0.0
    z_spo2 = max(0.0, (mu_spo2 - float(today_spo2 or mu_spo2)) / sd_spo2) if today_spo2 is not None else 0.0

    i_raw = 0.35 * z_resp + 0.30 * z_rhr + 0.25 * z_hrv + 0.10 * z_spo2
    immune_index = min(100, int(round((i_raw / 3.0) * 100)))

    if immune_index >= 56:
        tier = "High Infection / Illness Risk"
        tier_key = "HIGH"
    elif immune_index >= 26:
        tier = "Watch / Mild Autonomic Stress"
        tier_key = "WATCH"
    else:
        tier = "Normal"
        tier_key = "NORMAL"

    return {
        "immune_strain_index": immune_index,
        "tier": tier,
        "tier_key": tier_key,
        "raw_index": round(i_raw, 2),
        "z_scores": {
            "hrv": round(z_hrv, 2),
            "rhr": round(z_rhr, 2),
            "resp": round(z_resp, 2),
            "spo2": round(z_spo2, 2)
        }
    }

def calculate_daytime_stress_balance(stress_raw: Optional[dict[str, Any]]) -> dict[str, Any]:
    """
    Daytime Stress Balance Ratio.
    Quantifies parasympathetic restoration vs sympathetic activation during waking hours.
    """
    if not stress_raw or not isinstance(stress_raw, dict):
        return {
            "rest_minutes": None,
            "high_stress_minutes": None,
            "stress_balance_ratio": None,
            "is_optimal": None,
            "status": "NO DATA"
        }

    pts = stress_raw.get("stressValuesArray") or []
    if not pts:
        return {
            "rest_minutes": None,
            "high_stress_minutes": None,
            "stress_balance_ratio": None,
            "is_optimal": None,
            "status": "NO DATA"
        }

    rest_count = sum(1 for p in pts if len(p) >= 2 and 0 < p[1] < 25)
    high_count = sum(1 for p in pts if len(p) >= 2 and p[1] >= 50)
    
    rest_min = rest_count * 3
    high_min = high_count * 3
    ratio = round(rest_min / max(1.0, high_min), 2)
    is_optimal = ratio >= 1.5

    return {
        "rest_minutes": rest_min,
        "high_stress_minutes": high_min,
        "stress_balance_ratio": ratio,
        "is_optimal": is_optimal,
    }
