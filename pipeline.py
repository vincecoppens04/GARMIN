import os
import math
import json
import textwrap
import urllib.request
from datetime import date, datetime, timedelta, time
from zoneinfo import ZoneInfo
from pathlib import Path
from garminconnect import Garmin
from supabase import create_client, Client

def load_env(env_path=None):
    """Loads environment variables from .env file without requiring external dependencies."""
    if env_path is None:
        env_path = Path(__file__).resolve().parent / ".env"
    else:
        env_path = Path(env_path)

    if env_path.is_file():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = val

load_env()

# Normal CDF: use scipy if available, otherwise exact math.erf formulation
try:
    from scipy.stats import norm
    norm_cdf = norm.cdf
except ImportError:
    def norm_cdf(z: float) -> float:
        """Standard normal cumulative distribution function using math.erf."""
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

# =====================================================================
# CONFIGURATION & TIMEZONES
# =====================================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
APP_USER_EMAIL = os.getenv("APP_USER_EMAIL")
APP_USER_PASSWORD = os.getenv("APP_USER_PASSWORD")
TOKENSTORE = os.path.expanduser("~/.garminconnect")

# Configurable User Timezone (Crucial for midnight boundaries & bucketing)
USER_TIMEZONE = ZoneInfo("Europe/Brussels")

def get_garmin_client() -> Garmin:
    token_dir = Path(TOKENSTORE).expanduser()
    token_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Try to reuse cached OAuth tokens (NO EMAIL SENT)
    try:
        garmin = Garmin()
        garmin.login(str(token_dir))
        print("✓ Authenticated using cached Garmin session tokens.")
        return garmin
    except Exception as e:
        print(f"[Notice] Cached session missing or expired ({e}). Logging in with credentials...")

    # 2. Fallback: Full login with credentials (TRIGGERS EMAIL)
    email = os.getenv("GARMIN_EMAIL") or os.getenv("EMAIL")
    password = os.getenv("GARMIN_PASSWORD") or os.getenv("PASSWORD")
    
    garmin = Garmin(
        email=email,
        password=password,
        prompt_mfa=lambda: input("Enter Garmin MFA code: ").strip(),
    )
    garmin.login(str(token_dir))

    # 3. Correctly save tokens so subsequent syncs reuse them
    try:
        if hasattr(garmin, "client") and hasattr(garmin.client, "dump"):
            garmin.client.dump(str(token_dir))
        elif hasattr(garmin, "garth") and hasattr(garmin.garth, "dump"):
            garmin.garth.dump(str(token_dir))
        elif hasattr(garmin, "dump"):
            garmin.dump(str(token_dir))
        print(f"✓ Session tokens successfully saved to {token_dir}")
    except Exception as dump_err:
        print(f"[Warning] Failed to persist session tokens: {dump_err}")

    return garmin

def get_supabase_client() -> tuple[Client, str]:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    auth = supabase.auth.sign_in_with_password({
        "email": APP_USER_EMAIL,
        "password": APP_USER_PASSWORD,
    })
    return supabase, auth.user.id

# =====================================================================
# 1. LOAD & STRAIN ENGINE (Timezone-Aware & Continuous)
# =====================================================================

