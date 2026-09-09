from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class UserBaselines:
    user_id: str
    email: Optional[str] = None
    max_hr: int = 190
    baseline_sleep_need_min: int = 435
    debt_payback_rate: float = 0.33
    sex: str = "male"
    birth_year: int = 2004
    target_wake_time: str = "07:00"
    vo2_max: Optional[float] = None

    @classmethod
    def from_supabase_row(cls, row: dict[str, Any], user_id: str) -> "UserBaselines":
        if not row:
            return cls(user_id=user_id)
        return cls(
            user_id=user_id,
            email=row.get("email"),
            max_hr=int(row.get("max_hr", 190)),
            baseline_sleep_need_min=int(row.get("baseline_sleep_need_min", 435)),
            debt_payback_rate=float(row.get("debt_payback_rate", 0.33)),
            sex=row.get("sex", "male"),
            birth_year=int(row.get("birth_year", 2004)),
            target_wake_time=row.get("target_wake_time", "07:00"),
            vo2_max=float(row["vo2_max"]) if row.get("vo2_max") is not None else None,
        )
