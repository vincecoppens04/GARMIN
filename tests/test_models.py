from engine.models.day_record import DayRecord
from engine.models.activity_record import ActivityRecord
from engine.models.user_baselines import UserBaselines

def test_day_record_creation_and_properties():
    rec = DayRecord(
        user_id="user_123",
        date="2026-09-07",
        recovery_score=85,
        recovery_driver="HRV +12% vs 30d baseline",
        hrv_rmssd=65.0,
        rhr=48,
        day_strain=14.5,
        target_strain_min=12.0,
        target_strain_max=16.0,
    )
    assert rec.is_primed is True
    assert rec.is_overreaching is False
    quad_title, _ = rec.quadrant
    assert quad_title == "OPTIMAL OVERLOAD"

    # Test Supabase tiered conversions
    tier1 = rec.to_supabase_dict(tier=1)
    assert "recommended_bedtime" in tier1
    assert "sleep_equation_str" in tier1
    assert tier1["recovery_score"] == 85

    tier2 = rec.to_supabase_dict(tier=2)
    assert "recommended_bedtime" not in tier2
    assert "sleep_equation_str" not in tier2
    assert "metrics_v2" in tier2

    summary = rec.to_summary_dict()
    assert summary["recovery"] == 85
    assert summary["strain"] == 14.5

def test_activity_record_creation_and_supabase_dict():
    act = ActivityRecord(
        id=12345678,
        user_id="user_123",
        date="2026-09-07",
        activity_type="running",
        name="Morning Interval Run",
        duration_sec=3600,
        avg_hr=155,
        max_hr=178,
        workout_strain=12.4,
        hrr_60s=38,
        hrr_120s=52,
        hrr_benchmark="Optimal (High Vagal Recovery)",
        glycogen_depleted_kcal=450,
        carb_refuel_target_g=112,
    )
    data = act.to_supabase_dict(include_v2=True)
    assert data["id"] == 12345678
    assert data["hrr_60s"] == 38
    assert data["carb_refuel_target_g"] == 112

def test_user_baselines_from_row():
    row = {
        "max_hr": 195,
        "baseline_sleep_need_min": 450,
        "debt_payback_rate": "0.33",
        "sex": "female",
        "birth_year": 1998,
        "target_wake_time": "06:30",
        "vo2_max": 54.2,
    }
    b = UserBaselines.from_supabase_row(row, user_id="user_abc")
    assert b.max_hr == 195
    assert b.baseline_sleep_need_min == 450
    assert b.sex == "female"
    assert b.target_wake_time == "06:30"
    assert b.vo2_max == 54.2