def calculate_activity_strain(
    avg_hr: int | float | None,
    duration_sec: int,
    rhr: int,
    max_hr: int,
    sex: str = "male"
) -> float:
    """
    Computes standalone cardiovascular strain (0-21) for a single workout window.
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
    strain = round(21.0 * (1.0 - math.exp(-0.015 * trimp)), 1)
    return min(21.0, strain)

def calculate_strain_and_curve(
    hr_data: dict, 
    rhr: int, 
    max_hr: int, 
    target_date_str: str,
    sex: str = "male"
) -> tuple[float, list]:
    """
    Computes cumulative cardio strain using continuous Banister formulation
    with an exertion threshold (y >= 0.15) and builds an exact 96-bucket 
    15-minute curve in local time.
    """
    hr_values = hr_data.get("heartRateValues", [])
    if not hr_values:
        return 0.0, []

    # 1. Strictly filter nulls and sort chronologically
    valid_points = sorted(
        [p for p in hr_values if p[1] is not None and len(p) >= 2],
        key=lambda x: x[0]
    )
    if not valid_points:
        return 0.0, []

    hr_reserve = max(20, max_hr - rhr)
    total_trimp = 0.0

    # Sex-specific Banister coefficients
    b_coeff = 1.92 if sex.lower() == "male" else 1.67
    a_coeff = 0.64 if sex.lower() == "male" else 0.86

    # 2. Setup 96 fifteen-minute buckets (00:00 to 23:45 local time)
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
                # Cardiac exertion above 15% of HR reserve accumulates strain (allows walks & active daily stress)
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
                # Calibrated 0-21 logarithmic strain scalar (k = 0.015)
                current_strain = round(21.0 * (1.0 - math.exp(-0.015 * total_trimp)), 1)
                buckets[b_idx]["cum_strain"] = min(21.0, current_strain)

    # 3. Format complete 96-bucket curve with forward-fill for smooth presentation
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

    final_day_strain = round(21.0 * (1.0 - math.exp(-0.015 * total_trimp)), 1)
    return min(21.0, final_day_strain), strain_curve_96

# =====================================================================
# 2. PHYSIOLOGICAL RECOVERY & HEALTH-STRESS ENGINE
# =====================================================================

def calculate_recovery_and_health_stress(
    today_hrv: float | None,
    today_rhr: int | None,
    today_resp: float | None,
    today_spo2: float | None,
    sleep_actual_sec: int | None,
    last_night_target_min: int,
    history: list
) -> tuple[int, str, list, str, str]:
    """
    Computes recovery score with dynamic weight re-normalization,
    and runs a multi-signal pre-symptomatic illness/stress evaluation.
    """
    alerts = []
    
    # 1. Extract historical baselines (up to 30 days)
    hrv_hist = [h["hrv_rmssd"] for h in history if h.get("hrv_rmssd") is not None]
    rhr_hist = [h["rhr"] for h in history if h.get("rhr") is not None]
    resp_hist = [h["resp_rate"] for h in history if h.get("resp_rate") is not None]
    spo2_hist = [h["spo2"] for h in history if h.get("spo2") is not None]

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

# =====================================================================
# 3. SLEEP ENGINE (True Debt Ledger & Recommended Bedtime)
# =====================================================================

def calculate_sleep_ledger_and_bedtime(
    base_sleep_need_min: int,
    debt_payback_rate: float,
    prev_summary: dict | None,
    day_strain: float,
    target_date_str: str,
    target_wake_time: str = "07:00",
    sleep_latency_min: int = 15,
    deadband_min: int = 30,
    max_debt_ceiling_min: int = 120
) -> tuple[int, int, str, int, int]:
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

def calculate_circadian_consistency(recent_summaries: list, today_onset: str | datetime | None, today_wake: str | datetime | None) -> int:
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

# =====================================================================
# 4. CALIBRATED STRAIN TARGET WITH ILLNESS OVERRIDE
# =====================================================================

def calculate_target_strain_window(recovery_score: int, health_status: str) -> tuple[float, float]:
    """
    Saturating target curve: Target = 21 * (Recovery / 100) ** 0.65.
    Forces active recovery if sickness is detected.
    """
    if health_status == "HIGH_STRAIN_SICKNESS":
        # Override: sickness requires physical rest
        return 0.0, 6.0
    elif health_status == "WATCH":
        # Restrict ceiling on watch days
        return 4.0, 9.0

    # Normal target curve from sports science brief
    midpoint = round(21.0 * ((recovery_score / 100.0) ** 0.65), 1)
    return max(0.0, round(midpoint - 1.5, 1)), min(21.0, round(midpoint + 1.5, 1))

# =====================================================================
# 5. LIGHTWEIGHT AI BRIEFING & HABIT IMPACT ENGINES
# =====================================================================

def generate_ai_briefing(
    recovery_score: int,
    day_strain: float,
    target_strain_min: float,
    target_strain_max: float,
    current_debt: int,
    health_status: str,
    alerts: list,
    driver: str,
) -> str:
    """
    Generates a concise, 2-sentence clinical sports science morning briefing.
    Uses Google Gemini Flash if GEMINI_API_KEY is configured in .env,
    otherwise uses an intelligent, deterministic local sports science rule engine.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
            alert_str = ", ".join(alerts) if alerts else "None"
            prompt = (
                f"You are an elite sports scientist and physiologist. Analyze this morning's telemetry:\n"
                f"- Recovery Score: {recovery_score}%\n"
                f"- Primary Driver: {driver}\n"
                f"- Health Status: {health_status}\n"
                f"- Health Alerts: {alert_str}\n"
                f"- Prescribed Day Strain Target: {target_strain_min:.1f} - {target_strain_max:.1f} / 21.0\n"
                f"- Acute Sleep Debt: {current_debt} min\n"
                f"Write exactly 2 concise, clinical, and directly actionable sentences for the athlete's morning briefing. "
                f"No conversational filler, no greetings, no hashtags. Focus on capacity to absorb cardiovascular load and bedtime strategy."
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 90, "temperature": 0.4}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return text
        except Exception:
            pass  # Seamless fallback to local deterministic expert engine

    # --- Local Deterministic Sports Science Rule Engine (Zero external dependencies) ---
    if health_status == "HIGH_STRAIN_SICKNESS":
        return (
            "CRITICAL HEALTH ALERT: Multiple vital anomalies indicate acute systemic stress or early infection. "
            "Suspend all cardiovascular exertion today, prioritize hydration, and focus entirely on passive recovery."
        )
    if health_status == "WATCH":
        alerts_joined = ", ".join(alerts)
        alert_text = f" ({alerts_joined})" if alerts else ""
        return (
            f"PHYSIOLOGICAL STRAIN ELEVATED: Vitals show significant deviation from your 30-day baseline{alert_text}. "
            f"Cap exertion at gentle active recovery (under {target_strain_max:.1f} strain) and avoid strenuous cardio."
        )

    if recovery_score >= 67:
        if current_debt > 30:
            return (
                f"Autonomic recovery is primed ({driver}) despite {current_debt}m of acute sleep debt. "
                f"You have capacity to absorb {target_strain_min:.1f}–{target_strain_max:.1f} strain today, but prioritize an earlier bedtime tonight to clear the deficit."
            )
        return (
            f"Parasympathetic tone is optimal ({driver}), indicating high cardiovascular adaptability. "
            f"You are greenlit for strenuous training—target {target_strain_min:.1f}–{target_strain_max:.1f} strain today."
        )
    elif recovery_score >= 34:
        if recovery_score >= 50:
            return (
                f"Physiological equilibrium is steady ({driver}). "
                f"Your cardiovascular system is prepared for moderate maintenance load; target {target_strain_min:.1f}–{target_strain_max:.1f} strain today."
            )
        return (
            f"Mild systemic fatigue detected ({driver}). "
            f"Modulate today's training volume to avoid overreaching—cap strain at {target_strain_max:.1f} and prioritize restorative nutrition."
        )
    else:
        return (
            f"Autonomic recovery is suppressed ({driver}). "
            f"Cardiovascular reserve is restricted today; limit exertion to gentle active recovery (under {target_strain_max:.1f} strain) to restore balance."
        )

