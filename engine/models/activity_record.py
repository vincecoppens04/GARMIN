from dataclasses import dataclass, field
from typing import Optional, Any
from engine.config import safe_round

@dataclass
class ActivityRecord:
    id: Any
    user_id: str
    date: str
    activity_type: str = "unknown"
    name: str = "Workout"
    start_time: Optional[str] = None
    duration_sec: int = 0
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    distance_m: float = 0.0
    calories: int = 0
    garmin_load: Optional[float] = None
    aerobic_te: Optional[float] = None
    workout_strain: float = 0.0
    hrr_60s: Optional[int] = None
    hrr_120s: Optional[int] = None
    hrr_benchmark: Optional[str] = None
    glycogen_depleted_kcal: Optional[int] = None
    carb_refuel_target_g: Optional[int] = None
    stress_recovery_min: Optional[int] = None
    metrics_v2: dict[str, Any] = field(default_factory=dict)

    def to_supabase_dict(self, include_v2: bool = True) -> dict[str, Any]:
        """Converts activity record into Supabase-compatible payload."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "date": self.date,
            "activity_type": self.activity_type,
            "name": self.name,
            "start_time": self.start_time,
            "duration_sec": self.duration_sec,
            "avg_hr": self.avg_hr,
            "max_hr": self.max_hr,
            "distance_m": self.distance_m,
            "calories": self.calories,
            "garmin_load": self.garmin_load,
            "aerobic_te": self.aerobic_te,
            "workout_strain": self.workout_strain,
        }
        if include_v2:
            data.update({
                "hrr_60s": self.hrr_60s,
                "hrr_120s": self.hrr_120s,
                "hrr_benchmark": self.hrr_benchmark,
                "glycogen_depleted_kcal": self.glycogen_depleted_kcal,
                "carb_refuel_target_g": self.carb_refuel_target_g,
                "stress_recovery_min": self.stress_recovery_min,
                "metrics_v2": self.metrics_v2,
            })
        return data

    @classmethod
    def from_supabase_row(cls, row: dict[str, Any]) -> "ActivityRecord":
        return cls(
            id=row.get("id"),
            user_id=row.get("user_id", ""),
            date=row.get("date", ""),
            activity_type=row.get("activity_type", "unknown"),
            name=row.get("name", "Workout"),
            start_time=row.get("start_time"),
            duration_sec=int(row.get("duration_sec") or 0),
            avg_hr=safe_round(row.get("avg_hr")),
            max_hr=safe_round(row.get("max_hr")),
            distance_m=float(row.get("distance_m") or 0.0),
            calories=int(row.get("calories") or 0),
            garmin_load=safe_round(row.get("garmin_load"), decimals=1),
            aerobic_te=safe_round(row.get("aerobic_te"), decimals=1),
            workout_strain=float(row.get("workout_strain") or 0.0),
            hrr_60s=safe_round(row.get("hrr_60s")),
            hrr_120s=safe_round(row.get("hrr_120s")),
            hrr_benchmark=row.get("hrr_benchmark"),
            glycogen_depleted_kcal=safe_round(row.get("glycogen_depleted_kcal")),
            carb_refuel_target_g=safe_round(row.get("carb_refuel_target_g")),
            stress_recovery_min=safe_round(row.get("stress_recovery_min")),
            metrics_v2=row.get("metrics_v2") or {},
        )
