from dataclasses import dataclass, field
from typing import Optional, Any
from engine.config import safe_round

@dataclass
class DayRecord:
    """
    Domain Entity representing a complete day's sports science telemetry.
    Matches the schema of the Supabase `daily_summaries` table.
    """
    user_id: str
    date: str
    recovery_score: int
    recovery_driver: str
    hrv_rmssd: Optional[float] = None
    rhr: Optional[int] = None
    resp_rate: Optional[float] = None
    spo2: Optional[float] = None
    day_strain: float = 0.0
    target_strain_min: float = 0.0
    target_strain_max: float = 21.0
    strain_curve_15m: list[dict[str, Any]] = field(default_factory=list)
    sleep_actual_sec: Optional[int] = None
    sleep_bed_sec: Optional[int] = None
    sleep_efficiency: Optional[float] = None
    sleep_onset: Optional[str] = None
    sleep_wake: Optional[str] = None
    sleep_need_min: int = 435
    sleep_debt_min: int = 0
    recommended_bedtime: str = "22:30"
    sleep_equation_str: str = ""
    circadian_consistency: int = 80
    sleep_stages_timeline: list[dict[str, Any]] = field(default_factory=list)
    health_alerts: list[str] = field(default_factory=list)
    ai_briefing: str = ""
    immune_strain_index: Optional[float] = None
    immune_tier: Optional[str] = None
    nocturnal_dip_pct: Optional[float] = None
    sleep_curve_type: Optional[str] = None
    hrv_trend_slope: Optional[float] = None
    restoration_pct: Optional[float] = None
    restlessness_index: Optional[float] = None
    social_jetlag_min: Optional[int] = None
    chronic_strain_debt: Optional[float] = None
    alcohol_latency_hr: Optional[float] = None
    stress_balance_ratio: Optional[float] = None
    metrics_v2: dict[str, Any] = field(default_factory=dict)

    @property
    def is_primed(self) -> bool:
        return self.recovery_score >= 67

    @property
    def is_overreaching(self) -> bool:
        return self.recovery_score < 60 and self.day_strain >= 12.0

    @property
    def quadrant(self) -> tuple[str, str]:
        if self.recovery_score >= 60 and self.day_strain >= 12.0:
            return "OPTIMAL OVERLOAD", "High Recovery + High Strain = Productive athletic adaptation"
        elif self.recovery_score < 60 and self.day_strain >= 12.0:
            return "OVERREACHING", "Low Recovery + High Strain = Elevated injury/fatigue risk"
        elif self.recovery_score >= 60 and self.day_strain < 12.0:
            return "RESTORING / PRIMED", "High Recovery + Moderate Strain = Tapering or deloading"
        else:
            return "DETRAINING / SYSTEMIC STRESS", "Low Recovery + Low Strain = Sickness or life stress"

    def to_supabase_dict(self, tier: int = 1) -> dict[str, Any]:
        """
        Converts the DayRecord into a Supabase upsert payload.
        tier=1: Full schema including recommended_bedtime and sleep_equation_str.
        tier=2: Clean schema omitting unmigrated string columns but preserving all V2 metrics.
        tier=3: Core legacy schema omitting newly migrated V2 columns.
        """
        record = {
            "user_id": self.user_id,
            "date": self.date,
            "recovery_score": self.recovery_score,
            "recovery_driver": self.recovery_driver,
            "hrv_rmssd": self.hrv_rmssd,
            "rhr": self.rhr,
            "resp_rate": self.resp_rate,
            "spo2": self.spo2,
            "day_strain": self.day_strain,
            "target_strain_min": self.target_strain_min,
            "target_strain_max": self.target_strain_max,
            "strain_curve_15m": self.strain_curve_15m,
            "sleep_actual_sec": self.sleep_actual_sec,
            "sleep_bed_sec": self.sleep_bed_sec,
            "sleep_efficiency": self.sleep_efficiency,
            "sleep_onset": self.sleep_onset,
            "sleep_wake": self.sleep_wake,
            "sleep_need_min": self.sleep_need_min,
            "sleep_debt_min": self.sleep_debt_min,
            "recommended_bedtime": self.recommended_bedtime,
            "sleep_equation_str": self.sleep_equation_str,
            "circadian_consistency": self.circadian_consistency,
            "sleep_stages_timeline": self.sleep_stages_timeline,
            "health_alerts": self.health_alerts,
            "ai_briefing": self.ai_briefing,
            "immune_strain_index": self.immune_strain_index,
            "immune_tier": self.immune_tier,
            "nocturnal_dip_pct": self.nocturnal_dip_pct,
            "sleep_curve_type": self.sleep_curve_type,
            "hrv_trend_slope": self.hrv_trend_slope,
            "restoration_pct": self.restoration_pct,
            "restlessness_index": self.restlessness_index,
            "social_jetlag_min": self.social_jetlag_min,
            "chronic_strain_debt": self.chronic_strain_debt,
            "alcohol_latency_hr": self.alcohol_latency_hr,
            "stress_balance_ratio": self.stress_balance_ratio,
            "metrics_v2": self.metrics_v2,
        }

        if tier == 2:
            return {k: v for k, v in record.items() if k not in ("recommended_bedtime", "sleep_equation_str")}
        elif tier == 3:
            unmigrated = (
                "immune_strain_index", "immune_tier", "nocturnal_dip_pct", "sleep_curve_type",
                "hrv_trend_slope", "restoration_pct", "restlessness_index", "social_jetlag_min",
                "chronic_strain_debt", "alcohol_latency_hr", "stress_balance_ratio", "metrics_v2",
                "recommended_bedtime", "sleep_equation_str"
            )
            return {k: v for k, v in record.items() if k not in unmigrated}
        return record

    def to_summary_dict(self) -> dict[str, Any]:
        """Converts DayRecord into the pipeline's return dictionary."""
        return {
            "date": self.date,
            "recovery": self.recovery_score,
            "recovery_score": self.recovery_score,
            "strain": self.day_strain,
            "day_strain": self.day_strain,
            "target_strain_min": self.target_strain_min,
            "target_strain_max": self.target_strain_max,
            "sleep_sec": self.sleep_actual_sec or 0,
            "sleep_need_min": self.sleep_need_min,
            "debt_min": self.sleep_debt_min,
            "bedtime": self.recommended_bedtime,
            "recommended_bedtime": self.recommended_bedtime,
            "sleep_equation_str": self.sleep_equation_str,
            "sync_freshness": self.metrics_v2.get("sync_freshness", {}),
            "health_alerts": self.health_alerts,
            "circadian_consistency": self.circadian_consistency,
            "ai_briefing": self.ai_briefing,
            "metrics_v2": self.metrics_v2,
        }

    @classmethod
    def from_supabase_row(cls, row: dict[str, Any]) -> "DayRecord":
        return cls(
            user_id=row.get("user_id", ""),
            date=row.get("date", ""),
            recovery_score=int(row.get("recovery_score") or 0),
            recovery_driver=row.get("recovery_driver", "UNKNOWN"),
            hrv_rmssd=safe_round(row.get("hrv_rmssd"), decimals=1),
            rhr=safe_round(row.get("rhr")),
            resp_rate=safe_round(row.get("resp_rate"), decimals=1),
            spo2=safe_round(row.get("spo2"), decimals=1),
            day_strain=float(row.get("day_strain") or 0.0),
            target_strain_min=float(row.get("target_strain_min") or 0.0),
            target_strain_max=float(row.get("target_strain_max") or 21.0),
            strain_curve_15m=row.get("strain_curve_15m") or [],
            sleep_actual_sec=safe_round(row.get("sleep_actual_sec")),
            sleep_bed_sec=safe_round(row.get("sleep_bed_sec")),
            sleep_efficiency=safe_round(row.get("sleep_efficiency"), decimals=1),
            sleep_onset=row.get("sleep_onset"),
            sleep_wake=row.get("sleep_wake"),
            sleep_need_min=int(row.get("sleep_need_min") or 435),
            sleep_debt_min=int(row.get("sleep_debt_min") or 0),
            recommended_bedtime=row.get("recommended_bedtime") or "22:30",
            sleep_equation_str=row.get("sleep_equation_str") or "",
            circadian_consistency=int(row.get("circadian_consistency") or 80),
            sleep_stages_timeline=row.get("sleep_stages_timeline") or [],
            health_alerts=row.get("health_alerts") or [],
            ai_briefing=row.get("ai_briefing") or "",
            immune_strain_index=safe_round(row.get("immune_strain_index"), decimals=1),
            immune_tier=row.get("immune_tier"),
            nocturnal_dip_pct=safe_round(row.get("nocturnal_dip_pct"), decimals=1),
            sleep_curve_type=row.get("sleep_curve_type"),
            hrv_trend_slope=safe_round(row.get("hrv_trend_slope"), decimals=2),
            restoration_pct=safe_round(row.get("restoration_pct"), decimals=1),
            restlessness_index=safe_round(row.get("restlessness_index"), decimals=2),
            social_jetlag_min=safe_round(row.get("social_jetlag_min")),
            chronic_strain_debt=safe_round(row.get("chronic_strain_debt"), decimals=1),
            alcohol_latency_hr=safe_round(row.get("alcohol_latency_hr"), decimals=1),
            stress_balance_ratio=safe_round(row.get("stress_balance_ratio"), decimals=2),
            metrics_v2=row.get("metrics_v2") or {},
        )
