from datetime import datetime
from engine.calculators.sleep import (
    calculate_sleep_ledger_and_bedtime,
    calculate_circadian_consistency,
    calculate_circadian_windows,
)
from engine.calculators.strain import (
    calculate_activity_strain,
    calculate_target_strain_window,
    calculate_acwr,
    calculate_training_monotony,
)
from engine.calculators.recovery import (
    calculate_recovery_and_health_stress,
    calculate_workout_prescriber,
    calculate_immune_strain_index,
)
from engine.calculators.metabolic import (
    calculate_caffeine_clearance,
    calculate_alcohol_latency,
)

def test_sleep_ledger_and_bedtime():
    debt, target_min, bedtime, equation = calculate_sleep_ledger_and_bedtime(
        base_sleep_need_min=435,
        debt_payback_rate=0.33,
        prev_summary={"sleep_debt_min": 30, "sleep_actual_sec": 420 * 60},
        day_strain=15.0,
        target_date_str="2026-09-07",
        target_wake_time="07:00",
    )
    assert debt >= 0
    assert target_min > 435
    assert ":" in bedtime
    assert "Base" in equation

def test_activity_strain():
    strain = calculate_activity_strain(
        avg_hr=150,
        duration_sec=3600,
        rhr=50,
        max_hr=190,
        sex="male",
    )
    assert 0.0 < strain <= 21.0

def test_target_strain_window():
    min_s, max_s = calculate_target_strain_window(recovery_score=80, health_status="NORMAL")
    assert 0.0 <= min_s < max_s <= 21.0

    # Sickness restriction
    min_sick, max_sick = calculate_target_strain_window(recovery_score=80, health_status="HIGH_STRAIN_SICKNESS")
    assert max_sick == 6.0

def test_workout_prescriber():
    pres_green = calculate_workout_prescriber(80)
    assert pres_green["zone"] == "GREEN"

    pres_red = calculate_workout_prescriber(25)
    assert pres_red["zone"] == "RED"

def test_caffeine_clearance():
    # Anchored bedtime cutoff
    res = calculate_caffeine_clearance(
        habit_entry={"any_caffeine": True, "late_caffeine": False},
        bedtime_str="23:15"
    )
    assert res["active"] is True
    assert "remaining_mg_at_bedtime" in res
    assert len(res["curve_points"]) == 13

def test_circadian_windows():
    windows = calculate_circadian_windows(wake_time_str="07:00", bedtime_str="23:15")
    assert len(windows) == 5
    caff_win = next(w for w in windows if w["id"] == "caffeine")
    assert caff_win["time_window"] == "13:15"  # Exactly Bedtime - 10 hours!

def test_acwr():
    history_28d = [{"day_strain": 12.0} for _ in range(28)]
    res = calculate_acwr(history_28d)
    assert res["acwr"] == 1.0
    assert res["zone_key"] == "SWEET_SPOT"

def test_training_monotony():
    history_7d = [{"day_strain": 12.0} for _ in range(7)]
    res = calculate_training_monotony(history_7d)
    assert res["mean_strain"] == 12.0