def calculate_habit_correlations(supabase: Client, user_id: str) -> list[dict]:
    """
    Computes ΔHRV and ΔRHR impact for habits logged in habit_logs over trailing 60 days.
    """
    try:
        habits_res = supabase.table("habit_logs").select("*").eq("user_id", user_id).order("date", desc=True).limit(60).execute()
        summaries_res = supabase.table("daily_summaries").select("date, hrv_rmssd, rhr").eq("user_id", user_id).order("date", desc=True).limit(60).execute()

        habits_by_date = {h["date"]: h for h in (habits_res.data or []) if h.get("date")}
        summaries = summaries_res.data or []

        habit_keys = [
            ("alcohol", "Alcohol"),
            ("late_meal", "Late Meal (<2h bed)"),
            ("late_caffeine", "Late Caffeine"),
            ("any_caffeine", "Any Caffeine"),
            ("screen_in_bed", "Screen in Bed"),
            ("travel_day", "Travel / Jetlag"),
        ]
        results = []

        for key, label in habit_keys:
            present_hrv, absent_hrv = [], []
            present_rhr, absent_rhr = [], []

            for s in summaries:
                d = s.get("date")
                if not d or d not in habits_by_date:
                    continue
                h_entry = habits_by_date[d]
                is_present = bool(h_entry.get(key, False))

                hrv = s.get("hrv_rmssd")
                rhr = s.get("rhr")
                if hrv is not None:
                    (present_hrv if is_present else absent_hrv).append(float(hrv))
                if rhr is not None:
                    (present_rhr if is_present else absent_rhr).append(float(rhr))

            # Only report if logged at least 3 times
            if len(present_hrv) >= 3 and len(absent_hrv) >= 3:
                delta_hrv = round((sum(present_hrv) / len(present_hrv)) - (sum(absent_hrv) / len(absent_hrv)), 1)
                delta_rhr = round((sum(present_rhr) / len(present_rhr)) - (sum(absent_rhr) / len(absent_rhr)), 1)
                results.append({
                    "habit_key": key,
                    "label": label,
                    "count": len(present_hrv),
                    "delta_hrv": delta_hrv,
                    "delta_rhr": delta_rhr,
                })

        return results
    except Exception:
        return []

