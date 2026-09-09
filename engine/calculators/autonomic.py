from typing import Optional, Any

def calculate_autonomic_sleep_profile(
    sleep_raw: dict[str, Any],
    daytime_rhr: Optional[float]
) -> dict[str, Any]:
    """
    Autonomic Sleep Profile: Nocturnal Dipping & Curve Shape.
    Assesses whether sympathetic tone shuts down during sleep using overnight HR time series.
    """
    sleep_hr_list = sleep_raw.get("sleepHeartRate") or [] if isinstance(sleep_raw, dict) else []
    valid_hrs = [item["value"] for item in sleep_hr_list if isinstance(item, dict) and item.get("value") is not None]
    
    if not valid_hrs or not daytime_rhr or daytime_rhr <= 0:
        return {
            "dip_pct": None,
            "dipping_tier": "NO DATA",
            "curve_shape": "NO DATA",
            "curve_desc": "Awaiting overnight HR time series.",
            "lowest_overnight_hr": None,
            "nadir_ratio": None
        }

    lowest_hr = min(valid_hrs)
    dip_pct = round(((daytime_rhr - lowest_hr) / daytime_rhr) * 100, 1)

    if dip_pct > 20.0:
        dipping_tier = "Extreme Dipper"
        dip_desc = "High vagal tone or severe physiological exhaustion"
    elif dip_pct >= 10.0:
        dipping_tier = "Normal Dipper"
        dip_desc = "Healthy cardiovascular decompression during sleep"
    else:
        dipping_tier = "Non-Dipper"
        dip_desc = "Sympathetic elevation, high systemic inflammation, or late digestion penalty"

    t_total = len(valid_hrs)
    nadir_idx = valid_hrs.index(lowest_hr)
    nadir_ratio = round(nadir_idx / max(1, t_total), 2)

    half = t_total // 2
    h1 = valid_hrs[:half] if half > 0 else valid_hrs
    h2 = valid_hrs[half:] if half > 0 else valid_hrs
    mean_h1 = sum(h1) / len(h1) if h1 else 0.0
    mean_h2 = sum(h2) / len(h2) if h2 else 0.0

    if 0.25 <= nadir_ratio <= 0.75:
        curve_shape = "Hammock"
        curve_desc = "Optimal recovery: HR reached nadir midway through sleep and recovered smoothly."
    elif mean_h1 > mean_h2 + 4.0:
        curve_shape = "Slope"
        curve_desc = "Delayed recovery: Elevated heart rate in early sleep due to late digestion/alcohol."
    else:
        curve_shape = "Plateau"
        curve_desc = "Continuous sympathetic elevation: Heart rate remained unrelaxed across sleep cycle."

    return {
        "dip_pct": dip_pct,
        "dipping_tier": dipping_tier,
        "dip_desc": dip_desc,
        "curve_shape": curve_shape,
        "curve_desc": curve_desc,
        "lowest_overnight_hr": lowest_hr,
        "nadir_ratio": nadir_ratio
    }

def calculate_hrv_trend_slope(hrv_raw: dict[str, Any]) -> dict[str, Any]:
    """
    Overnight HRV Trend Slope.
    Ordinary least squares (OLS) linear regression y = mx + c over 5-min overnight readings.
    """
    readings = hrv_raw.get("hrvReadings") or [] if isinstance(hrv_raw, dict) else []
    vals = [r.get("hrvValue") for r in readings if isinstance(r, dict) and r.get("hrvValue") is not None]
    if len(vals) < 3:
        return {"slope": None, "classification": "NO DATA", "desc": "Awaiting overnight HRV readings."}

    n = len(vals)
    x = list(range(n))
    mean_x = (n - 1) / 2.0
    mean_y = sum(vals) / n

    denom = sum((xi - mean_x) ** 2 for xi in x)
    numer = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, vals))
    m = numer / denom if denom > 0 else 0.0

    if m > 0.05:
        cls = "Ascending (Regenerative)"
        desc = "Parasympathetic tone deepened progressively toward morning."
    elif m < -0.05:
        cls = "Descending (Depleting)"
        desc = "Parasympathetic tone waned toward morning; body struggled with homeostasis."
    else:
        cls = "Flat"
        desc = "Balanced autonomic tone sustained steadily across sleep stages."

    return {"slope": round(m, 3), "classification": cls, "desc": desc}