# =====================================================================
# 6. PHONE PUSH NOTIFICATION ENGINE
# =====================================================================

def send_phone_notification(title: str, message: str, priority: str = "normal", tags: list | None = None) -> bool:
    """
    Delivers a push notification directly to the user's phone lock screen.
    Supports ntfy.sh (zero-setup instant mobile push), OneSignal REST API, or generic Webhook.
    """
    delivered = False

    # 1. ntfy.sh (Instant phone push: free iOS/Android app subscribed to your private topic)
    ntfy_topic = os.getenv("NTFY_TOPIC")
    if ntfy_topic:
        try:
            req = urllib.request.Request(
                f"https://ntfy.sh/{ntfy_topic}",
                data=message.encode("utf-8"),
                headers={
                    "Title": title.encode("utf-8"),
                    "Priority": "high" if priority == "high" else "default",
                    "Tags": ",".join(tags) if tags else "running",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    delivered = True
                    print(f"  ✓ Push delivered to phone via ntfy.sh ({ntfy_topic})")
        except Exception as e:
            print(f"  [Push Error] ntfy.sh failed: {e}")

    # 2. OneSignal REST API (Native iOS PWA Web Push directly to your phone)
    onesignal_app_id = os.getenv("ONESIGNAL_APP_ID")
    onesignal_api_key = os.getenv("ONESIGNAL_REST_API_KEY") or os.getenv("ONESIGNAL_API_KEY")
    app_url = os.getenv("APP_URL")  # e.g. https://your-app.vercel.app
    if onesignal_app_id and onesignal_api_key:
        try:
            url = "https://onesignal.com/api/v1/notifications"
            payload = {
                "app_id": onesignal_app_id,
                "included_segments": ["Subscribed Users"],
                "headings": {"en": title},
                "contents": {"en": message},
            }
            if app_url:
                payload["url"] = app_url  # Tapping notification opens your Vercel app!
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Authorization": f"Basic {onesignal_api_key}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    delivered = True
                    print(f"  ✓ Push delivered to iPhone via OneSignal")
        except Exception as e:
            print(f"  [Push Error] OneSignal failed: {e}")

    # 3. Generic Webhook (Discord / Slack / Pushover / Home Assistant)
    webhook_url = os.getenv("NOTIFY_WEBHOOK_URL")
    if webhook_url:
        try:
            payload = {"title": title, "message": message, "content": f"**{title}**\n{message}"}
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status in (200, 204):
                    delivered = True
                    print(f"  ✓ Push delivered to phone via Webhook")
        except Exception as e:
            print(f"  [Push Error] Webhook failed: {e}")

    if not (ntfy_topic or (onesignal_app_id and onesignal_api_key) or webhook_url):
        print("  [Push Notice] No phone notification channel configured. Add NTFY_TOPIC or ONESIGNAL_* to .env")

    return delivered

def notify_morning_sync_reminder():
    """Notification 1 (07:30): Ask if watch has synced."""
    title = "⌚ Garmin Sync Reminder"
    message = "Hi, have you already uploaded or synced your Garmin?"
    return send_phone_notification(title, message, priority="normal", tags=["watch", "arrows_counterclockwise"])

def notify_morning_readiness(summary: dict):
    """Notification 2 (08:00 or on-demand 'Sync Now'): Daily situation briefing."""
    rec = summary.get("recovery", 50)
    strain = summary.get("strain", 0.0)
    health = summary.get("health_status", "NORMAL")
    alerts = summary.get("health_alerts", [])
    briefing = summary.get("ai_briefing", "")
    t_min = summary.get("target_strain_min", 0.0)
    t_max = summary.get("target_strain_max", 21.0)
    
    # Notification 5: Immediate Health & Sickness Alert
    if health != "NORMAL" or alerts:
        alert_msg = f"Multiple vital anomalies detected ({', '.join(alerts)}). Cardiovascular strain should be capped today. Rest and active recovery recommended."
        send_phone_notification("⚠️ Health Alert: Rest Recommended", alert_msg, priority="high", tags=["warning", "medical_symbol"])
    
    zone_emoji = "🟢" if rec >= 67 else ("🟡" if rec >= 34 else "🔴")
    title = f"{zone_emoji} Recovery: {rec}% | Daily Situation"
    
    msg_lines = [
        f"Hi, this is your situation for today:",
        f"• Recovery: {rec}% ({'Primed' if rec>=67 else 'Adequate' if rec>=34 else 'Rest Required'})",
        f"• Target Strain: {t_min:.1f} – {t_max:.1f}",
    ]
    if briefing:
        msg_lines.append(f"\"{briefing}\"")
        
    message = "\n".join(msg_lines)
    return send_phone_notification(title, message, priority="normal", tags=["chart_with_upwards_trend", "muscle"])

def notify_evening_sync_reminder():
    """Notification 3 (20:30): Evening sync reminder."""
    title = "⌚ Garmin Evening Sync"
    message = "Hi, have you synced your Garmin recently?"
    return send_phone_notification(title, message, priority="normal", tags=["watch", "bed"])

def notify_evening_bedtime(summary: dict):
    """Notification 4 (21:00): Evening bedtime and wind-down prescription."""
    strain = summary.get("strain", 0.0)
    bedtime = summary.get("bedtime", "22:30")
    need_min = summary.get("sleep_need_min", 435)
    debt = summary.get("debt_min", 0)
    
    need_h = need_min // 60
    need_m = need_min % 60
    
    debt_text = f" (clearing {debt}m debt)" if debt > 0 else ""
    title = f"🌙 Sleep Prescription: Bedtime {bedtime}"
    message = (
        f"Hi, based on your day strain of {strain:.1f}, it's best you go to sleep at {bedtime} "
        f"to get {need_h}h {need_m:02d}m of restorative sleep{debt_text}."
    )
    return send_phone_notification(title, message, priority="normal", tags=["crescent_moon", "sleeping"])

# =====================================================================
# 7. MOBILE APP DASHBOARD PRESENTATION ENGINE
# =====================================================================

def print_app_dashboard(
    target_date: str,
    user_email: str,
    recovery_score: int,
    driver: str,
    alerts: list,
    health_status: str,
    conf: str,
    vitals_stats: dict,
    day_strain: float,
    target_strain_min: float,
    target_strain_max: float,
    strain_curve: list,
    sleep_actual_sec: int | None,
    sleep_bed_sec: int | None,
    sleep_efficiency: float | None,
    daily_sleep: dict,
    last_night_target_min: int,
    current_debt: int,
    target_tonight_min: int,
    bedtime_str: str,
    sleep_equation_str: str,
    circadian_consistency: int,
    activities_list: list,
    cardio_age_info: dict,
    ai_briefing: str = "",
    habit_correlations: list | None = None,
):
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

def safe_round(val, decimals: int = 0, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return round(f, decimals) if decimals > 0 else int(round(f))
    except (ValueError, TypeError):
        return default

# =====================================================================
# 6. MAIN PIPELINE EXECUTION
# =====================================================================

def process_day(
    target_date: str,
    garmin: Garmin | None = None,
    supabase_tuple: tuple[Client, str] | None = None,
    quiet: bool = False
) -> dict:
    if not quiet:
        print(f"\n========================================================")
        print(f" Processing V2 Garmin Telemetry Engine for: {target_date}")
        print(f"========================================================")

    # 1. Connect
    garmin = garmin or get_garmin_client()
    if supabase_tuple:
        supabase, user_id = supabase_tuple
    else:
        supabase, user_id = get_supabase_client()

    # 2. Fetch User Baselines
    baselines_res = supabase.table("user_baselines").select("*").eq("user_id", user_id).single().execute()
    baselines = baselines_res.data or {}
    max_hr = baselines.get("max_hr", 190)
    base_sleep_need = baselines.get("baseline_sleep_need_min", 435)
    debt_payback_rate = float(baselines.get("debt_payback_rate", 0.33))
    user_sex = baselines.get("sex", "male")

    # 3. Pull Garmin Endpoints with Exact Field Extraction
    print("-> Fetching Garmin endpoints...")
    sleep_raw = garmin.get_sleep_data(target_date)
    hrv_raw = garmin.get_hrv_data(target_date)
    hr_raw = garmin.get_heart_rates(target_date)
    
    # RHR extraction via dedicated get_rhr_day()
    rhr_raw = garmin.get_rhr_day(target_date)
    
    # Multi-path Resting Heart Rate (RHR) extraction
    today_rhr = None
    if isinstance(rhr_raw, dict):
        # 1. Try Garmin metricsMap structure: allMetrics -> metricsMap -> WELLNESS_RESTING_HEART_RATE
        metrics_list = (
            rhr_raw.get("allMetrics", {})
            .get("metricsMap", {})
            .get("WELLNESS_RESTING_HEART_RATE", [])
        )
        if metrics_list and isinstance(metrics_list, list) and len(metrics_list) > 0:
            val = metrics_list[0].get("value")
            if val is not None:
                today_rhr = int(round(float(val)))

        # 2. Try direct root keys
        if today_rhr is None:
            val = (
                rhr_raw.get("restingHeartRate") or 
                rhr_raw.get("allDayMetDTO", {}).get("restingHeartRate") or 
                rhr_raw.get("statistics", {}).get("restingHeartRate")
            )
            if val is not None:
                today_rhr = int(round(float(val)))

    # 3. Fallback to intraday heart rate root property
    if today_rhr is None and isinstance(hr_raw, dict):
        val = hr_raw.get("restingHeartRate")
        if val is not None:
            today_rhr = int(round(float(val)))

    # Sleep Vitals Extraction
    daily_sleep = sleep_raw.get("dailySleepDTO") or {}
    sleep_actual_sec = daily_sleep.get("sleepTimeSeconds")
    
    # Data Freshness Guard: Alert if today's sleep has not yet synced via Bluetooth
    is_today = (target_date == date.today().isoformat())
    if is_today and (not sleep_actual_sec or sleep_actual_sec <= 0):
        print(f"\n  [Sync Notice] Today's sleep data ({target_date}) has not yet synced from your Garmin watch.")
        print("  -> Open Garmin Connect on your phone to complete the Bluetooth sync.")
        print("  -> Calculating provisional readiness from available telemetry...\n")
    
    sleep_bed_sec = None
    if daily_sleep.get("sleepStartTimestampGMT") and daily_sleep.get("sleepEndTimestampGMT"):
        sleep_bed_sec = int((daily_sleep["sleepEndTimestampGMT"] - daily_sleep["sleepStartTimestampGMT"]) / 1000)
    
    sleep_efficiency = round((sleep_actual_sec / sleep_bed_sec) * 100, 1) if sleep_actual_sec and sleep_bed_sec else None

    # Vitals with updated keys
    today_resp = daily_sleep.get("avgRespirationValue") or daily_sleep.get("averageRespirationValue")
    today_spo2 = daily_sleep.get("avgSpO2") or daily_sleep.get("averageSpO2Value")

    hrv_summary = hrv_raw.get("hrvSummary") or {}
    today_hrv = hrv_summary.get("lastNightAvg")

    # Sleep stage intervals
    stages_timeline = []
    if "sleepLevelsMap" in daily_sleep and daily_sleep["sleepLevelsMap"]:
        for stage_name, intervals in daily_sleep["sleepLevelsMap"].items():
            for entry in intervals:
                stages_timeline.append({
                    "stage": stage_name,
                    "start": entry.get("startGMT"),
                    "end": entry.get("endGMT")
                })

    # 4. Compute Strain & 96-Bucket Curve
    print("-> Calculating Timezone-Aware Cardiovascular Strain...")
    day_strain, strain_curve = calculate_strain_and_curve(
        hr_raw, today_rhr or 50, max_hr, target_date, sex=user_sex
    )

    # 5. Fetch History & Yesterday's Target
    print("-> Pulling 30-day baseline history...")
    hist_res = supabase.table("daily_summaries")\
        .select("hrv_rmssd, rhr, resp_rate, spo2, sleep_onset, sleep_wake")\
        .eq("user_id", user_id)\
        .lt("date", target_date)\
        .order("date", desc=True)\
        .limit(30)\
        .execute()
    history = hist_res.data or []

    prev_date = (date.fromisoformat(target_date) - timedelta(days=1)).isoformat()
    prev_res = supabase.table("daily_summaries").select("*").eq("user_id", user_id).eq("date", prev_date).execute()
    prev_summary = prev_res.data[0] if prev_res.data else None
    
    # Evaluate sleep against yesterday's prescribed target, not base need
    last_night_target = prev_summary.get("sleep_need_min", base_sleep_need) if prev_summary else base_sleep_need

    # 6. Run Engines
    recovery_score, driver, alerts, health_status, conf, vitals_stats = calculate_recovery_and_health_stress(
        today_hrv, today_rhr, today_resp, today_spo2, sleep_actual_sec, last_night_target, history
    )
    
    current_debt, target_tonight_min, bedtime_str, sleep_equation_str = calculate_sleep_ledger_and_bedtime(
        base_sleep_need, debt_payback_rate, prev_summary, day_strain, target_date
    )
    
    target_strain_min, target_strain_max = calculate_target_strain_window(recovery_score, health_status)

    # Sleep onset & wake timestamps (converted directly to local timezone)
    start_gmt = daily_sleep.get("sleepStartTimestampGMT")
    end_gmt = daily_sleep.get("sleepEndTimestampGMT")
    today_onset_dt = datetime.fromtimestamp(start_gmt / 1000, tz=ZoneInfo("UTC")).astimezone(USER_TIMEZONE) if start_gmt else None
    today_wake_dt = datetime.fromtimestamp(end_gmt / 1000, tz=ZoneInfo("UTC")).astimezone(USER_TIMEZONE) if end_gmt else None
    today_onset_iso = today_onset_dt.isoformat() if today_onset_dt else None
    today_wake_iso = today_wake_dt.isoformat() if today_wake_dt else None

    circadian_consistency = calculate_circadian_consistency(history, today_onset_dt, today_wake_dt)

    # 7. Generate AI Morning Coaching Briefing
    ai_briefing = generate_ai_briefing(
        recovery_score=recovery_score,
        day_strain=day_strain,
        target_strain_min=target_strain_min,
        target_strain_max=target_strain_max,
        current_debt=current_debt,
        health_status=health_status,
        alerts=alerts,
        driver=driver,
    )

    # 8. Compute Trailing 60-Day Habit Impact Analytics (Tab 4)
    habit_correlations = calculate_habit_correlations(supabase, user_id)

    # 9. Upsert Daily Record with Explicit on_conflict Target
    summary_record = {
        "user_id": user_id,
        "date": target_date,
        "recovery_score": recovery_score,
        "recovery_driver": driver,
        "hrv_rmssd": today_hrv,
        "rhr": today_rhr,
        "resp_rate": today_resp,
        "spo2": today_spo2,
        "day_strain": day_strain,
        "target_strain_min": target_strain_min,
        "target_strain_max": target_strain_max,
        "strain_curve_15m": strain_curve,
        "sleep_actual_sec": sleep_actual_sec,
        "sleep_bed_sec": sleep_bed_sec,
        "sleep_efficiency": sleep_efficiency,
        "sleep_onset": today_onset_iso,
        "sleep_wake": today_wake_iso,
        "sleep_need_min": target_tonight_min,
        "sleep_debt_min": current_debt,
        "circadian_consistency": circadian_consistency,
        "sleep_stages_timeline": stages_timeline,
        "health_alerts": alerts,
        "ai_briefing": ai_briefing,
    }

    print("-> Upserting daily summary record to Supabase (on_conflict=user_id,date)...")
    supabase.table("daily_summaries").upsert(summary_record, on_conflict="user_id,date").execute()

    # 8. Sync Activities
    print("-> Syncing activities...")
    synced_activities = []
    try:
        activities = garmin.get_activities_by_date(target_date, target_date)
        for act in activities:
            act_id = act.get("activityId")
            avg_hr = safe_round(act.get("averageHR"))
            max_hr_val = safe_round(act.get("maxHR"))
            calories_val = safe_round(act.get("calories"), default=0)
            duration = safe_round(act.get("duration"), default=0)
            distance_val = safe_round(act.get("distance"), decimals=2, default=0.0)
            load_val = safe_round(act.get("activityTrainingLoad"), decimals=1)
            te_val = safe_round(act.get("aerobicTrainingEffect"), decimals=1)

            workout_strain = calculate_activity_strain(
                avg_hr=avg_hr,
                duration_sec=duration,
                rhr=today_rhr or 50,
                max_hr=max_hr,
                sex=user_sex,
            )
            act_record = {
                "id": act_id,
                "user_id": user_id,
                "date": target_date,
                "activity_type": act.get("activityType", {}).get("typeKey", "unknown"),
                "name": act.get("activityName", "Workout"),
                "start_time": act.get("startTimeGMT"),
                "duration_sec": duration,
                "avg_hr": avg_hr,
                "max_hr": max_hr_val,
                "distance_m": distance_val,
                "calories": calories_val,
                "garmin_load": load_val,
                "aerobic_te": te_val,
                "workout_strain": workout_strain,
            }
            supabase.table("activities").upsert(act_record, on_conflict="id").execute()
            synced_activities.append(act_record)
    except Exception as e:
        print(f"  [Notice] Activity sync skipped or empty: {e}")

    # 9. Sync VO2 Max to user_baselines for Cardiovascular Age (Tab 4)
    print("-> Checking VO2 Max in training status...")
    vo2_max_val = None
    try:
        training_raw = garmin.get_training_status(target_date)
        if isinstance(training_raw, dict):
            vo2_data = training_raw.get("mostRecentVO2Max", {}).get("generic", {})
            vo2_max_val = vo2_data.get("vo2MaxPreciseValue") or vo2_data.get("vo2MaxValue")
        
        if vo2_max_val:
            supabase.table("user_baselines").update({"vo2_max": vo2_max_val}).eq("user_id", user_id).execute()
    except Exception as e:
        pass

    current_vo2 = vo2_max_val or baselines.get("vo2_max")
    chrono_age = date.today().year - int(baselines.get("birth_year", 2004))
    cardio_age = None
    if current_vo2:
        expected_vo2 = 50.5 - (0.37 * chrono_age)
        raw_delta = ((float(current_vo2) - expected_vo2) / 0.37) + ((50.0 - float(today_rhr or 50.0)) / 5.0)
        # Enforce biological maturity floor (18.0 years) - fitness age cannot be negative or pediatric
        cardio_age = max(18.0, round(chrono_age - raw_delta, 1))

    cardio_age_info = {
        "chrono_age": chrono_age,
        "vo2_max": current_vo2,
        "rhr": today_rhr,
        "cardio_age": cardio_age,
    }

    # 10. Display Full Executive Mobile App Dashboard
    if not quiet:
        print_app_dashboard(
            target_date=target_date,
            user_email=APP_USER_EMAIL or baselines.get("email") or "user@garmin.com",
            recovery_score=recovery_score,
            driver=driver,
            alerts=alerts,
            health_status=health_status,
            conf=conf,
            vitals_stats=vitals_stats,
            day_strain=day_strain,
            target_strain_min=target_strain_min,
            target_strain_max=target_strain_max,
            strain_curve=strain_curve,
            sleep_actual_sec=sleep_actual_sec,
            sleep_bed_sec=sleep_bed_sec,
            sleep_efficiency=sleep_efficiency,
            daily_sleep=daily_sleep,
            last_night_target_min=last_night_target,
            current_debt=current_debt,
            target_tonight_min=target_tonight_min,
            bedtime_str=bedtime_str,
            sleep_equation_str=sleep_equation_str,
            circadian_consistency=circadian_consistency,
            activities_list=synced_activities,
            cardio_age_info=cardio_age_info,
            ai_briefing=ai_briefing,
            habit_correlations=habit_correlations,
        )

    return {
        "date": target_date,
        "recovery": recovery_score,
        "strain": day_strain,
        "target_strain_min": target_strain_min,
        "target_strain_max": target_strain_max,
        "sleep_sec": sleep_actual_sec or 0,
        "sleep_need_min": target_tonight_min,
        "debt_min": current_debt,
        "bedtime": bedtime_str,
        "health_status": health_status,
        "health_alerts": alerts,
        "activities_count": len(synced_activities),
        "vo2_max": current_vo2,
        "circadian_consistency": circadian_consistency,
        "ai_briefing": ai_briefing,
    }

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    cmd = args[0].strip().lower() if args else "yesterday"

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
    elif cmd == "today":
        process_day(date.today().isoformat())
    elif cmd == "yesterday":
        process_day((date.today() - timedelta(days=1)).isoformat())
    else:
        process_day(cmd)
